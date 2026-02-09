"""
车辆状态数据定义
纯数据结构，无业务逻辑
"""
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Vector3:
    """3D 向量"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    @staticmethod
    def from_tuple(t: Tuple[float, float, float]) -> 'Vector3':
        return Vector3(t[0], t[1], t[2])
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

@dataclass
class VehicleControlInput:
    """车辆控制输入"""
    throttle: float = 0.0      # 油门 (0.0 ~ 1.0)
    brake: float = 0.0         # 刹车 (0.0 ~ 1.0)
    steering: float = 0.0      # 转向 (-1.0 ~ 1.0)
    handbrake: bool = False     # 手刹
    gear_up: bool = False       # 升档
    gear_down: bool = False     # 降档
    clutch: float = 0.0         # 离合器 (0.0 ~ 1.0)

@dataclass
class VehicleState:
    """车辆物理状态"""
    # 位置和旋转
    position: Vector3 = None
    heading: float = 0.0          # 航向角 (度)
    
    # 运动状态
    velocity: Vector3 = None
    speed: float = 0.0            # 速度 (km/h)
    acceleration: Vector3 = None
    
    # 转向状态
    steering_angle: float = 0.0   # 转向角 (度)
    
    # 发动机状态
    engine_rpm: float = 800.0     # 发动机转速
    throttle: float = 0.0         # 油门 (0.0 ~ 1.0)
    brake: float = 0.0            # 刹车 (0.0 ~ 1.0)
    
    def __post_init__(self):
        if self.position is None:
            self.position = Vector3()
        if self.velocity is None:
            self.velocity = Vector3()
        if self.acceleration is None:
            self.acceleration = Vector3()
