"""
物理系统 - 系统层
计算车辆的运动学/动力学
"""
import math
from .base_system import SystemBase
from ..data.vehicle_state import VehicleState, VehicleControlInput

class PhysicsSystem(SystemBase):
    """
    物理系统
    
    职责：
    - 计算车辆的运动学/动力学
    - 计算速度、加速度、位置变化
    - 处理碰撞检测（未来）
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        
        # 车辆参数
        self.max_speed = self.config.get('max_speed', 100.0)
        self.mass = self.config.get('mass', 1500.0)
        self.drag_coefficient = self.config.get('drag_coefficient', 0.3)
        
        # 加速/减速参数
        self.acceleration = self.config.get('acceleration', 50.0)
        self.deceleration = self.config.get('deceleration', 30.0)
        self.brake_deceleration = self.config.get('brake_deceleration', 80.0)
        
        # 转向参数
        self.turn_speed = self.config.get('turn_speed', 150.0)
        self.max_steering_angle = self.config.get('max_steering_angle', 30.0)
        
        # 输入平滑
        self._init_input_smoothing()
        
        # 平滑后的输入
        self._smoothed_input = VehicleControlInput()
    
    def _init_input_smoothing(self):
        """初始化输入平滑参数"""
        smoothing_config = self.config.get('input_smoothing', {})
        
        self.throttle_smooth = {
            'current': 0.0,
            'rise_rate': smoothing_config.get('throttle_rise', 6.0),
            'fall_rate': smoothing_config.get('throttle_fall', 10.0),
        }
        
        self.brake_smooth = {
            'current': 0.0,
            'rise_rate': smoothing_config.get('brake_rise', 6.0),
            'fall_rate': smoothing_config.get('brake_fall', 10.0),
        }
        
        self.steering_smooth = {
            'current': 0.0,
            'rise_rate': smoothing_config.get('steering_rise', 2.5),
            'fall_rate': smoothing_config.get('steering_fall', 5.0),
        }
    
    def update(self, dt: float, raw_input: VehicleControlInput, state: VehicleState) -> None:
        """
        更新物理系统
        
        参数：
        - dt: 时间步长（秒）
        - raw_input: 原始控制输入
        - state: 车辆状态（会被修改）
        """
        # 1. 平滑输入
        self._smooth_input(dt, raw_input)
        
        # 2. 计算速度变化
        self._update_speed(dt, state)
        
        # 3. 计算转向
        self._update_steering(dt, state)
        
        # 4. 更新位置
        self._update_position(dt, state)
        
        # 5. 更新状态中的输入
        state.throttle = self._smoothed_input.throttle
        state.brake = self._smoothed_input.brake
        state.steering_angle = self._smoothed_input.steering * self.max_steering_angle
    
    def _smooth_input(self, dt: float, raw_input: VehicleControlInput):
        """平滑输入"""
        self._smoothed_input.throttle = self._smooth_value(
            dt,
            self.throttle_smooth,
            self._smoothed_input.throttle,
            raw_input.throttle,
            clamp_min=0.0,
            clamp_max=1.0,
        )
        self._smoothed_input.brake = self._smooth_value(
            dt,
            self.brake_smooth,
            self._smoothed_input.brake,
            raw_input.brake,
            clamp_min=0.0,
            clamp_max=1.0,
        )
        self._smoothed_input.steering = self._smooth_value(
            dt,
            self.steering_smooth,
            self._smoothed_input.steering,
            raw_input.steering,
            clamp_min=-1.0,
            clamp_max=1.0,
        )
        self._smoothed_input.handbrake = raw_input.handbrake
    
    def _smooth_value(
        self,
        dt: float,
        smooth_param: dict,
        current: float,
        target: float,
        clamp_min: float = 0.0,
        clamp_max: float = 1.0,
    ) -> float:
        """平滑单个值。

        注意：油门/刹车范围是 [0..1]，但转向需要是 [-1..1]。
        所以 clamping 范围必须由调用方指定，否则会导致左右转向不对称。
        """
        delta = target - current
        is_rising = (delta > 0) == (current > 0) or (delta != 0 and current == 0)
        
        rate = smooth_param['rise_rate'] if is_rising else smooth_param['fall_rate']
        max_delta = dt * rate
        
        result = current + max(-max_delta, min(max_delta, delta))
        return max(float(clamp_min), min(float(clamp_max), result))
    
    def _update_speed(self, dt: float, state: VehicleState):
        """更新速度"""
        accel = 0.0
        
        if self._smoothed_input.throttle > 0:
            accel = self.acceleration * self._smoothed_input.throttle
        elif self._smoothed_input.brake > 0:
            accel = -self.brake_deceleration * self._smoothed_input.brake
        elif self._smoothed_input.handbrake:
            accel = -self.brake_deceleration * 0.8
        else:
            if state.speed > 0:
                accel = -self.deceleration * 0.3
            elif state.speed < 0:
                accel = self.deceleration * 0.3
        
        # 空气阻力
        drag = 0.5 * self.drag_coefficient * state.speed * abs(state.speed) / 1000.0
        accel -= drag
        
        state.speed += accel * dt
        state.speed = max(-self.max_speed * 0.3, min(self.max_speed, state.speed))
        
        if abs(state.speed) < 0.1 and self._smoothed_input.throttle == 0:
            state.speed = 0.0
    
    def _update_steering(self, dt: float, state: VehicleState):
        """更新转向"""
        if abs(state.speed) < 0.5:
            return
        
        speed_factor = max(0.3, 1.0 - abs(state.speed) / 150.0)
        turn_rate = self.turn_speed * self._smoothed_input.steering * speed_factor
        
        state.heading += turn_rate * dt
        state.heading %= 360
    
    def _update_position(self, dt: float, state: VehicleState):
        """更新位置"""
        if abs(state.speed) < 0.1:
            return
        
        speed_ms = state.speed / 3.6
        
        heading_rad = math.radians(state.heading)
        dx = math.sin(heading_rad) * speed_ms * dt
        dy = math.cos(heading_rad) * speed_ms * dt
        
        state.position.x += dx
        state.position.y += dy
