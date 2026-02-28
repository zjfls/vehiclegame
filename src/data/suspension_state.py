"""
悬挂状态数据定义
"""
from dataclasses import dataclass, field
from typing import List
from .vehicle_state import Vector3

def _default_contact_normal() -> Vector3:
    return Vector3(0, 0, 1)

@dataclass
class WheelSuspensionState:
    """单个车轮的悬挂状态"""
    # 悬挂压缩
    compression: float = 0.0        # 压缩量 (-1.0 ~ 1.0, 0=静止位置)
    compression_velocity: float = 0.0  # 压缩速度
    
    # 悬挂力
    spring_force: float = 0.0       # 弹簧力 (N)
    damper_force: float = 0.0       # 阻尼力 (N)
    total_force: float = 0.0        # 总力 (N)
    
    # 车轮位置偏移
    wheel_offset: Vector3 = field(default_factory=Vector3)    # 车轮相对于车身的偏移
    
    # 接触状态
    is_in_air: bool = False         # 是否悬空
    contact_point: Vector3 = field(default_factory=Vector3)   # 接触点
    contact_normal: Vector3 = field(default_factory=_default_contact_normal)  # 接触法线

@dataclass
class SuspensionState:
    """悬挂系统状态"""
    wheels: List[WheelSuspensionState] = field(default_factory=list)
    
    def get_wheel_state(self, index: int) -> WheelSuspensionState:
        """获取指定车轮的悬挂状态"""
        if index < len(self.wheels):
            return self.wheels[index]
        return WheelSuspensionState()
