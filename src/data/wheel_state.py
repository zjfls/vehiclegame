"""
车轮状态数据定义
"""
from dataclasses import dataclass, field
from typing import List
from .vehicle_state import Vector3

@dataclass
class WheelState:
    """单个车轮状态"""
    # 车轮位置
    position: Vector3 = field(default_factory=Vector3)       # 车轮世界坐标
    local_position: Vector3 = field(default_factory=Vector3) # 车轮相对车身坐标
    
    # 车轮旋转
    rotation_angle: float = 0.0    # 车轮旋转角 (度)
    rotation_speed: float = 0.0    # 车轮旋转速度 (度/秒)
    
    # 车轮转向
    steering_angle: float = 0.0    # 转向角 (度)
    
    # 车轮速度
    linear_velocity: Vector3 = field(default_factory=Vector3)  # 线速度 (m/s)
    angular_velocity: float = 0.0    # 角速度 (rad/s)
    
    # 轮胎状态
    long_slip: float = 0.0        # 纵向打滑
    lat_slip: float = 0.0         # 侧向打滑
    tire_load: float = 0.0        # 轮胎负载 (N)
    
    # 驱动力
    drive_torque: float = 0.0     # 驱动扭矩

@dataclass
class WheelsState:
    """所有车轮状态"""
    wheels: List[WheelState] = field(default_factory=list)
    
    def get_wheel_state(self, index: int) -> WheelState:
        """获取指定车轮的状态"""
        if index < len(self.wheels):
            return self.wheels[index]
        return WheelState()
    
    def set_wheel_count(self, count: int):
        """设置车轮数量"""
        while len(self.wheels) < count:
            self.wheels.append(WheelState())
