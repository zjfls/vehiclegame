"""Vehicle config loader / validator.

This project historically stored vehicle configs in a flat-ish schema ("v1").
We now migrate to a single "v2" schema, but we still provide a helper to
produce a legacy-shaped dict so existing systems keep working while the
simulation is upgraded.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class VehicleConfigError(ValueError):
    pass


def _as_floats3(value: Any, *, default: Tuple[float, float, float]) -> List[float]:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return [float(value[0]), float(value[1]), float(value[2])]
        except Exception:
            return [float(default[0]), float(default[1]), float(default[2])]
    return [float(default[0]), float(default[1]), float(default[2])]


def _infer_track_width_from_wheels(wheels_v1: List[dict]) -> Optional[float]:
    xs = []
    for w in wheels_v1:
        pos = w.get("position")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            try:
                xs.append(float(pos[0]))
            except Exception:
                pass
    if len(xs) >= 2:
        return float(max(xs) - min(xs))
    return None


def _infer_wheelbase_from_wheels(wheels_v1: List[dict]) -> Optional[float]:
    ys = []
    for w in wheels_v1:
        pos = w.get("position")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            try:
                ys.append(float(pos[1]))
            except Exception:
                pass
    if len(ys) >= 2:
        return float(max(ys) - min(ys))
    return None


def _infer_drivetrain_layout(wheels_v2: List[dict]) -> str:
    # Panda3D: +Y forward. Wheels use local coordinates.
    driven_front = False
    driven_rear = False
    for w in wheels_v2:
        if not bool(w.get("is_driven", False)):
            continue
        pos = w.get("position_local_m")
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            y = float(pos[1])
            if y >= 0:
                driven_front = True
            else:
                driven_rear = True
    if driven_front and driven_rear:
        return "AWD"
    if driven_front:
        return "FWD"
    if driven_rear:
        return "RWD"
    return "AWD"


def _estimate_yaw_inertia(mass_kg: float, wheelbase_m: float, track_width_m: float) -> float:
    # Uniform rectangle around Z: Iz = m/12 * (L^2 + W^2). We scale it a bit
    # to better match typical vehicle yaw inertia.
    base = (mass_kg / 12.0) * (wheelbase_m * wheelbase_m + track_width_m * track_width_m)
    return float(max(100.0, base * 1.4))


def upgrade_v1_to_v2(raw_v1: Dict[str, Any], *, vehicle_id: str) -> Dict[str, Any]:
    """Upgrade legacy vehicle config (v1) to v2 schema."""
    name = str(raw_v1.get("name") or vehicle_id)
    position = _as_floats3(raw_v1.get("position"), default=(0.0, 0.0, 12.0))
    heading = float(raw_v1.get("heading", 0.0) or 0.0)
    mass_kg = float(raw_v1.get("vehicle_mass", 1500.0) or 1500.0)

    physics_v1 = raw_v1.get("physics") if isinstance(raw_v1.get("physics"), dict) else {}
    pose_v1 = raw_v1.get("pose") if isinstance(raw_v1.get("pose"), dict) else {}
    suspension_v1 = raw_v1.get("suspension") if isinstance(raw_v1.get("suspension"), dict) else {}
    transmission_v1 = raw_v1.get("transmission") if isinstance(raw_v1.get("transmission"), dict) else {}
    diff_v1 = transmission_v1.get("differential") if isinstance(transmission_v1.get("differential"), dict) else {}

    wheels_v1 = raw_v1.get("wheels") if isinstance(raw_v1.get("wheels"), list) else []
    tires_v1 = raw_v1.get("tires") if isinstance(raw_v1.get("tires"), list) else []
    susp_wheels_v1 = suspension_v1.get("wheels") if isinstance(suspension_v1.get("wheels"), list) else []

    track_width = float(pose_v1.get("track_width") or _infer_track_width_from_wheels(wheels_v1) or 1.8)
    wheelbase = float(pose_v1.get("wheelbase") or _infer_wheelbase_from_wheels(wheels_v1) or 2.6)
    cg_height = float(pose_v1.get("cg_height") or 0.55)
    com_pos = _as_floats3(suspension_v1.get("com_position"), default=(0.0, 0.0, cg_height))

    yaw_inertia = _estimate_yaw_inertia(mass_kg, wheelbase, track_width)

    # Controls / smoothing
    smoothing = physics_v1.get("input_smoothing") if isinstance(physics_v1.get("input_smoothing"), dict) else {}
    steer_max_deg = float(physics_v1.get("max_steering_angle", 35.0) or 35.0)

    # Simple kinematics used by the current (v1) simulation path.
    simple_physics = {
        "max_speed_kmh": float(physics_v1.get("max_speed", 160.0) or 160.0),
        "acceleration_kmhps": float(physics_v1.get("acceleration", 50.0) or 50.0),
        "deceleration_kmhps": float(physics_v1.get("deceleration", 30.0) or 30.0),
        "brake_deceleration_kmhps": float(physics_v1.get("brake_deceleration", 80.0) or 80.0),
        "turn_speed_deg_s": float(physics_v1.get("turn_speed", 150.0) or 150.0),
        "drag_coefficient": float(physics_v1.get("drag_coefficient", 0.3) or 0.3),
    }

    # Aero defaults: pick conservative but plausible values.
    default_area = 2.2
    default_crr = 0.016
    if mass_kg >= 3000:
        default_area = 3.2
        default_crr = 0.022
    elif mass_kg >= 2000:
        default_area = 2.6
        default_crr = 0.018

    aero = {
        "cd": float(physics_v1.get("drag_coefficient", 0.35) or 0.35),
        "frontal_area_m2": float(default_area),
        "rolling_resistance": float(default_crr),
    }

    # Wheels
    wheels_v2: List[dict] = []
    wheel_mass_kg = 20.0
    g = 9.81
    for w in wheels_v1:
        pos = _as_floats3(w.get("position"), default=(0.0, 0.0, 0.0))
        r = float(w.get("radius", 0.35) or 0.35)
        r = max(0.05, r)
        inertia = float(w.get("inertia", 0.5 * wheel_mass_kg * r * r) or (0.5 * wheel_mass_kg * r * r))
        # Brake torque large enough to lock the wheel on high mu.
        brake_max = float(w.get("brake_max_torque", (mass_kg * g / 4.0) * r * 2.0))
        wheels_v2.append(
            {
                "position_local_m": pos,
                "radius_m": r,
                "inertia_kgm2": inertia,
                "brake_max_torque_nm": brake_max,
                "can_steer": bool(w.get("can_steer", False)),
                "is_driven": bool(w.get("is_driven", False)),
            }
        )

    # Tires
    tires_v2: List[dict] = []
    for t in tires_v1:
        tires_v2.append(
            {
                "mu": float(t.get("friction", 1.0) or 1.0),
                "long_stiff": float(t.get("long_stiff_value", 1000.0) or 1000.0),
                "lat_stiff": float(t.get("lat_stiff_value", 17.0) or 17.0),
                "lat_stiff_max_load": float(t.get("lat_stiff_max_load", 2.0) or 2.0),
            }
        )

    # Suspension (keep the natural-frequency based tuning style)
    susp_wheels_v2: List[dict] = []
    for sw in susp_wheels_v1:
        susp_wheels_v2.append(
            {
                "position_local_m": _as_floats3(sw.get("position"), default=(0.0, 0.0, 0.0)),
                "natural_frequency_hz": float(sw.get("natural_frequency", 7.0) or 7.0),
                "damping_ratio": float(sw.get("damping_ratio", 1.0) or 1.0),
                "rest_length_m": float(sw.get("rest_length", 0.3) or 0.3),
                "max_compression_m": float(sw.get("max_compression", 0.1) or 0.1),
                "max_droop_m": float(sw.get("max_droop", 0.1) or 0.1),
            }
        )

    engine_v1 = transmission_v1.get("engine") if isinstance(transmission_v1.get("engine"), dict) else {}
    powertrain = {
        "engine": {
            "idle_rpm": float(engine_v1.get("idle_rpm", 800.0) or 800.0),
            "max_rpm": float(engine_v1.get("max_rpm", 6000.0) or 6000.0),
            "moi_kgm2": float(engine_v1.get("moi", 1.0) or 1.0),
            "torque_curve_nm": engine_v1.get("torque_curve") or [],
            "damping_full_throttle": float(engine_v1.get("damping_full_throttle", 0.15) or 0.15),
            "damping_zero_throttle_clutch_engaged": float(
                engine_v1.get("damping_zero_throttle_clutch_engaged", 2.0) or 2.0
            ),
            "damping_zero_throttle_clutch_disengaged": float(
                engine_v1.get("damping_zero_throttle_clutch_disengaged", 0.35) or 0.35
            ),
        },
        "gearbox": {
            "ratios": transmission_v1.get("gear_ratios") or [0.0, 3.5, 2.5, 1.8, 1.4, 1.0],
            "final_drive": float(transmission_v1.get("final_ratio", 3.5) or 3.5),
            "reverse_ratio": float(transmission_v1.get("reverse_ratio", -3.5) or -3.5),
            "auto_shift": bool(transmission_v1.get("auto_shift", True)),
            "shift_time_s": float(transmission_v1.get("shift_time", 0.3) or 0.3),
            "shift_rpm_up_ratio": float(transmission_v1.get("shift_rpm_up_ratio", 0.85) or 0.85),
            "shift_rpm_down_ratio": float(transmission_v1.get("shift_rpm_down_ratio", 0.35) or 0.35),
        },
        "clutch": {
            "strength": float(transmission_v1.get("clutch_strength", 10.0) or 10.0),
            "engage_time_s": float(transmission_v1.get("clutch_engage_time_s", 0.20) or 0.20),
        },
        "differential": {
            "type": str(diff_v1.get("diff_type") or "limited_slip"),
            "layout": "AWD",
            "front_rear_split": float(diff_v1.get("front_rear_split", 0.5) or 0.5),
            "front_bias": float(diff_v1.get("front_bias", 1.5) or 1.5),
            "rear_bias": float(diff_v1.get("rear_bias", 2.0) or 2.0),
        },
    }

    v2 = {
        "version": 2,
        "name": name,
        "spawn": {"position_m": position, "heading_deg": heading},
        "chassis": {
            "mass_kg": mass_kg,
            "cg_height_m": cg_height,
            "cg_position_m": com_pos,
            "wheelbase_m": wheelbase,
            "track_width_m": track_width,
            "yaw_inertia_kgm2": yaw_inertia,
        },
        "controls": {
            "steer_max_deg": steer_max_deg,
            "input_smoothing": {
                "throttle_rise": float(smoothing.get("throttle_rise", 6.0) or 6.0),
                "throttle_fall": float(smoothing.get("throttle_fall", 10.0) or 10.0),
                "brake_rise": float(smoothing.get("brake_rise", 6.0) or 6.0),
                "brake_fall": float(smoothing.get("brake_fall", 10.0) or 10.0),
                "steering_rise": float(smoothing.get("steering_rise", 2.5) or 2.5),
                "steering_fall": float(smoothing.get("steering_fall", 5.0) or 5.0),
            },
        },
        "aero": aero,
        "simple_physics": simple_physics,
        "powertrain": powertrain,
        "wheels": wheels_v2,
        "tires": tires_v2,
        "suspension": {"com_position_m": com_pos, "wheels": susp_wheels_v2},
        "visual": {"pose": dict(pose_v1)},
    }

    # Infer drivetrain layout after wheels exist.
    v2["powertrain"]["differential"]["layout"] = _infer_drivetrain_layout(wheels_v2)
    return v2


def _validate_v2(cfg: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if int(cfg.get("version", 0) or 0) != 2:
        errors.append("version must be 2")

    spawn = cfg.get("spawn")
    if not isinstance(spawn, dict):
        errors.append("spawn must be an object")
    else:
        pos = spawn.get("position_m")
        if not (isinstance(pos, (list, tuple)) and len(pos) >= 3):
            errors.append("spawn.position_m must be [x,y,z]")

    chassis = cfg.get("chassis")
    if not isinstance(chassis, dict):
        errors.append("chassis must be an object")
    else:
        if float(chassis.get("mass_kg", 0.0) or 0.0) <= 0:
            errors.append("chassis.mass_kg must be > 0")
        if float(chassis.get("wheelbase_m", 0.0) or 0.0) <= 0:
            errors.append("chassis.wheelbase_m must be > 0")
        if float(chassis.get("track_width_m", 0.0) or 0.0) <= 0:
            errors.append("chassis.track_width_m must be > 0")
        if float(chassis.get("yaw_inertia_kgm2", 0.0) or 0.0) <= 0:
            errors.append("chassis.yaw_inertia_kgm2 must be > 0")

    wheels = cfg.get("wheels")
    tires = cfg.get("tires")
    susp = cfg.get("suspension")

    if not isinstance(wheels, list) or not wheels:
        errors.append("wheels must be a non-empty list")
    if not isinstance(tires, list) or not tires:
        errors.append("tires must be a non-empty list")
    if isinstance(wheels, list) and isinstance(tires, list) and wheels and tires:
        if len(wheels) != len(tires):
            errors.append("wheels and tires length must match")

    if not isinstance(susp, dict) or not isinstance(susp.get("wheels"), list):
        errors.append("suspension.wheels must be a list")
    elif isinstance(wheels, list) and wheels and len(susp.get("wheels") or []) != len(wheels):
        errors.append("suspension.wheels length must match wheels")

    pt = cfg.get("powertrain")
    if not isinstance(pt, dict):
        errors.append("powertrain must be an object")
    else:
        engine = pt.get("engine")
        if not isinstance(engine, dict):
            errors.append("powertrain.engine must be an object")
        gearbox = pt.get("gearbox")
        if not isinstance(gearbox, dict):
            errors.append("powertrain.gearbox must be an object")
        else:
            ratios = gearbox.get("ratios")
            if not isinstance(ratios, list) or len(ratios) < 2:
                errors.append("powertrain.gearbox.ratios must be a list with >=2 entries")

    return errors


def validate_v2(cfg: Dict[str, Any]) -> List[str]:
    """Public validator for v2 configs (used by the console editor)."""
    try:
        cfg_n = normalize_v2(cfg)
    except Exception:
        cfg_n = cfg
    return _validate_v2(cfg_n)


def normalize_v2(cfg: Dict[str, Any]) -> Dict[str, Any]:
    # Minimal normalization: convert obvious numeric fields.
    cfg = dict(cfg)
    cfg["version"] = 2

    spawn = dict(cfg.get("spawn") or {})
    spawn["position_m"] = _as_floats3(spawn.get("position_m"), default=(0.0, 0.0, 12.0))
    spawn["heading_deg"] = float(spawn.get("heading_deg", 0.0) or 0.0)
    cfg["spawn"] = spawn

    chassis = dict(cfg.get("chassis") or {})
    chassis["mass_kg"] = float(chassis.get("mass_kg", 1500.0) or 1500.0)
    chassis["cg_height_m"] = float(chassis.get("cg_height_m", 0.55) or 0.55)
    chassis["cg_position_m"] = _as_floats3(chassis.get("cg_position_m"), default=(0.0, 0.0, chassis["cg_height_m"]))
    chassis["wheelbase_m"] = float(chassis.get("wheelbase_m", 2.6) or 2.6)
    chassis["track_width_m"] = float(chassis.get("track_width_m", 1.8) or 1.8)
    chassis["yaw_inertia_kgm2"] = float(
        chassis.get("yaw_inertia_kgm2", _estimate_yaw_inertia(chassis["mass_kg"], chassis["wheelbase_m"], chassis["track_width_m"]))
    )
    cfg["chassis"] = chassis

    # Torque curve: ensure it's a list of [rpm, torque] and sorted.
    pt = dict(cfg.get("powertrain") or {})
    engine = dict(pt.get("engine") or {})
    curve = engine.get("torque_curve_nm")
    if isinstance(curve, list):
        pts = []
        for p in curve:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                try:
                    pts.append((float(p[0]), float(p[1])))
                except Exception:
                    pass
        pts.sort(key=lambda x: x[0])
        engine["torque_curve_nm"] = [[rpm, tq] for rpm, tq in pts]
    pt["engine"] = engine

    gearbox = dict(pt.get("gearbox") or {})
    ratios = gearbox.get("ratios")
    if isinstance(ratios, list):
        gearbox["ratios"] = [float(x) for x in ratios]
    pt["gearbox"] = gearbox

    diff = dict(pt.get("differential") or {})
    if not diff.get("layout") and isinstance(cfg.get("wheels"), list):
        diff["layout"] = _infer_drivetrain_layout(cfg["wheels"])
    pt["differential"] = diff
    cfg["powertrain"] = pt

    return cfg


def to_legacy_config(cfg_v2: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict shaped like the current VehicleEntity/systems expect."""
    cfg_v2 = normalize_v2(cfg_v2)

    errors = _validate_v2(cfg_v2)
    if errors:
        raise VehicleConfigError("Invalid v2 vehicle config: " + "; ".join(errors))

    spawn = cfg_v2["spawn"]
    chassis = cfg_v2["chassis"]
    controls = cfg_v2.get("controls") if isinstance(cfg_v2.get("controls"), dict) else {}
    aero = cfg_v2.get("aero") if isinstance(cfg_v2.get("aero"), dict) else {}
    simple = cfg_v2.get("simple_physics") if isinstance(cfg_v2.get("simple_physics"), dict) else {}
    visual = cfg_v2.get("visual") if isinstance(cfg_v2.get("visual"), dict) else {}
    pose = visual.get("pose") if isinstance(visual.get("pose"), dict) else {}
    pt = cfg_v2.get("powertrain") if isinstance(cfg_v2.get("powertrain"), dict) else {}

    physics = {
        "max_speed": float(simple.get("max_speed_kmh", 160.0) or 160.0),
        "mass": float(chassis.get("mass_kg", 1500.0) or 1500.0),
        "drag_coefficient": float(simple.get("drag_coefficient", aero.get("cd", 0.35)) or 0.35),
        "acceleration": float(simple.get("acceleration_kmhps", 50.0) or 50.0),
        "deceleration": float(simple.get("deceleration_kmhps", 30.0) or 30.0),
        "brake_deceleration": float(simple.get("brake_deceleration_kmhps", 80.0) or 80.0),
        "turn_speed": float(simple.get("turn_speed_deg_s", 150.0) or 150.0),
        "max_steering_angle": float(controls.get("steer_max_deg", 35.0) or 35.0),
        "input_smoothing": dict(controls.get("input_smoothing") or {}),
    }

    # Map wheels/tires back.
    wheels_legacy: List[dict] = []
    for w in cfg_v2.get("wheels") or []:
        wheels_legacy.append(
            {
                "position": _as_floats3(w.get("position_local_m"), default=(0.0, 0.0, 0.0)),
                "radius": float(w.get("radius_m", 0.35) or 0.35),
                "can_steer": bool(w.get("can_steer", False)),
                "is_driven": bool(w.get("is_driven", False)),
            }
        )

    tires_legacy: List[dict] = []
    for t in cfg_v2.get("tires") or []:
        tires_legacy.append(
            {
                "lat_stiff_max_load": float(t.get("lat_stiff_max_load", 2.0) or 2.0),
                "lat_stiff_value": float(t.get("lat_stiff", 17.0) or 17.0),
                "long_stiff_value": float(t.get("long_stiff", 1000.0) or 1000.0),
                "friction": float(t.get("mu", 1.0) or 1.0),
            }
        )

    susp = cfg_v2.get("suspension") if isinstance(cfg_v2.get("suspension"), dict) else {}
    susp_wheels = []
    for sw in susp.get("wheels") or []:
        susp_wheels.append(
            {
                "position": _as_floats3(sw.get("position_local_m"), default=(0.0, 0.0, 0.0)),
                "natural_frequency": float(sw.get("natural_frequency_hz", 7.0) or 7.0),
                "damping_ratio": float(sw.get("damping_ratio", 1.0) or 1.0),
                "rest_length": float(sw.get("rest_length_m", 0.3) or 0.3),
                "max_compression": float(sw.get("max_compression_m", 0.1) or 0.1),
                "max_droop": float(sw.get("max_droop_m", 0.1) or 0.1),
            }
        )

    suspension_legacy = {
        "vehicle_mass": float(chassis.get("mass_kg", 1500.0) or 1500.0),
        "com_position": _as_floats3(susp.get("com_position_m"), default=(0.0, 0.0, float(chassis.get("cg_height_m", 0.55) or 0.55))),
        "wheels": susp_wheels,
    }

    # Pose system tuning remains as-is, but fill the geometric values from chassis.
    pose_legacy = dict(pose)
    pose_legacy.setdefault("track_width", float(chassis.get("track_width_m", 1.8) or 1.8))
    pose_legacy.setdefault("wheelbase", float(chassis.get("wheelbase_m", 2.6) or 2.6))
    pose_legacy.setdefault("cg_height", float(chassis.get("cg_height_m", 0.55) or 0.55))
    pose_legacy.setdefault("vehicle_mass", float(chassis.get("mass_kg", 1500.0) or 1500.0))

    engine = pt.get("engine") if isinstance(pt.get("engine"), dict) else {}
    gearbox = pt.get("gearbox") if isinstance(pt.get("gearbox"), dict) else {}
    clutch = pt.get("clutch") if isinstance(pt.get("clutch"), dict) else {}
    diff = pt.get("differential") if isinstance(pt.get("differential"), dict) else {}

    transmission_legacy = {
        "engine": {
            "moi": float(engine.get("moi_kgm2", 1.0) or 1.0),
            "max_rpm": float(engine.get("max_rpm", 6000.0) or 6000.0),
            "torque_curve": engine.get("torque_curve_nm") or [],
            "damping_full_throttle": float(engine.get("damping_full_throttle", 0.15) or 0.15),
            "damping_zero_throttle_clutch_engaged": float(engine.get("damping_zero_throttle_clutch_engaged", 2.0) or 2.0),
            "damping_zero_throttle_clutch_disengaged": float(engine.get("damping_zero_throttle_clutch_disengaged", 0.35) or 0.35),
        },
        "gear_ratios": gearbox.get("ratios") or [0.0, 3.5, 2.5, 1.8, 1.4, 1.0],
        "final_ratio": float(gearbox.get("final_drive", 3.5) or 3.5),
        "reverse_ratio": float(gearbox.get("reverse_ratio", -3.5) or -3.5),
        "auto_shift": bool(gearbox.get("auto_shift", True)),
        "shift_time": float(gearbox.get("shift_time_s", 0.3) or 0.3),
        "clutch_strength": float(clutch.get("strength", 10.0) or 10.0),
        "differential": {
            "diff_type": str(diff.get("type") or "limited_slip"),
            "front_rear_split": float(diff.get("front_rear_split", 0.5) or 0.5),
            "front_bias": float(diff.get("front_bias", 1.5) or 1.5),
            "rear_bias": float(diff.get("rear_bias", 2.0) or 2.0),
        },
    }

    return {
        "name": str(cfg_v2.get("name") or "Vehicle"),
        "position": list(spawn["position_m"]),
        "heading": float(spawn.get("heading_deg", 0.0) or 0.0),
        "vehicle_mass": float(chassis.get("mass_kg", 1500.0) or 1500.0),
        "physics": physics,
        "suspension": suspension_legacy,
        "pose": pose_legacy,
        "wheels": wheels_legacy,
        "tires": tires_legacy,
        "transmission": transmission_legacy,
    }


def load_v2_from_file(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and int(data.get("version", 0) or 0) == 2:
        return normalize_v2(data)
    raise VehicleConfigError(f"Not a v2 vehicle config: {path}")


def load_vehicle_v2(vehicle_id: str, *, config_dir: str = "configs") -> Dict[str, Any]:
    path = Path(config_dir) / "vehicles" / f"{vehicle_id}.json"
    if not path.exists():
        raise VehicleConfigError(f"Vehicle config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and int(data.get("version", 0) or 0) == 2:
        return normalize_v2(data)
    # If we still see v1 in the wild, provide an explicit error so the caller can migrate.
    raise VehicleConfigError(f"Vehicle config is not v2 (run migration): {path}")


def load_vehicle_legacy(vehicle_id: str, *, config_dir: str = "configs") -> Dict[str, Any]:
    return to_legacy_config(load_vehicle_v2(vehicle_id, config_dir=config_dir))
