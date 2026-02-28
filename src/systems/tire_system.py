"""
轮胎系统 - 系统层
计算轮胎力和打滑
"""
import math
from .base_system import SystemBase
from .update_context import SystemUpdateContext
from ..data.vehicle_state import VehicleState
from ..data.tire_state import TireState, TireConfig

class TireSystem(SystemBase):
    """
    轮胎系统
    
    使用简化的 Pacejka 魔术公式计算轮胎力
    
    职责：
    - 计算轮胎力（纵向力、侧向力）
    - 计算轮胎打滑
    - 处理轮胎与地面的交互
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        
        # 轮胎配置
        self.tire_configs = []
        if isinstance(config, list):
            for tire_config in config:
                self.tire_configs.append(TireConfig(**tire_config))
        elif isinstance(config, dict):
            for tire_config in config.get('tires', []):
                self.tire_configs.append(TireConfig(**tire_config))
    
    def update(self, ctx: SystemUpdateContext) -> None:
        """更新轮胎系统"""
        dt = ctx.dt
        vehicle_state = ctx.vehicle_state
        wheels_state = ctx.wheels_state
        suspension_state = ctx.suspension_state
        tires_state = ctx.tires_state
        
        # Future: Query terrain for surface type and friction
        # if ctx.terrain is not None:
        #     sample = ctx.terrain.sample(vehicle_state.position.x, vehicle_state.position.y)
        #     surface_friction = sample.friction
        
        if wheels_state is None or suspension_state is None or tires_state is None:
            return
        for i, config in enumerate(self.tire_configs):
            if i < len(tires_state.tires):
                self._update_tire(
                    dt, config, vehicle_state,
                    wheels_state.wheels[i],
                    suspension_state.wheels[i],
                    tires_state.tires[i]
                )
    
    def _update_tire(self, dt: float, config: TireConfig,
                     vehicle_state: VehicleState, wheel_state,
                     suspension_state, tire_state: TireState):
        """更新单个轮胎"""
        
        # 1. 计算轮胎负载（基于悬挂力）
        gravity = 9.81
        wheel_mass = 20.0  # 车轮质量 kg
        
        # 静止时轮胎负载
        # SuspensionSystem uses a negative spring_force value for upward support.
        suspension_support = max(0.0, -float(getattr(suspension_state, "spring_force", 0.0)))
        tire_state.rest_tire_load = wheel_mass * gravity + suspension_support
        tire_state.tire_load = tire_state.rest_tire_load
        tire_state.normalized_tire_load = 1.0
        if tire_state.rest_tire_load > 0:
            tire_state.normalized_tire_load = tire_state.tire_load / tire_state.rest_tire_load
        
        # 如果车轮悬空，负载为0
        if suspension_state.is_in_air:
            tire_state.tire_load = 0.0
            tire_state.long_force = 0.0
            tire_state.lat_force = 0.0
            tire_state.wheel_torque = 0.0
            return
        
        # 2. 计算纵向打滑
        # longSlip = (wheelSpeed - groundSpeed) / groundSpeed
        wheel_circumference = 2 * math.pi * 0.35  # 假设半径 0.35m
        wheel_angular_speed = wheel_state.angular_velocity  # rad/s
        wheel_linear_speed = wheel_angular_speed * 0.35  # m/s
        
        vehicle_speed = vehicle_state.speed / 3.6  # km/h to m/s
        
        if vehicle_speed > 0.1:
            tire_state.long_slip = (wheel_linear_speed - vehicle_speed) / vehicle_speed
        else:
            # 低速时简化处理
            tire_state.long_slip = wheel_linear_speed - vehicle_speed
        
        # 3. 计算侧向打滑
        # latSlip = atan(lateralVelocity / forwardVelocity)
        # 简化：使用转向角和速度估计
        steering_rad = math.radians(vehicle_state.steering_angle)
        speed_factor = min(1.0, vehicle_state.speed / 100.0)
        
        # 侧向打滑与转向角和速度相关
        if wheel_state.steering_angle != 0:
            # 转向轮有额外的侧向打滑
            tire_state.lat_slip = math.radians(wheel_state.steering_angle) * 0.3 * speed_factor
        else:
            # 根据车辆横向速度估计（简化）
            tire_state.lat_slip = steering_rad * 0.1 * speed_factor
        
        # 4. 计算轮胎力
        # Longitudinal: derive requested force from drive torque, clamp by friction.
        wheel_radius = 0.35
        max_friction = float(config.friction) * float(tire_state.tire_load)
        requested_long = float(getattr(wheel_state, "drive_torque", 0.0)) / wheel_radius
        tire_state.long_force = max(-max_friction, min(max_friction, requested_long))

        # Lateral: keep simplified Pacejka estimate, then apply a friction circle.
        lat = self._pacejka_formula(
            tire_state.lat_slip,
            tire_state.tire_load,
            config.friction,
            config.lat_stiff_value,
        )
        remaining = max(0.0, max_friction * max_friction - float(tire_state.long_force) ** 2)
        max_lat = math.sqrt(remaining) if remaining > 0.0 else 0.0
        tire_state.lat_force = max(-max_lat, min(max_lat, float(lat)))
        
        # 5. 计算车轮扭矩（纵向力的反作用力）
        tire_state.wheel_torque = -tire_state.long_force * wheel_radius
        
        # 6. 计算回正力矩（简化）
        pneumatic_trail = 0.02  # 气胎拖距 2cm
        tire_state.align_moment = tire_state.lat_force * pneumatic_trail
    
    def _pacejka_formula(self, slip: float, load: float, friction: float, stiffness: float) -> float:
        """
        简化的 Pacejka 魔术公式
        
        y = D * sin(C * arctan(B*x - E*(B*x - arctan(B*x))))
        
        参数：
        - B: 刚度因子
        - C: 形状因子
        - D: 峰值因子 (friction * load)
        - E: 曲率因子
        """
        if load <= 0:
            return 0.0
        
        # Pacejka 参数
        B = stiffness / (friction * load) if (friction * load) > 0 else 1.0
        C = 1.9
        D = friction * load
        E = 0.97
        
        # 计算
        Bx = B * slip
        inner = Bx - E * (Bx - math.atan(Bx))
        force = D * math.sin(C * math.atan(inner))
        
        return force
    
    def _smoothing_function1(self, K: float) -> float:
        """平滑函数1"""
        return min(1.0, K - (1.0/3.0) * K * K + (1.0/27.0) * K * K * K)
