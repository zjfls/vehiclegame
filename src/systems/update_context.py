"""System update context.

The project originally defined ISystem.update(self, dt: float) but most concrete
systems require additional inputs/state. To keep a single, statically-checkable
interface, we pass a single context object to every system update.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from ..data.pose_state import PoseState
from ..data.suspension_state import SuspensionState
from ..data.tire_state import TiresState
from ..data.transmission_state import TransmissionState
from ..data.vehicle_state import VehicleControlInput, VehicleState
from ..data.wheel_state import WheelsState


@dataclass(slots=True)
class SystemUpdateContext:
    dt: float
    vehicle_state: VehicleState

    # Optional payloads. VehicleEntity populates these for per-vehicle updates.
    control_input: Optional[VehicleControlInput] = None
    transmission_state: Optional[TransmissionState] = None
    wheels_state: Optional[WheelsState] = None
    suspension_state: Optional[SuspensionState] = None
    tires_state: Optional[TiresState] = None
    pose_state: Optional[PoseState] = None

    # When True, the game should treat tire forces as the primary source of
    # longitudinal/lateral acceleration and avoid using the simple speed model.
    use_tire_forces: bool = False

    # Terrain query interface for suspension/tire systems.
    # Set to NullTerrainQuery() by default; game layer should provide actual terrain.
    # Systems should check 'terrain is not None' before using.
    terrain: Optional["ITerrainQuery"] = None

    # Future extensibility: weather, damage, AI context, etc.
    # can be added here without changing system signatures.
