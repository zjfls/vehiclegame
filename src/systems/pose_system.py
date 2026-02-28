"""
姿态系统 - 系统层
计算车身的姿态（侧倾、俯仰）
"""
import math
from .base_system import SystemBase
from .update_context import SystemUpdateContext
from ..data.vehicle_state import VehicleState
from ..data.suspension_state import SuspensionState
from ..data.pose_state import PoseState
from ..data.vehicle_state import Vector3

class PoseSystem(SystemBase):
    """
    姿态系统
    
    职责：
    - 计算车身的姿态（侧倾、俯仰）
    - 基于加速度和转向计算姿态变化
    - 处理车身晃动
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        
        # 车辆参数
        self.vehicle_mass = self.config.get('vehicle_mass', 1500.0)
        self.track_width = self.config.get('track_width', 1.5)
        self.wheelbase = self.config.get('wheelbase', 2.6)
        self.cg_height = self.config.get('cg_height', 0.5)
        
        # 姿态配置
        self.max_roll = self.config.get('max_roll', 5.0)
        self.max_pitch = self.config.get('max_pitch', 3.0)
        
        self.roll_stiffness = self.config.get('roll_stiffness', 10000.0)
        self.pitch_stiffness = self.config.get('pitch_stiffness', 10000.0)
        self.bounce_stiffness = self.config.get('bounce_stiffness', 15000.0)
        
        self.roll_damping = self.config.get('roll_damping', 500.0)
        self.pitch_damping = self.config.get('pitch_damping', 500.0)
        self.bounce_damping = self.config.get('bounce_damping', 800.0)
        
        # 防倾杆
        self.front_anti_roll = self.config.get('front_anti_roll', 1000.0)
        self.rear_anti_roll = self.config.get('rear_anti_roll', 1000.0)
    
    def update(self, ctx: SystemUpdateContext) -> None:
        """更新姿态系统"""
        dt = ctx.dt
        vehicle_state = ctx.vehicle_state
        suspension_state = ctx.suspension_state
        pose_state = ctx.pose_state
        if suspension_state is None or pose_state is None:
            return
        # 1. 计算侧倾
        target_roll = self._calculate_target_roll(vehicle_state, suspension_state)
        self._update_roll(dt, target_roll, pose_state)
        
        # 2. 计算俯仰
        target_pitch = self._calculate_target_pitch(vehicle_state, suspension_state)
        self._update_pitch(dt, target_pitch, pose_state)
        
        # 3. 计算晃动
        target_bounce = self._calculate_target_bounce(suspension_state)
        self._update_bounce(dt, target_bounce, pose_state)
    
    def _calculate_target_roll(self, vehicle_state: VehicleState, 
                               suspension_state: SuspensionState) -> float:
        """计算目标侧倾角"""
        # 横向加速度
        speed_ms = vehicle_state.speed / 3.6
        steering_rad = math.radians(vehicle_state.steering_angle)
        turn_radius = self.wheelbase / math.tan(steering_rad) if abs(steering_rad) > 0.01 else 1000.0
        lateral_accel = (speed_ms ** 2) / turn_radius
        
        # 基础侧倾
        base_roll = math.degrees(math.atan2(lateral_accel, 9.81))
        
        # 悬挂差异导致的侧倾
        if len(suspension_state.wheels) >= 4:
            left_avg = (suspension_state.wheels[0].compression + 
                       suspension_state.wheels[2].compression) / 2
            right_avg = (suspension_state.wheels[1].compression + 
                        suspension_state.wheels[3].compression) / 2
            roll_from_suspension = math.degrees(math.atan2(
                (left_avg - right_avg) * 0.3,
                self.track_width
            ))
        else:
            roll_from_suspension = 0.0
        
        # 防倾杆减少侧倾
        anti_roll_effect = min(0.3, (self.front_anti_roll + self.rear_anti_roll) / 10000.0)
        
        target_roll = base_roll * (1 - anti_roll_effect) + roll_from_suspension
        return max(-self.max_roll, min(self.max_roll, target_roll))
    
    def _update_roll(self, dt: float, target_roll: float, pose_state: PoseState):
        """更新侧倾角（带阻尼）"""
        error = target_roll - pose_state.roll
        spring_torque = error * self.roll_stiffness
        damper_torque = -pose_state.roll_velocity * self.roll_damping
        total_torque = spring_torque + damper_torque
        
        moi = self.vehicle_mass * (self.track_width ** 2) / 12
        angular_accel = total_torque / moi
        
        pose_state.roll_velocity += angular_accel * dt
        pose_state.roll += pose_state.roll_velocity * dt
        pose_state.roll_velocity *= 0.95
        
        pose_state.roll = max(-self.max_roll, min(self.max_roll, pose_state.roll))
    
    def _calculate_target_pitch(self, vehicle_state: VehicleState, 
                               suspension_state: SuspensionState) -> float:
        """计算目标俯仰角"""
        # 纵向加速度
        accel = vehicle_state.acceleration.y if vehicle_state.acceleration else 0.0
        
        # 基础俯仰
        base_pitch = -math.degrees(math.atan2(accel, 9.81))
        
        # 悬挂差异导致的俯仰
        if len(suspension_state.wheels) >= 4:
            front_avg = (suspension_state.wheels[0].compression + 
                        suspension_state.wheels[1].compression) / 2
            rear_avg = (suspension_state.wheels[2].compression + 
                       suspension_state.wheels[3].compression) / 2
            pitch_from_suspension = math.degrees(math.atan2(
                (front_avg - rear_avg) * 0.3,
                self.wheelbase
            ))
        else:
            pitch_from_suspension = 0.0
        
        target_pitch = base_pitch + pitch_from_suspension
        return max(-self.max_pitch, min(self.max_pitch, target_pitch))
    
    def _update_pitch(self, dt: float, target_pitch: float, pose_state: PoseState):
        """更新俯仰角"""
        error = target_pitch - pose_state.pitch
        spring_torque = error * self.pitch_stiffness
        damper_torque = -pose_state.pitch_velocity * self.pitch_damping
        total_torque = spring_torque + damper_torque
        
        moi = self.vehicle_mass * (self.wheelbase ** 2) / 12
        angular_accel = total_torque / moi
        
        pose_state.pitch_velocity += angular_accel * dt
        pose_state.pitch += pose_state.pitch_velocity * dt
        pose_state.pitch_velocity *= 0.95
        
        pose_state.pitch = max(-self.max_pitch, min(self.max_pitch, pose_state.pitch))
    
    def _calculate_target_bounce(self, suspension_state: SuspensionState) -> float:
        """计算目标晃动"""
        if not suspension_state.wheels:
            return 0.0
        
        avg_compression = sum(w.compression for w in suspension_state.wheels) / len(suspension_state.wheels)
        return avg_compression * 0.3
    
    def _update_bounce(self, dt: float, target_bounce: float, pose_state: PoseState):
        """更新晃动"""
        error = target_bounce - pose_state.bounce
        spring_force = error * self.bounce_stiffness
        damper_force = -pose_state.bounce_velocity * self.bounce_damping
        total_force = spring_force + damper_force
        
        accel = total_force / self.vehicle_mass
        pose_state.bounce_velocity += accel * dt
        pose_state.bounce += pose_state.bounce_velocity * dt
        pose_state.bounce_velocity *= 0.95
