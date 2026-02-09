"""
车辆实体 - 业务层
协调各个子系统，管理车辆的生命周期
"""
from typing import Optional
from ..data.vehicle_state import VehicleState, VehicleControlInput, Vector3
from ..data.suspension_state import SuspensionState, WheelSuspensionState
from ..data.pose_state import PoseState
from ..data.wheel_state import WheelsState
from ..data.tire_state import TiresState, TireState
from ..data.transmission_state import TransmissionState

class VehicleEntity:
    """
    车辆实体
    
    职责：
    - 协调各个子系统
    - 管理车辆状态
    - 提供统一的接口
    """
    
    def __init__(self, vehicle_id: str, config: dict):
        self.vehicle_id = vehicle_id
        self.config = config
        
        # 车辆状态
        self.state = VehicleState()
        self.suspension_state = SuspensionState()
        self.pose_state = PoseState()
        self.wheels_state = WheelsState()
        self.tire_states = TiresState()
        self.transmission_state = TransmissionState()
        
        # 控制输入
        self.current_input = VehicleControlInput()
        
        # 子系统
        self._systems = {}
        
        # 初始化状态
        self._initialize_state()
    
    def _initialize_state(self):
        """初始化车辆状态"""
        # 从配置读取初始位置
        initial_pos = self.config.get('position', [0, 0, 0])
        self.state.position = Vector3.from_tuple(initial_pos)
        self.state.heading = self.config.get('heading', 0.0)
        
        # 初始化车轮数量
        wheel_configs = self.config.get('wheels', [])
        self.wheels_state.set_wheel_count(len(wheel_configs))
        
        # 初始化轮胎数量
        self.tire_states.set_tire_count(len(wheel_configs))
        
        # 初始化悬挂状态
        for wheel_config in wheel_configs:
            wheel_suspension = WheelSuspensionState()
            self.suspension_state.wheels.append(wheel_suspension)
        
        # 初始化传动状态
        self.transmission_state.current_gear = 1
    
    def register_system(self, name: str, system):
        """注册子系统"""
        self._systems[name] = system
    
    def get_system(self, name: str):
        """获取子系统"""
        return self._systems.get(name)
    
    def update(self, dt: float):
        """
        更新车辆
        
        系统更新顺序：
        1. PhysicsSystem - 计算基础运动
        2. TransmissionSystem - 计算发动机扭矩
        3. WheelSystem - 计算车轮
        4. SuspensionSystem - 计算悬挂
        5. TireSystem - 计算轮胎力
        6. PoseSystem - 计算姿态
        7. AnimationSystem - 驱动动画
        """
        # 1. 物理系统
        physics = self.get_system('physics')
        if physics:
            physics.update(dt, self.current_input, self.state)
        
        # 2. 传动系统
        transmission = self.get_system('transmission')
        if transmission:
            transmission.update(dt, self.state, self.current_input, self.transmission_state)
            self.state.engine_rpm = self.transmission_state.engine_rpm
            for i, torque in enumerate(self.transmission_state.wheel_torques):
                if i < len(self.wheels_state.wheels):
                    self.wheels_state.wheels[i].drive_torque = torque
        
        # 3. 车轮系统
        wheels = self.get_system('wheels')
        if wheels:
            wheels.update(dt, self.state, self.wheels_state)
        
        # 4. 悬挂系统
        suspension = self.get_system('suspension')
        if suspension:
            suspension.update(dt, self.state, self.wheels_state, self.suspension_state)
        
        # 5. 轮胎系统
        tires = self.get_system('tires')
        if tires:
            tires.update(dt, self.state, self.wheels_state, self.suspension_state, self.tire_states)
            self._apply_tire_forces()
        
        # 6. 姿态系统
        pose = self.get_system('pose')
        if pose:
            pose.update(dt, self.state, self.suspension_state, self.pose_state)
        
        # 7. 动画系统
        animation = self.get_system('animation')
        if animation:
            animation.update(dt, self.state, self.pose_state, self.suspension_state, self.wheels_state)
    
    def _apply_tire_forces(self):
        """将轮胎力应用到车辆运动"""
        total_long_force = sum(t.long_force for t in self.tire_states.tires)
        # 简化处理，实际应该更复杂
    
    # ========== 状态获取接口 ==========
    
    def get_state(self) -> VehicleState:
        """获取车辆状态"""
        return self.state
    
    def get_suspension_state(self) -> SuspensionState:
        """获取悬挂状态"""
        return self.suspension_state
    
    def get_wheel_suspension_state(self, index: int):
        """获取指定车轮的悬挂状态"""
        return self.suspension_state.get_wheel_state(index)
    
    def get_pose_state(self) -> PoseState:
        """获取姿态状态"""
        return self.pose_state
    
    def get_wheels_state(self) -> WheelsState:
        """获取车轮状态"""
        return self.wheels_state
    
    def get_tire_states(self) -> TiresState:
        """获取轮胎状态"""
        return self.tire_states
    
    def get_transmission_state(self) -> TransmissionState:
        """获取传动状态"""
        return self.transmission_state
    
    # ========== 控制输入接口 ==========
    
    def set_throttle(self, value: float):
        """设置油门 (0.0 ~ 1.0)"""
        self.current_input.throttle = max(0.0, min(1.0, value))
    
    def set_brake(self, value: float):
        """设置刹车 (0.0 ~ 1.0)"""
        self.current_input.brake = max(0.0, min(1.0, value))
    
    def set_steering(self, value: float):
        """设置转向 (-1.0 ~ 1.0)"""
        self.current_input.steering = max(-1.0, min(1.0, value))
    
    def set_handbrake(self, value: bool):
        """设置手刹"""
        self.current_input.handbrake = value
    
    def set_gear_up(self):
        """升档（手动模式）"""
        self.current_input.gear_up = True
    
    def set_gear_down(self):
        """降档（手动模式）"""
        self.current_input.gear_down = True
    
    def get_control_input(self) -> VehicleControlInput:
        """获取当前控制输入"""
        return self.current_input
    
    # ========== 位置和变换 ==========
    
    def get_position(self) -> Vector3:
        """获取位置"""
        return self.state.position
    
    def get_heading(self) -> float:
        """获取航向角"""
        return self.state.heading
    
    def get_speed(self) -> float:
        """获取速度 (km/h)"""
        return self.state.speed
    
    def get_body_transform(self):
        """获取车身变换（包含姿态）"""
        return {
            'position': self.state.position,
            'heading': self.state.heading,
            'roll': self.pose_state.roll,
            'pitch': self.pose_state.pitch,
            'bounce': self.pose_state.bounce,
        }
