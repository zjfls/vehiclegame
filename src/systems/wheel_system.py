"""
车轮系统 - 系统层
管理所有车轮的状态
"""
import math
from .base_system import SystemBase
from .update_context import SystemUpdateContext
from ..data.vehicle_state import VehicleState
from ..data.wheel_state import WheelsState, WheelState
from ..data.vehicle_state import Vector3

class WheelSystem(SystemBase):
    """
    车轮系统
    
    职责：
    - 管理所有车轮的状态
    - 计算车轮的旋转角
    - 计算车轮的转向角
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        
        # 车轮配置 - 可能直接是列表
        if isinstance(config, list):
            self.wheel_configs = config
        else:
            self.wheel_configs = config.get('wheels', []) if config else []
        
        # 转向速度因子曲线
        if isinstance(config, dict):
            self.steering_speed_curve = config.get('steering_speed_curve', [
                (0, 1.0), (60, 0.8), (120, 0.6)
            ])
        else:
            self.steering_speed_curve = [(0, 1.0), (60, 0.8), (120, 0.6)]
    
    def update(self, ctx: SystemUpdateContext) -> None:
        """更新车轮系统"""
        dt = ctx.dt
        vehicle_state = ctx.vehicle_state
        wheels_state = ctx.wheels_state
        if wheels_state is None:
            return
        for i, wheel_config in enumerate(self.wheel_configs):
            if i < len(wheels_state.wheels):
                self._update_wheel(dt, vehicle_state, wheel_config, wheels_state.wheels[i])
    
    def _update_wheel(self, dt: float, vehicle_state: VehicleState,
                      wheel_config: dict, wheel_state: WheelState):
        """更新单个车轮"""
        # 车轮参数
        radius = wheel_config.get('radius', 0.35)
        can_steer = wheel_config.get('can_steer', False)
        is_driven = wheel_config.get('is_driven', False)
        
        # 1. 计算车轮旋转
        self._update_wheel_rotation(dt, vehicle_state, wheel_state, radius, is_driven)
        
        # 2. 计算车轮转向
        self._update_wheel_steering(vehicle_state, wheel_state, can_steer)
        
        # 3. 计算车轮位置
        self._update_wheel_position(vehicle_state, wheel_state, wheel_config)
    
    def _update_wheel_rotation(self, dt: float, vehicle_state: VehicleState,
                             wheel_state: WheelState, radius: float, is_driven: bool):
        """更新车轮旋转"""
        speed_ms = vehicle_state.speed / 3.6
        
        if is_driven:
            wheel_rotation_speed = (speed_ms / radius) * (180.0 / math.pi)
        else:
            wheel_rotation_speed = (speed_ms / radius) * (180.0 / math.pi) * 0.9
        
        wheel_state.rotation_speed = wheel_rotation_speed
        
        # 更新旋转角
        wheel_state.rotation_angle += wheel_rotation_speed * dt
        wheel_state.rotation_angle %= 360.0
        
        # 更新角速度
        wheel_state.angular_velocity = wheel_rotation_speed * (math.pi / 180.0)
    
    def _update_wheel_steering(self, vehicle_state: VehicleState,
                               wheel_state: WheelState, can_steer: bool):
        """更新车轮转向"""
        if can_steer:
            wheel_state.steering_angle = vehicle_state.steering_angle
        else:
            wheel_state.steering_angle = 0.0
    
    def _update_wheel_position(self, vehicle_state: VehicleState,
                              wheel_state: WheelState, wheel_config: dict):
        """更新车轮位置"""
        # 车轮相对车身位置
        local_pos = wheel_config.get('position', [0, 0, 0])
        wheel_state.local_position = Vector3.from_tuple(local_pos)
        
        # 车轮世界位置
        heading_rad = math.radians(vehicle_state.heading)
        cos_h = math.cos(heading_rad)
        sin_h = math.sin(heading_rad)
        
        # 旋转变换
        wx = local_pos[0] * cos_h + local_pos[1] * sin_h
        wy = -local_pos[0] * sin_h + local_pos[1] * cos_h
        wz = local_pos[2]
        
        wheel_state.position = Vector3(
            vehicle_state.position.x + wx,
            vehicle_state.position.y + wy,
            vehicle_state.position.z + wz
        )
        
        # 车轮速度
        wheel_state.linear_velocity = vehicle_state.velocity if vehicle_state.velocity else Vector3()
