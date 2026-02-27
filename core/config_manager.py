"""
配置管理器 - 加载/保存车辆、地形等配置
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .vehicle_config_loader import upgrade_v1_to_v2, normalize_v2


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 初始配置子目录
        for subdir in ["vehicles", "terrain"]:
            (self.config_dir / subdir).mkdir(exist_ok=True)
        
        # 创建默认车辆配置（如果不存在）
        self._create_default_vehicle_configs()
    
    def _create_default_vehicle_configs(self) -> None:
        """创建默认车辆配置"""
        vehicles_dir = self.config_dir / "vehicles"

        def _write_v2(path: Path, vehicle_id: str, v1_config: Dict[str, Any]) -> None:
            # All repo vehicles use v2 schema. Generate v2 directly so running the
            # game does not depend on a separate migration step.
            v2 = normalize_v2(upgrade_v1_to_v2(v1_config, vehicle_id=vehicle_id))
            path.write_text(json.dumps(v2, indent=2, ensure_ascii=False), encoding="utf-8")
        
        # 跑车配置
        sports_car = vehicles_dir / "sports_car.json"
        if not sports_car.exists():
            _write_v2(sports_car, "sports_car", {
                "name": "Sports Car",
                "position": [0, 0, 12.0],
                "heading": 0,
                "vehicle_mass": 1500.0,
                "physics": {
                    "max_speed": 200.0,
                    "drag_coefficient": 0.3,
                    "acceleration": 80.0,
                    "deceleration": 40.0,
                    "brake_deceleration": 120.0,
                    "turn_speed": 200.0,
                    "max_steering_angle": 40.0,
                    "input_smoothing": {
                        "throttle_rise": 8.0,
                        "throttle_fall": 12.0,
                        "brake_rise": 8.0,
                        "brake_fall": 12.0,
                        "steering_rise": 3.0,
                        "steering_fall": 6.0,
                    }
                },
                "suspension": {
                    "com_position": [0, 0, 0.3],
                    "wheels": [
                        {"position": [-0.9, 1.3, -0.35], "natural_frequency": 7.0, "damping_ratio": 1.0, "rest_length": 0.3, "max_compression": 0.1, "max_droop": 0.1},
                        {"position": [0.9, 1.3, -0.35], "natural_frequency": 7.0, "damping_ratio": 1.0, "rest_length": 0.3, "max_compression": 0.1, "max_droop": 0.1},
                        {"position": [-0.9, -1.3, -0.35], "natural_frequency": 7.0, "damping_ratio": 1.0, "rest_length": 0.3, "max_compression": 0.1, "max_droop": 0.1},
                        {"position": [0.9, -1.3, -0.35], "natural_frequency": 7.0, "damping_ratio": 1.0, "rest_length": 0.3, "max_compression": 0.1, "max_droop": 0.1},
                    ]
                },
                "tires": [
                    {"lat_stiff_max_load": 2.0, "lat_stiff_value": 17.0, "long_stiff_value": 1000.0, "friction": 1.0},
                    {"lat_stiff_max_load": 2.0, "lat_stiff_value": 17.0, "long_stiff_value": 1000.0, "friction": 1.0},
                    {"lat_stiff_max_load": 2.0, "lat_stiff_value": 17.0, "long_stiff_value": 1200.0, "friction": 1.1},
                    {"lat_stiff_max_load": 2.0, "lat_stiff_value": 17.0, "long_stiff_value": 1200.0, "friction": 1.1},
                ],
                "transmission": {
                    "engine": {
                        "moi": 1.0,
                        "max_rpm": 7000.0,
                        "torque_curve": [(0, 300), (1000, 350), (3000, 450), (5000, 420), (6500, 380), (7000, 0)],
                        "damping_full_throttle": 0.15,
                        "damping_zero_throttle_clutch_engaged": 2.0,
                        "damping_zero_throttle_clutch_disengaged": 0.35,
                    },
                    "gear_ratios": [0, 3.5, 2.5, 1.8, 1.4, 1.0, 0.8],
                    "final_ratio": 3.5,
                    "reverse_ratio": -3.5,
                    "auto_shift": True,
                    "shift_time": 0.3,
                    "clutch_strength": 10.0,
                    "differential": {
                        "diff_type": "limited_slip",
                        "front_rear_split": 0.5,
                        "front_bias": 1.5,
                        "rear_bias": 2.0,
                    }
                },
                "pose": {
                    "track_width": 1.8,
                    "wheelbase": 2.6,
                    "cg_height": 0.5,
                    "max_roll": 6.0,
                    "max_pitch": 4.0,
                    "roll_stiffness": 12000.0,
                    "pitch_stiffness": 12000.0,
                    "bounce_stiffness": 18000.0,
                    "roll_damping": 600.0,
                    "pitch_damping": 600.0,
                    "bounce_damping": 900.0,
                    "front_anti_roll": 1500.0,
                    "rear_anti_roll": 1200.0,
                },
                "wheels": [
                    {"position": [-0.9, 1.3, -0.35], "radius": 0.35, "can_steer": True, "is_driven": True},
                    {"position": [0.9, 1.3, -0.35], "radius": 0.35, "can_steer": True, "is_driven": True},
                    {"position": [-0.9, -1.3, -0.35], "radius": 0.35, "can_steer": False, "is_driven": True},
                    {"position": [0.9, -1.3, -0.35], "radius": 0.35, "can_steer": False, "is_driven": True},
                ],
            })
        
        # 卡车配置
        truck = vehicles_dir / "truck.json"
        if not truck.exists():
            _write_v2(truck, "truck", {
                "name": "Truck",
                "position": [0, 0, 12.0],
                "heading": 0,
                "vehicle_mass": 3500.0,
                "physics": {
                    "max_speed": 120.0,
                    "drag_coefficient": 0.6,
                    "acceleration": 30.0,
                    "deceleration": 25.0,
                    "brake_deceleration": 80.0,
                    "turn_speed": 120.0,
                    "max_steering_angle": 35.0,
                    "input_smoothing": {
                        "throttle_rise": 5.0,
                        "throttle_fall": 8.0,
                        "brake_rise": 10.0,
                        "brake_fall": 15.0,
                        "steering_rise": 2.0,
                        "steering_fall": 4.0,
                    }
                },
                "suspension": {
                    "com_position": [0, 0, 0.5],
                    "wheels": [
                        {"position": [-1.0, 1.8, -0.4], "natural_frequency": 5.0, "damping_ratio": 0.8, "rest_length": 0.4, "max_compression": 0.15, "max_droop": 0.15},
                        {"position": [1.0, 1.8, -0.4], "natural_frequency": 5.0, "damping_ratio": 0.8, "rest_length": 0.4, "max_compression": 0.15, "max_droop": 0.15},
                        {"position": [-1.0, -1.8, -0.4], "natural_frequency": 5.0, "damping_ratio": 0.8, "rest_length": 0.4, "max_compression": 0.15, "max_droop": 0.15},
                        {"position": [1.0, -1.8, -0.4], "natural_frequency": 5.0, "damping_ratio": 0.8, "rest_length": 0.4, "max_compression": 0.15, "max_droop": 0.15},
                    ]
                },
                "tires": [
                    {"lat_stiff_max_load": 3.0, "lat_stiff_value": 15.0, "long_stiff_value": 800.0, "friction": 0.9},
                    {"lat_stiff_max_load": 3.0, "lat_stiff_value": 15.0, "long_stiff_value": 800.0, "friction": 0.9},
                    {"lat_stiff_max_load": 3.0, "lat_stiff_value": 15.0, "long_stiff_value": 1000.0, "friction": 1.0},
                    {"lat_stiff_max_load": 3.0, "lat_stiff_value": 15.0, "long_stiff_value": 1000.0, "friction": 1.0},
                ],
                "transmission": {
                    "engine": {
                        "moi": 2.0,
                        "max_rpm": 4500.0,
                        "torque_curve": [(0, 500), (1000, 800), (2000, 900), (3000, 850), (4000, 600), (4500, 0)],
                        "damping_full_throttle": 0.2,
                        "damping_zero_throttle_clutch_engaged": 3.0,
                        "damping_zero_throttle_clutch_disengaged": 0.5,
                    },
                    "gear_ratios": [0, 4.5, 3.0, 2.0, 1.5, 1.0, 0.7],
                    "final_ratio": 4.0,
                    "reverse_ratio": -4.0,
                    "auto_shift": True,
                    "shift_time": 0.5,
                    "clutch_strength": 15.0,
                    "differential": {
                        "diff_type": "open",
                        "front_rear_split": 0.5,
                        "front_bias": 1.0,
                        "rear_bias": 1.0,
                    }
                },
                "pose": {
                    "track_width": 2.0,
                    "wheelbase": 3.5,
                    "cg_height": 0.8,
                    "max_roll": 8.0,
                    "max_pitch": 6.0,
                    "roll_stiffness": 15000.0,
                    "pitch_stiffness": 15000.0,
                    "bounce_stiffness": 25000.0,
                    "roll_damping": 800.0,
                    "pitch_damping": 800.0,
                    "bounce_damping": 1200.0,
                    "front_anti_roll": 1800.0,
                    "rear_anti_roll": 1500.0,
                },
                "wheels": [
                    {"position": [-1.0, 1.8, -0.4], "radius": 0.45, "can_steer": True, "is_driven": True},
                    {"position": [1.0, 1.8, -0.4], "radius": 0.45, "can_steer": True, "is_driven": True},
                    {"position": [-1.0, -1.8, -0.4], "radius": 0.45, "can_steer": False, "is_driven": True},
                    {"position": [1.0, -1.8, -0.4], "radius": 0.45, "can_steer": False, "is_driven": True},
                ],
            })
        
        # 越野车配置
        offroad = vehicles_dir / "offroad.json"
        if not offroad.exists():
            _write_v2(offroad, "offroad", {
                "name": "Off-Road",
                "position": [0, 0, 12.0],
                "heading": 0,
                "vehicle_mass": 2200.0,
                "physics": {
                    "max_speed": 160.0,
                    "drag_coefficient": 0.45,
                    "acceleration": 50.0,
                    "deceleration": 30.0,
                    "brake_deceleration": 100.0,
                    "turn_speed": 160.0,
                    "max_steering_angle": 38.0,
                    "input_smoothing": {
                        "throttle_rise": 6.0,
                        "throttle_fall": 10.0,
                        "brake_rise": 8.0,
                        "brake_fall": 12.0,
                        "steering_rise": 2.5,
                        "steering_fall": 5.0,
                    }
                },
                "suspension": {
                    "com_position": [0, 0, 0.4],
                    "wheels": [
                        {"position": [-0.95, 1.5, -0.38], "natural_frequency": 6.0, "damping_ratio": 0.9, "rest_length": 0.35, "max_compression": 0.12, "max_droop": 0.12},
                        {"position": [0.95, 1.5, -0.38], "natural_frequency": 6.0, "damping_ratio": 0.9, "rest_length": 0.35, "max_compression": 0.12, "max_droop": 0.12},
                        {"position": [-0.95, -1.5, -0.38], "natural_frequency": 6.0, "damping_ratio": 0.9, "rest_length": 0.35, "max_compression": 0.12, "max_droop": 0.12},
                        {"position": [0.95, -1.5, -0.38], "natural_frequency": 6.0, "damping_ratio": 0.9, "rest_length": 0.35, "max_compression": 0.12, "max_droop": 0.12},
                    ]
                },
                "tires": [
                    {"lat_stiff_max_load": 2.5, "lat_stiff_value": 16.0, "long_stiff_value": 900.0, "friction": 1.2},
                    {"lat_stiff_max_load": 2.5, "lat_stiff_value": 16.0, "long_stiff_value": 900.0, "friction": 1.2},
                    {"lat_stiff_max_load": 2.5, "lat_stiff_value": 16.0, "long_stiff_value": 1100.0, "friction": 1.3},
                    {"lat_stiff_max_load": 2.5, "lat_stiff_value": 16.0, "long_stiff_value": 1100.0, "friction": 1.3},
                ],
                "transmission": {
                    "engine": {
                        "moi": 1.5,
                        "max_rpm": 5500.0,
                        "torque_curve": [(0, 350), (1000, 500), (2500, 600), (4000, 550), (5000, 450), (5500, 0)],
                        "damping_full_throttle": 0.18,
                        "damping_zero_throttle_clutch_engaged": 2.5,
                        "damping_zero_throttle_clutch_disengaged": 0.4,
                    },
                    "gear_ratios": [0, 4.0, 2.8, 1.9, 1.3, 0.9, 0.75],
                    "final_ratio": 3.8,
                    "reverse_ratio": -3.8,
                    "auto_shift": True,
                    "shift_time": 0.4,
                    "clutch_strength": 12.0,
                    "differential": {
                        "diff_type": "limited_slip",
                        "front_rear_split": 0.5,
                        "front_bias": 1.3,
                        "rear_bias": 1.8,
                    }
                },
                "pose": {
                    "track_width": 1.9,
                    "wheelbase": 2.9,
                    "cg_height": 0.65,
                    "max_roll": 7.0,
                    "max_pitch": 5.0,
                    "roll_stiffness": 13500.0,
                    "pitch_stiffness": 13500.0,
                    "bounce_stiffness": 21000.0,
                    "roll_damping": 700.0,
                    "pitch_damping": 700.0,
                    "bounce_damping": 1050.0,
                    "front_anti_roll": 1650.0,
                    "rear_anti_roll": 1350.0,
                },
                "wheels": [
                    {"position": [-0.95, 1.5, -0.38], "radius": 0.4, "can_steer": True, "is_driven": True},
                    {"position": [0.95, 1.5, -0.38], "radius": 0.4, "can_steer": True, "is_driven": True},
                    {"position": [-0.95, -1.5, -0.38], "radius": 0.4, "can_steer": False, "is_driven": True},
                    {"position": [0.95, -1.5, -0.38], "radius": 0.4, "can_steer": False, "is_driven": True},
                ],
            })
    
    def load_config(self, config_type: str, name: str) -> Dict[str, Any]:
        """加载配置"""
        path = self.config_dir / config_type / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_config(self, config_type: str, name: str, config: Dict[str, Any]) -> None:
        """保存配置"""
        dir_path = self.config_dir / config_type
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / f"{name}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def list_configs(self, config_type: str) -> List[str]:
        """列出某类型的所有配置"""
        dir_path = self.config_dir / config_type
        if not dir_path.exists():
            return []
        return sorted([f.stem for f in dir_path.glob("*.json")])
    
    def delete_config(self, config_type: str, name: str) -> bool:
        """删除配置"""
        path = self.config_dir / config_type / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False
    
    def config_exists(self, config_type: str, name: str) -> bool:
        """检查配置是否存在"""
        path = self.config_dir / config_type / f"{name}.json"
        return path.exists()
