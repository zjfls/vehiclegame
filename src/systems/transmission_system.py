"""
传动系统 - 系统层
发动机、离合器、变速箱、差速器
"""
import math
from .base_system import SystemBase
from ..data.vehicle_state import VehicleState, VehicleControlInput
from ..data.transmission_state import TransmissionState, EngineConfig, DifferentialConfig

class TransmissionSystem(SystemBase):
    """传动系统"""
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        
        # 发动机配置
        engine_config = config.get('engine', {}) if config else {}
        self.engine_config = EngineConfig(**engine_config)
        
        # 档位比
        self.gear_ratios = config.get('gear_ratios', [0, 3.5, 2.5, 1.8, 1.4, 1.0]) if config else [0, 3.5, 2.5, 1.8, 1.4, 1.0]
        self.final_ratio = config.get('final_ratio', 3.5)
        self.reverse_ratio = config.get('reverse_ratio', -3.5)
        
        # 差速器配置
        diff_config = config.get('differential', {}) if config else {}
        self.diff_config = DifferentialConfig(**diff_config)
        
        # 自动换档
        self.auto_shift = config.get('auto_shift', True) if config else True
        self.shift_time = config.get('shift_time', 0.3) if config else 0.3
        
        # 离合器
        self.clutch_strength = config.get('clutch_strength', 10.0) if config else 10.0
    
    def update(self, dt: float, vehicle_state: VehicleState,
               control_input: VehicleControlInput, transmission_state: TransmissionState) -> None:
        """更新传动系统"""
        
        # 1. 处理换档
        if transmission_state.is_shifting:
            transmission_state.shift_timer -= dt
            if transmission_state.shift_timer <= 0:
                transmission_state.is_shifting = False
                transmission_state.clutch_position = 0.0
        elif self.auto_shift:
            self._auto_shift(vehicle_state, transmission_state)
        
        # 2. 计算发动机扭矩
        engine_torque = self._get_engine_torque(transmission_state.engine_rpm)
        
        # 3. 应用离合器
        clutch_factor = 1.0 - transmission_state.clutch_position
        torque_after_clutch = engine_torque * clutch_factor
        
        # 4. 通过变速箱
        gear_ratio = self.gear_ratios[transmission_state.current_gear]
        total_ratio = gear_ratio * self.final_ratio
        
        if total_ratio != 0:
            torque_after_gearbox = torque_after_clutch * total_ratio
        else:
            torque_after_gearbox = 0.0
        
        # 5. 分配到各车轮
        wheel_torques = self._distribute_torque(
            torque_after_gearbox,
            transmission_state.current_gear
        )
        
        transmission_state.wheel_torques = wheel_torques
        
        # 6. 更新发动机转速
        transmission_state.engine_rpm = self._calculate_engine_rpm(
            vehicle_state.speed,
            transmission_state.current_gear
        )
        
        # 7. 应用发动机阻尼
        self._apply_engine_damping(dt, transmission_state, control_input)
    
    def _get_engine_torque(self, rpm: float) -> float:
        """从扭矩曲线获取发动机扭矩"""
        curve = self.engine_config.torque_curve
        
        for i in range(len(curve) - 1):
            rpm1, torque1 = curve[i]
            rpm2, torque2 = curve[i + 1]
            
            if rpm1 <= rpm <= rpm2:
                if rpm2 != rpm1:
                    t = (rpm - rpm1) / (rpm2 - rpm1)
                    return torque1 + t * (torque2 - torque1)
                else:
                    return torque1
        
        if rpm < curve[0][0]:
            return curve[0][1]
        return 0.0
    
    def _distribute_torque(self, total_torque: float, gear: int) -> list:
        """分配扭矩到各车轮"""
        torques = [0.0, 0.0, 0.0, 0.0]
        
        if gear == 0:
            return torques
        
        front_torque = total_torque * self.diff_config.front_rear_split
        torques[0] = front_torque * 0.5
        torques[1] = front_torque * 0.5
        
        rear_torque = total_torque * (1.0 - self.diff_config.front_rear_split)
        torques[2] = rear_torque * 0.5
        torques[3] = rear_torque * 0.5
        
        return torques
    
    def _calculate_engine_rpm(self, speed_kmh: float, gear: int) -> float:
        """根据车速计算发动机转速"""
        if gear == 0 or gear >= len(self.gear_ratios):
            return 800.0
        
        gear_ratio = self.gear_ratios[gear]
        total_ratio = gear_ratio * self.final_ratio
        
        if total_ratio == 0:
            return 800.0
        
        speed_ms = speed_kmh / 3.6
        wheel_rpm = (speed_ms / (2 * math.pi * 0.35)) * 60
        engine_rpm = wheel_rpm * total_ratio
        
        return max(800.0, min(self.engine_config.max_rpm, engine_rpm))
    
    def _auto_shift(self, vehicle_state: VehicleState, transmission_state: TransmissionState):
        """自动换档逻辑"""
        if transmission_state.is_shifting:
            return
        
        rpm = transmission_state.engine_rpm
        max_rpm = self.engine_config.max_rpm
        current_gear = transmission_state.current_gear
        
        if rpm > max_rpm * 0.85 and current_gear < len(self.gear_ratios) - 1:
            self._shift_up(transmission_state)
        elif rpm < max_rpm * 0.35 and current_gear > 1:
            self._shift_down(transmission_state)
    
    def _shift_up(self, transmission_state: TransmissionState):
        """升档"""
        transmission_state.current_gear += 1
        transmission_state.is_shifting = True
        transmission_state.shift_timer = self.shift_time
        transmission_state.clutch_position = 1.0
    
    def _shift_down(self, transmission_state: TransmissionState):
        """降档"""
        transmission_state.current_gear -= 1
        transmission_state.is_shifting = True
        transmission_state.shift_timer = self.shift_time
        transmission_state.clutch_position = 1.0
    
    def _apply_engine_damping(self, dt: float, transmission_state: TransmissionState,
                              control_input: VehicleControlInput):
        """应用发动机阻尼"""
        if control_input.throttle > 0.1:
            damping = self.engine_config.damping_full_throttle
        elif transmission_state.clutch_position < 0.1:
            damping = self.engine_config.damping_zero_throttle_clutch_engaged
        else:
            damping = self.engine_config.damping_zero_throttle_clutch_disengaged
        
        rpm_change = -damping * dt * 10
        transmission_state.engine_rpm = max(800.0, transmission_state.engine_rpm + rpm_change)
