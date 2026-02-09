"""
姿态状态数据定义
"""
from dataclasses import dataclass
from .vehicle_state import Vector3

@dataclass
class PoseState:
    """车身姿态状态"""
    # 姿态角
    roll: float = 0.0              # 侧倾角 (度)
    pitch: float = 0.0            # 俯仰角 (度)
    
    # 姿态速度
    roll_velocity: float = 0.0     # 侧倾角速度 (度/秒)
    pitch_velocity: float = 0.0   # 俯仰角速度 (度/秒)
    
    # 晃动
    bounce: float = 0.0           # 上下晃动 (m)
    bounce_velocity: float = 0.0  # 晃动速度 (m/s)
    
    # 车身变换
    body_position: Vector3 = None   # 车身位置
    body_rotation: Vector3 = None   # 车身旋转 (roll, pitch, yaw)
    
    def __post_init__(self):
        if self.body_position is None:
            self.body_position = Vector3()
        if self.body_rotation is None:
            self.body_rotation = Vector3()
