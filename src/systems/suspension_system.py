"""
悬挂系统 - 系统层
计算每个车轮的悬挂压缩量和力
"""
import math
from .base_system import SystemBase
from .update_context import SystemUpdateContext
from ..data.suspension_state import WheelSuspensionState
from ..data.vehicle_state import VehicleState
from ..data.vehicle_state import Vector3

class SuspensionSystem(SystemBase):
    """
    悬挂系统
    
    职责：
    - 计算每个车轮的悬挂压缩量
    - 计算悬挂力（弹力 + 阻尼）
    - 处理悬挂的上下运动
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        
        # 悬挂配置
        self.vehicle_mass = self.config.get('vehicle_mass', 1500.0)
        com_pos = self.config.get('com_position', [0, 0, 0.3])
        if isinstance(com_pos, list):
            self.com_position = Vector3.from_tuple(tuple(com_pos))
        else:
            self.com_position = com_pos
        
        # 车轮配置
        self.wheel_configs = self.config.get('wheels', [])
        
        # 默认参数
        self.default_natural_frequency = 7.0
        self.default_damping_ratio = 1.0
        self.default_rest_length = 0.3
        self.default_max_compression = 0.1
        self.default_max_droop = 0.1
        
        # 计算簧载质量
        self.sprung_masses = self._compute_sprung_masses()
    
    def _compute_sprung_masses(self) -> list:
        """
        计算每个车轮的簧载质量
        
        算法：根据车轮位置相对于质心的距离分配质量
        """
        num_wheels = len(self.wheel_configs)
        if num_wheels == 0:
            return []
        
        sprung_masses = []
        total_inverse_distance = 0.0
        inverse_distances = []
        
        for config in self.wheel_configs:
            wheel_pos = config.get('position', [0, 0, 0])
            com_pos = self.com_position.to_tuple()
            
            # 计算车轮到质心的水平距离
            distance = math.sqrt(
                (wheel_pos[0] - com_pos[0]) ** 2 +
                (wheel_pos[1] - com_pos[1]) ** 2
            )
            distance = max(0.1, distance)
            inverse_distance = 1.0 / distance
            inverse_distances.append(inverse_distance)
            total_inverse_distance += inverse_distance
        
        # 分配质量
        for inv_dist in inverse_distances:
            sprung_mass = self.vehicle_mass * (inv_dist / total_inverse_distance)
            sprung_masses.append(sprung_mass)
        
        return sprung_masses
    
    def update(self, ctx: SystemUpdateContext) -> None:
        """更新悬挂系统"""
        dt = ctx.dt
        vehicle_state = ctx.vehicle_state
        wheels_state = ctx.wheels_state
        suspension_state = ctx.suspension_state
        
        # Future: Query terrain height/normal for ground contact
        # if ctx.terrain is not None:
        #     ground_height = ctx.terrain.sample_height(vehicle_state.position.x, vehicle_state.position.y)
        #     ground_normal = ctx.terrain.sample_normal(vehicle_state.position.x, vehicle_state.position.y)
        
        if wheels_state is None or suspension_state is None:
            return
        for i, config in enumerate(self.wheel_configs):
            if i < len(suspension_state.wheels) and i < len(self.sprung_masses):
                self._update_wheel_suspension(
                    dt, config, self.sprung_masses[i],
                    vehicle_state, wheels_state.wheels[i],
                    suspension_state.wheels[i]
                )
    
    def _update_wheel_suspension(self, dt: float, wheel_config: dict, sprung_mass: float,
                                  vehicle_state: VehicleState, wheel_state, suspension_state: WheelSuspensionState):
        """更新单个车轮的悬挂"""
        # 获取悬挂参数
        natural_frequency = wheel_config.get('natural_frequency', self.default_natural_frequency)
        damping_ratio = wheel_config.get('damping_ratio', self.default_damping_ratio)
        rest_length = wheel_config.get('rest_length', self.default_rest_length)
        max_compression = wheel_config.get('max_compression', self.default_max_compression)
        max_droop = wheel_config.get('max_droop', self.default_max_droop)
        
        # 1. 计算弹簧刚度
        spring_stiffness = (natural_frequency ** 2) * sprung_mass
        
        # 2. 计算阻尼率
        damper_rate = damping_ratio * 2.0 * math.sqrt(spring_stiffness * sprung_mass)
        
        # 3. 计算基础压缩（重力导致）
        gravity = 9.81
        base_compression = (sprung_mass * gravity) / spring_stiffness
        
        # 4. 计算动态压缩（加速度导致）
        vertical_accel = vehicle_state.acceleration.z if vehicle_state.acceleration else 0.0
        dynamic_compression = (sprung_mass * vertical_accel) / spring_stiffness
        
        # 5. 计算压缩速度影响
        wheel_vertical_velocity = wheel_state.linear_velocity.z if wheel_state.linear_velocity else 0.0
        velocity_compression = (wheel_vertical_velocity * damper_rate) / spring_stiffness
        
        # 6. 总压缩
        total_compression = base_compression + dynamic_compression + velocity_compression
        
        # 7. 限制压缩范围
        total_compression = max(-max_droop, min(max_compression, total_compression))
        
        # 8. 计算压缩速度
        old_compression = suspension_state.compression
        compression_velocity = (total_compression - old_compression) / dt if dt > 0 else 0.0
        
        # 9. 计算悬挂力
        spring_force = -spring_stiffness * total_compression
        damper_force = -damper_rate * compression_velocity
        total_force = spring_force + damper_force
        
        # 10. 更新状态
        suspension_state.compression = total_compression
        suspension_state.compression_velocity = compression_velocity
        suspension_state.spring_force = spring_force
        suspension_state.damper_force = damper_force
        suspension_state.total_force = total_force
        
        # 11. 计算车轮偏移
        suspension_state.wheel_offset = Vector3(0, 0, -total_compression)
        
        # 12. 判断是否悬空
        # compression > 0 means the suspension is compressed (wheel is pushing into the body).
        # Going "in air" should correspond to reaching max droop / extension.
        suspension_state.is_in_air = total_compression <= -max_droop * 0.99
