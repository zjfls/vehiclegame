"""
车辆实体 - 业务层
协调各个子系统，管理车辆的生命周期
"""
import math
from typing import Optional
from ..data.vehicle_state import VehicleState, VehicleControlInput, Vector3
from ..data.suspension_state import SuspensionState, WheelSuspensionState
from ..data.pose_state import PoseState
from ..data.wheel_state import WheelsState
from ..data.tire_state import TiresState, TireState
from ..data.transmission_state import TransmissionState
from ..systems.update_context import SystemUpdateContext

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
        
        # Terrain query interface (set by game layer)
        self.terrain = None
        
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
    
    def unregister_system(self, name: str):
        """注销子系统（会自动调用 shutdown）"""
        system = self._systems.pop(name, None)
        if system is not None:
            try:
                system.shutdown()
            except Exception:
                pass
    
    def initialize_systems(self):
        """初始化所有已注册的子系统"""
        for name, system in self._systems.items():
            if hasattr(system, 'initialize'):
                system.initialize()
    
    def shutdown_systems(self):
        """关闭所有子系统"""
        for name, system in self._systems.items():
            if hasattr(system, 'shutdown'):
                try:
                    system.shutdown()
                except Exception:
                    pass
    
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
        tires_system = self.get_system('tires')
        use_tire_forces = bool(tires_system)

        # Build a single context object so systems can share a stable interface.
        ctx = SystemUpdateContext(
            dt=dt,
            vehicle_state=self.state,
            control_input=self.current_input,
            transmission_state=self.transmission_state,
            wheels_state=self.wheels_state,
            suspension_state=self.suspension_state,
            tires_state=self.tire_states,
            pose_state=self.pose_state,
            use_tire_forces=use_tire_forces,
            terrain=self.terrain,
        )

        physics = self.get_system('physics')

        # 1. 物理系统
        # If ctx.use_tire_forces is True, PhysicsSystem will only do input
        # smoothing + steering, and skip its simple speed/position integration.
        if physics:
            physics.update(ctx)
        
        # 2. 传动系统
        transmission = self.get_system('transmission')
        if transmission:
            transmission.update(ctx)
            self.state.engine_rpm = self.transmission_state.engine_rpm
            for i, torque in enumerate(self.transmission_state.wheel_torques):
                if i < len(self.wheels_state.wheels):
                    self.wheels_state.wheels[i].drive_torque = torque
        
        # 3. 车轮系统
        wheels = self.get_system('wheels')
        if wheels:
            wheels.update(ctx)
        
        # 4. 悬挂系统
        suspension = self.get_system('suspension')
        if suspension:
            suspension.update(ctx)
        
        # 5. 轮胎系统
        if tires_system:
            tires_system.update(ctx)
            self._apply_tire_forces(dt, integrate_position=True)
        
        # 6. 姿态系统
        pose = self.get_system('pose')
        if pose:
            pose.update(ctx)
        
        # 7. 动画系统
        animation = self.get_system('animation')
        if animation:
            animation.update(ctx)
    
    def _get_vehicle_mass_kg(self) -> float:
        cfg = self.config if isinstance(self.config, dict) else {}

        # Most examples use config['physics']['mass'].
        physics = cfg.get('physics', {}) if isinstance(cfg.get('physics', {}), dict) else {}
        mass = physics.get('mass') or physics.get('mass_kg')

        # Newer configs use config['chassis']['mass_kg'].
        chassis = cfg.get('chassis', {}) if isinstance(cfg.get('chassis', {}), dict) else {}
        mass = mass or chassis.get('mass_kg')

        mass = mass or cfg.get('mass')

        try:
            m = float(mass)
            return m if m > 1.0 else 1500.0
        except Exception:
            return 1500.0

    def _get_max_speed_kmh(self) -> float:
        cfg = self.config if isinstance(self.config, dict) else {}

        physics = cfg.get('physics', {}) if isinstance(cfg.get('physics', {}), dict) else {}
        max_speed = physics.get('max_speed') or physics.get('max_speed_kmh')

        simple = cfg.get('simple_physics', {}) if isinstance(cfg.get('simple_physics', {}), dict) else {}
        max_speed = max_speed or simple.get('max_speed_kmh')

        try:
            v = float(max_speed)
            return v if v > 0 else 0.0
        except Exception:
            return 0.0

    def _get_physics_params(self) -> dict:
        cfg = self.config if isinstance(self.config, dict) else {}
        physics = cfg.get('physics', {}) if isinstance(cfg.get('physics', {}), dict) else {}

        def f(key: str, default: float) -> float:
            try:
                return float(physics.get(key, default))
            except Exception:
                return float(default)

        return {
            'deceleration_kmhps': f('deceleration', 30.0),
            'brake_deceleration_kmhps': f('brake_deceleration', 80.0),
            'drag_coefficient': f('drag_coefficient', 0.3),
        }

    def _apply_tire_forces(self, dt: float, *, integrate_position: bool) -> None:
        """Apply computed tire forces to the vehicle's kinematic state.

        The current PhysicsSystem provides a simple baseline movement model.
        TireSystem computes forces in Newtons; without applying them here, that
        information never affects vehicle motion.
        """

        if dt <= 0:
            return

        tires = self.tire_states.tires or []
        if not tires:
            return

        total_long_force_n = float(sum(t.long_force for t in tires))
        total_lat_force_n = float(sum(t.lat_force for t in tires))

        mass_kg = self._get_vehicle_mass_kg()
        if mass_kg <= 1.0:
            return

        # Accelerations in m/s^2.
        long_accel_ms2 = total_long_force_n / mass_kg
        lat_accel_ms2 = total_lat_force_n / mass_kg

        params = self._get_physics_params()

        # Integrate longitudinal acceleration into scalar speed (km/h).
        # Keep basic resistances/braking so the vehicle remains controllable.
        speed_before_kmh = float(self.state.speed)
        speed_kmh = speed_before_kmh

        tire_accel_kmhps = long_accel_ms2 * 3.6
        extra_accel_kmhps = 0.0

        brake = float(getattr(self.state, 'brake', 0.0) or 0.0)
        throttle = float(getattr(self.state, 'throttle', 0.0) or 0.0)
        handbrake = bool(getattr(self.current_input, 'handbrake', False))

        if brake > 0.0:
            extra_accel_kmhps -= float(params['brake_deceleration_kmhps']) * max(0.0, min(1.0, brake))
        elif handbrake:
            extra_accel_kmhps -= float(params['brake_deceleration_kmhps']) * 0.8
        elif throttle <= 0.0:
            decel = float(params['deceleration_kmhps'])
            if speed_kmh > 0.0:
                extra_accel_kmhps -= decel * 0.3
            elif speed_kmh < 0.0:
                extra_accel_kmhps += decel * 0.3

        drag = 0.5 * float(params['drag_coefficient']) * speed_kmh * abs(speed_kmh) / 1000.0
        extra_accel_kmhps -= float(drag)

        self.state.speed = speed_before_kmh + (tire_accel_kmhps + extra_accel_kmhps) * dt

        # Avoid unintended "reverse" when braking or coasting down to ~0.
        # Reverse gear is not modeled yet, so crossing zero is usually a bug.
        if throttle <= 0.0:
            if speed_before_kmh >= 0.0 and self.state.speed < 0.0:
                self.state.speed = 0.0
            elif speed_before_kmh <= 0.0 and self.state.speed > 0.0:
                self.state.speed = 0.0

        # Keep speed within a reasonable range if a max speed is known.
        max_speed_kmh = self._get_max_speed_kmh()
        if max_speed_kmh > 0:
            self.state.speed = max(-max_speed_kmh * 0.5, min(max_speed_kmh, self.state.speed))

        heading_rad = math.radians(float(self.state.heading))
        fx = math.sin(heading_rad)
        fy = math.cos(heading_rad)

        if integrate_position:
            speed_ms = float(self.state.speed) / 3.6
            self.state.position.x += fx * speed_ms * dt
            self.state.position.y += fy * speed_ms * dt

        # Publish velocity/acceleration for downstream systems/UI.
        speed_ms = float(self.state.speed) / 3.6
        self.state.velocity.x = fx * speed_ms
        self.state.velocity.y = fy * speed_ms
        self.state.velocity.z = 0.0

        # World accel from vehicle-forward (fx,fy) and vehicle-right (-fy,fx).
        net_long_accel_ms2 = (float(self.state.speed) - speed_before_kmh) / max(1e-6, dt) / 3.6
        self.state.acceleration.x = fx * net_long_accel_ms2 - fy * lat_accel_ms2
        self.state.acceleration.y = fy * net_long_accel_ms2 + fx * lat_accel_ms2
        self.state.acceleration.z = 0.0

        # Keep wheel linear velocities roughly consistent.
        for w in (self.wheels_state.wheels or []):
            w.linear_velocity.x = self.state.velocity.x
            w.linear_velocity.y = self.state.velocity.y
            w.linear_velocity.z = self.state.velocity.z
    
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
