 # 业务模型到代码映射
 
 ## 概述
 
 本文档将 PhysXVehicles 的业务模型映射到 Panda3D 项目的代码实现。
 
 ## 一、悬挂系统实现
 
 ### 1.1 数据模型
 
 ```python
 # src/data/suspension_state.py
 @dataclass
 class WheelSuspensionConfig:
     """单个车轮的悬挂配置"""
     # 位置
     position: Vector3           # 车轮相对车身位置
     
     # 弹簧参数
     natural_frequency: float    # 自然频率 (Hz), 典型值 5-10
     damping_ratio: float        # 阻尼比, 典型值 0.8-1.2
     max_compression: float      # 最大压缩量 (m)
     max_droop: float            # 最大伸长量 (m)
     
     # 力的应用点偏移
     force_offset: float         # 悬挂力应用点垂直偏移
 
 @dataclass
 class WheelSuspensionState:
     """单个车轮的悬挂状态"""
     # 动态状态
     compression: float          # 当前压缩量 (m, 正=压缩, 负=伸长)
     compression_velocity: float # 压缩速度 (m/s)
     
     # 计算结果
     spring_force: float         # 弹簧力 (N)
     damper_force: float         # 阻尼力 (N)
     total_force: float          # 总悬挂力 (N)
     
     # 几何
     wheel_offset: Vector3       # 车轮相对于静止位置的偏移
     
     # 接触
     is_in_air: bool             # 是否悬空
     contact_point: Vector3      # 地面接触点
 ```
 
 ### 1.2 系统实现
 
 ```python
 # src/systems/suspension_system.py
 class SuspensionSystem(SystemBase):
     """
     悬挂系统实现
     
     核心算法：
     1. 计算簧载质量（Sprung Mass）
     2. 计算弹簧刚度
     3. 计算悬挂力
     4. 计算车轮偏移
     """
     
     def __init__(self, config: dict):
         super().__init__(config)
         
         # 全局参数
         self.vehicle_mass = config.get('vehicle_mass', 1500.0)
         self.com_position = config.get('com_position', Vector3(0, 0, 0.3))
         
         # 车轮配置
         self.wheel_configs = []
         for wheel_config in config.get('wheels', []):
             self.wheel_configs.append(WheelSuspensionConfig(**wheel_config))
         
         # 计算簧载质量
         self.sprung_masses = self._compute_sprung_masses()
     
     def _compute_sprung_masses(self) -> List[float]:
         """
         计算每个车轮的簧载质量
         
         算法：根据车轮位置相对于质心的距离分配质量
         """
         num_wheels = len(self.wheel_configs)
         sprung_masses = []
         
         # 简化算法：按距离质心的反比分配
         total_inverse_distance = 0.0
         inverse_distances = []
         
         for config in self.wheel_configs:
             # 计算车轮到质心的距离
             wheel_pos = config.position
             com_pos = self.com_position
             distance = math.sqrt(
                 (wheel_pos.x - com_pos.x) ** 2 +
                 (wheel_pos.y - com_pos.y) ** 2
             )
             # 避免除零
             distance = max(0.1, distance)
             inverse_distance = 1.0 / distance
             inverse_distances.append(inverse_distance)
             total_inverse_distance += inverse_distance
         
         # 分配质量
         for inv_dist in inverse_distances:
             sprung_mass = self.vehicle_mass * (inv_dist / total_inverse_distance)
             sprung_masses.append(sprung_mass)
         
         return sprung_masses
     
     def update(self, dt: float, vehicle_state, wheels_state, suspension_state):
         """
         更新悬挂系统
         
         流程：
         1. 对每个车轮计算悬挂状态
         2. 更新悬挂状态数据
         """
         for i, config in enumerate(self.wheel_configs):
             if i < len(suspension_state.wheels):
                 self._update_wheel_suspension(
                     dt, config, self.sprung_masses[i],
                     vehicle_state, wheels_state.wheels[i],
                     suspension_state.wheels[i]
                 )
     
     def _update_wheel_suspension(self, dt, config, sprung_mass, 
                                   vehicle_state, wheel_state, suspension_state):
         """更新单个车轮的悬挂"""
         
         # 1. 计算弹簧刚度
         # spring_strength = (natural_frequency)² × sprung_mass
         spring_stiffness = (config.natural_frequency ** 2) * sprung_mass
         
         # 2. 计算阻尼率
         # damper_rate = damping_ratio × 2 × √(spring_strength × sprung_mass)
         damper_rate = config.damping_ratio * 2.0 * math.sqrt(spring_stiffness * sprung_mass)
         
         # 3. 计算基础压缩（重力导致）
         gravity = 9.81
         base_compression = (sprung_mass * gravity) / spring_stiffness
         
         # 4. 计算动态压缩（加速度导致）
         # 简化：使用车辆垂直加速度
         vertical_accel = vehicle_state.acceleration.z if vehicle_state.acceleration else 0.0
         dynamic_compression = (sprung_mass * vertical_accel) / spring_stiffness
         
         # 5. 计算压缩速度影响
         # 车轮垂直速度
         wheel_vertical_velocity = wheel_state.linear_velocity.z if wheel_state.linear_velocity else 0.0
         velocity_compression = (wheel_vertical_velocity * damper_rate) / spring_stiffness
         
         # 6. 总压缩
         total_compression = base_compression + dynamic_compression + velocity_compression
         
         # 7. 限制压缩范围
         total_compression = max(-config.max_droop, min(config.max_compression, total_compression))
         
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
         
         # 11. 计算车轮偏移（只考虑垂直方向）
         suspension_state.wheel_offset = Vector3(0, 0, -total_compression)
         
         # 12. 判断是否悬空
         suspension_state.is_in_air = abs(total_compression) >= config.max_compression * 0.99
 ```
 
 ## 二、轮胎系统实现
 
 ### 2.1 数据模型
 
 ```python
 # src/data/tire_state.py
 @dataclass
 class TireConfig:
     """轮胎配置"""
     # 侧向刚度
     lat_stiff_max_load: float    # 最大负载时的侧向刚度
     lat_stiff_value: float       # 侧向刚度值
     
     # 纵向刚度
     long_stiff_value: float      # 纵向刚度
     
     # 摩擦
     friction: float              # 摩擦系数
 
 @dataclass
 class TireState:
     """轮胎状态"""
     # 打滑
     long_slip: float             # 纵向打滑率
     lat_slip: float              # 侧向打滑角（弧度）
     
     # 力
     long_force: float            # 纵向力 (N)
     lat_force: float             # 侧向力 (N)
     align_moment: float          # 回正力矩 (Nm)
     
     # 负载
     tire_load: float             # 轮胎负载 (N)
     normalized_tire_load: float  # 归一化负载
 ```
 
 ### 2.2 系统实现（简化 Pacejka 模型）
 
 ```python
 # src/systems/tire_system.py
 class TireSystem(SystemBase):
     """
     轮胎系统实现
     
     使用简化的 Pacejka 魔术公式计算轮胎力
     """
     
     def __init__(self, config: dict):
         super().__init__(config)
         self.tire_configs = []
         for tire_config in config.get('tires', []):
             self.tire_configs.append(TireConfig(**tire_config))
     
     def update(self, dt, vehicle_state, wheels_state, suspension_state, tire_states):
         """更新轮胎系统"""
         for i, config in enumerate(self.tire_configs):
             if i < len(tire_states):
                 self._update_tire(
                     dt, config, vehicle_state, 
                     wheels_state.wheels[i], 
                     suspension_state.wheels[i],
                     tire_states[i]
                 )
     
     def _update_tire(self, dt, config, vehicle_state, wheel_state, 
                      suspension_state, tire_state):
         """更新单个轮胎"""
         
         # 1. 计算轮胎负载（基于悬挂力）
         rest_tire_load = suspension_state.spring_force + 9.81 * 375  # 简化的静态负载
         tire_state.tire_load = rest_tire_load
         tire_state.normalized_tire_load = tire_state.tire_load / rest_tire_load if rest_tire_load > 0 else 1.0
         
         # 2. 计算纵向打滑
         # longSlip = (wheelSpeed - groundSpeed) / groundSpeed
         wheel_speed = wheel_state.angular_velocity * 0.35  # 假设半径 0.35m
         vehicle_speed = vehicle_state.speed / 3.6  # km/h to m/s
         if vehicle_speed > 0.1:
             tire_state.long_slip = (wheel_speed - vehicle_speed) / vehicle_speed
         else:
             tire_state.long_slip = 0.0
         
         # 3. 计算侧向打滑
         # latSlip = atan(lateralVelocity / forwardVelocity)
         # 简化：使用转向角估计
         steering_rad = math.radians(vehicle_state.steering_angle)
         speed_factor = min(1.0, vehicle_state.speed / 100.0)
         tire_state.lat_slip = steering_rad * speed_factor
         
         # 4. 使用 Pacejka 公式计算轮胎力
         tire_state.long_force = self._pacejka_formula(
             tire_state.long_slip, 
             tire_state.tire_load, 
             config.friction,
             config.long_stiff_value
         )
         
         tire_state.lat_force = self._pacejka_formula(
             tire_state.lat_slip,
             tire_state.tire_load,
             config.friction,
             config.lat_stiff_value
         )
         
         # 5. 计算回正力矩（简化）
         tire_state.align_moment = tire_state.lat_force * 0.02  # 假设气胎拖距 2cm
     
     def _pacejka_formula(self, slip, load, friction, stiffness):
         """
         简化的 Pacejka 魔术公式
         
         B: 刚度因子
         C: 形状因子
         D: 峰值因子 (friction * load)
         E: 曲率因子
         """
         B = stiffness / (friction * load) if load > 0 else 1.0
         C = 1.9
         D = friction * load
         E = 0.97
         
         # y = D * sin(C * arctan(B*x - E*(B*x - arctan(B*x))))
         Bx = B * slip
         force = D * math.sin(C * math.atan(Bx - E * (Bx - math.atan(Bx))))
         
         return force
 ```
 
 ## 三、传动系统实现
 
 ### 3.1 数据模型
 
 ```python
 # src/data/transmission_state.py
 @dataclass
 class EngineConfig:
     """发动机配置"""
     moi: float                   # 转动惯量 (kg*m²)
     max_rpm: float               # 最大转速
     torque_curve: List[Tuple[float, float]]  # [(RPM, Torque), ...]
     damping_full_throttle: float # 全油门阻尼
     damping_zero_throttle_clutch_engaged: float
     damping_zero_throttle_clutch_disengaged: float
 
 @dataclass
 class GearConfig:
     """档位配置"""
     ratio: float                 # 传动比
     up_ratio: float              # 升档转速比
     down_ratio: float            # 降档转速比
 
 @dataclass
 class DifferentialConfig:
     """差速器配置"""
     diff_type: str               # 类型: 'open', 'limited_slip'
     front_rear_split: float      # 前后扭矩分配
     front_bias: float            # 前轴限滑比
     rear_bias: float             # 后轴限滑比
 
 @dataclass
 class TransmissionState:
     """传动状态"""
     engine_rpm: float            # 发动机转速
     current_gear: int            # 当前档位
     clutch_position: float       # 离合器位置 (0-1)
     wheel_torques: List[float]   # 各车轮扭矩
 ```
 
 ### 3.2 系统实现
 
 ```python
 # src/systems/transmission_system.py
 class TransmissionSystem(SystemBase):
     """
     传动系统实现
     
     包含：发动机、离合器、变速箱、差速器
     """
     
     def __init__(self, config: dict):
         super().__init__(config)
         
         # 发动机
         engine_config = config.get('engine', {})
         self.engine_config = EngineConfig(**engine_config)
         
         # 档位
         self.gear_ratios = config.get('gear_ratios', [0, 3.5, 2.5, 1.8, 1.4, 1.0])
         self.final_ratio = config.get('final_ratio', 3.5)
         self.reverse_ratio = config.get('reverse_ratio', -3.5)
         
         # 差速器
         diff_config = config.get('differential', {})
         self.front_rear_split = diff_config.get('front_rear_split', 0.5)
         
         # 自动换档
         self.auto_shift = config.get('auto_shift', True)
         self.shift_time = 0.0
         self.is_shifting = False
     
     def update(self, dt, vehicle_state, control_input):
         """更新传动系统"""
         
         # 1. 计算发动机扭矩
         engine_torque = self._get_engine_torque(vehicle_state.engine_rpm)
         
         # 2. 应用离合器
         clutch_factor = 1.0 - control_input.clutch
         torque_after_clutch = engine_torque * clutch_factor
         
         # 3. 通过变速箱
         gear_ratio = self.gear_ratios[vehicle_state.current_gear]
         total_ratio = gear_ratio * self.final_ratio
         torque_after_gearbox = torque_after_clutch * total_ratio
         
         # 4. 分配到各车轮
         wheel_torques = self._distribute_torque(
             torque_after_gearbox, 
             vehicle_state.current_gear
         )
         
         # 5. 更新发动机转速
         vehicle_state.engine_rpm = self._calculate_engine_rpm(
             vehicle_state.speed, 
             vehicle_state.current_gear
         )
         
         # 6. 自动换档
         if self.auto_shift and not self.is_shifting:
             self._auto_shift(vehicle_state)
         
         return wheel_torques
     
     def _get_engine_torque(self, rpm: float) -> float:
         """从扭矩曲线获取发动机扭矩"""
         curve = self.engine_config.torque_curve
         
         # 查找 RPM 所在区间
         for i in range(len(curve) - 1):
             rpm1, torque1 = curve[i]
             rpm2, torque2 = curve[i + 1]
             
             if rpm1 <= rpm <= rpm2:
                 # 线性插值
                 t = (rpm - rpm1) / (rpm2 - rpm1)
                 return torque1 + t * (torque2 - torque1)
         
         # 超出范围
         if rpm < curve[0][0]:
             return curve[0][1]
         return 0.0  # 超过最大 RPM
     
     def _distribute_torque(self, total_torque: float, gear: int) -> List[float]:
         """分配扭矩到各车轮"""
         torques = [0.0, 0.0, 0.0, 0.0]  # FL, FR, RL, RR
         
         if gear == 0:  # 空档
             return torques
         
         # 前轴扭矩
         front_torque = total_torque * self.front_rear_split
         torques[0] = front_torque * 0.5  # 左前
         torques[1] = front_torque * 0.5  # 右前
         
         # 后轴扭矩
         rear_torque = total_torque * (1.0 - self.front_rear_split)
         torques[2] = rear_torque * 0.5   # 左后
         torques[3] = rear_torque * 0.5   # 右后
         
         return torques
     
     def _calculate_engine_rpm(self, speed_kmh: float, gear: int) -> float:
         """根据车速计算发动机转速"""
         if gear == 0:
             return 800.0  # 空档怠速
         
         gear_ratio = self.gear_ratios[gear]
         total_ratio = gear_ratio * self.final_ratio
         
         # wheel_rpm = speed / (2 * pi * radius) * 60
         wheel_rpm = (speed_kmh / 3.6) / (2 * math.pi * 0.35) * 60
         
         # engine_rpm = wheel_rpm * total_ratio
         engine_rpm = wheel_rpm * total_ratio
         
         return max(800.0, min(self.engine_config.max_rpm, engine_rpm))
     
     def _auto_shift(self, vehicle_state):
         """自动换档逻辑"""
         rpm = vehicle_state.engine_rpm
         max_rpm = self.engine_config.max_rpm
         current_gear = vehicle_state.current_gear
         
         # 升档
         if rpm > max_rpm * 0.85 and current_gear < len(self.gear_ratios) - 1:
             vehicle_state.current_gear += 1
         
         # 降档
         elif rpm < max_rpm * 0.35 and current_gear > 1:
             vehicle_state.current_gear -= 1
 ```
 
 ## 四、姿态系统实现
 
 ### 4.1 数据模型
 
 ```python
 # src/data/pose_state.py
 @dataclass
 class PoseConfig:
     """姿态配置"""
     # 限值
     max_roll: float              # 最大侧倾角 (度)
     max_pitch: float             # 最大俯仰角 (度)
     
     # 刚度
     roll_stiffness: float        # 侧倾刚度
     pitch_stiffness: float       # 俯仰刚度
     bounce_stiffness: float      # 晃动刚度
     
     # 阻尼
     roll_damping: float          # 侧倾阻尼
     pitch_damping: float         # 俯仰阻尼
     bounce_damping: float        # 晃动阻尼
     
     # 防倾杆
     front_anti_roll: float       # 前防倾杆刚度
     rear_anti_roll: float        # 后防倾杆刚度
 
 @dataclass
 class PoseState:
     """姿态状态"""
     # 角度
     roll: float                  # 侧倾角 (度)
     pitch: float                 # 俯仰角 (度)
     
     # 角速度
     roll_velocity: float         # 侧倾角速度
     pitch_velocity: float        # 俯仰角速度
     
     # 晃动
     bounce: float                # 上下晃动 (m)
     bounce_velocity: float       # 晃动速度
 ```
 
 ### 4.2 系统实现（改进版，包含防倾杆）
 
 ```python
 # src/systems/pose_system.py
 class PoseSystem(SystemBase):
     """
     姿态系统实现
     
     基于悬挂状态和车辆动力学计算车身姿态
     包含防倾杆效果
     """
     
     def __init__(self, config: dict):
         super().__init__(config)
         
         # 车辆参数
         self.vehicle_mass = config.get('vehicle_mass', 1500.0)
         self.track_width = config.get('track_width', 1.5)  # 轮距
         self.wheelbase = config.get('wheelbase', 2.6)      # 轴距
         self.cg_height = config.get('cg_height', 0.5)      # 重心高度
         
         # 姿态参数
         self.max_roll = config.get('max_roll', 5.0)
         self.max_pitch = config.get('max_pitch', 3.0)
         
         self.roll_stiffness = config.get('roll_stiffness', 10000.0)
         self.pitch_stiffness = config.get('pitch_stiffness', 10000.0)
         self.bounce_stiffness = config.get('bounce_stiffness', 15000.0)
         
         self.roll_damping = config.get('roll_damping', 500.0)
         self.pitch_damping = config.get('pitch_damping', 500.0)
         self.bounce_damping = config.get('bounce_damping', 800.0)
         
         # 防倾杆
         self.front_anti_roll = config.get('front_anti_roll', 1000.0)
         self.rear_anti_roll = config.get('rear_anti_roll', 1000.0)
     
     def update(self, dt, vehicle_state, suspension_state, pose_state):
         """更新姿态系统"""
         
         # 1. 计算侧倾
         target_roll = self._calculate_target_roll(vehicle_state, suspension_state)
         self._update_roll(dt, target_roll, pose_state)
         
         # 2. 计算俯仰
         target_pitch = self._calculate_target_pitch(vehicle_state, suspension_state)
         self._update_pitch(dt, target_pitch, pose_state)
         
         # 3. 计算晃动
         target_bounce = self._calculate_target_bounce(suspension_state)
         self._update_bounce(dt, target_bounce, pose_state)
     
     def _calculate_target_roll(self, vehicle_state, suspension_state):
         """
         计算目标侧倾角
         
         基于横向加速度和防倾杆效果
         """
         # 横向加速度 (简化计算)
         speed_ms = vehicle_state.speed / 3.6
         steering_rad = math.radians(vehicle_state.steering_angle)
         turn_radius = self.wheelbase / math.tan(steering_rad) if abs(steering_rad) > 0.01 else 1000.0
         lateral_accel = (speed_ms ** 2) / turn_radius
         
         # 基础侧倾（无防倾杆）
         base_roll = math.degrees(math.atan2(lateral_accel, 9.81))
         
         # 悬挂差异导致的侧倾
         if len(suspension_state.wheels) >= 4:
             left_avg = (suspension_state.wheels[0].compression + 
                       suspension_state.wheels[2].compression) / 2
             right_avg = (suspension_state.wheels[1].compression + 
                        suspension_state.wheels[3].compression) / 2
             roll_from_suspension = math.degrees(math.atan2(
                 (left_avg - right_avg) * 0.3,  # 悬挂长度
                 self.track_width
             ))
         else:
             roll_from_suspension = 0.0
         
         # 防倾杆减少侧倾
         anti_roll_effect = min(0.3, (self.front_anti_roll + self.rear_anti_roll) / 10000.0)
         
         target_roll = base_roll * (1 - anti_roll_effect) + roll_from_suspension
         return max(-self.max_roll, min(self.max_roll, target_roll))
     
     def _update_roll(self, dt, target_roll, pose_state):
         """更新侧倾角（带弹簧阻尼）"""
         # 计算误差
         error = target_roll - pose_state.roll
         
         # 弹簧力
         spring_torque = error * self.roll_stiffness
         
         # 阻尼力
         damper_torque = -pose_state.roll_velocity * self.roll_damping
         
         # 总扭矩
         total_torque = spring_torque + damper_torque
         
         # 转动惯量（简化）
         moi = self.vehicle_mass * (self.track_width ** 2) / 12
         
         # 角加速度
         angular_accel = total_torque / moi
         
         # 更新角速度
         pose_state.roll_velocity += angular_accel * dt
         
         # 更新角度
         pose_state.roll += pose_state.roll_velocity * dt
         
         # 阻尼衰减
         pose_state.roll_velocity *= 0.95
         
         # 限制范围
         pose_state.roll = max(-self.max_roll, min(self.max_roll, pose_state.roll))
     
     def _calculate_target_pitch(self, vehicle_state, suspension_state):
         """
         计算目标俯仰角
         
         基于纵向加速度和悬挂差异
         """
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
     
     def _update_pitch(self, dt, target_pitch, pose_state):
         """更新俯仰角（类似侧倾）"""
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
     
     def _calculate_target_bounce(self, suspension_state):
         """计算目标晃动"""
         if not suspension_state.wheels:
             return 0.0
         
         # 平均压缩
         avg_compression = sum(w.compression for w in suspension_state.wheels) / len(suspension_state.wheels)
         
         # 转换为米
         return avg_compression * 0.3  # 假设悬挂长度 0.3m
     
     def _update_bounce(self, dt, target_bounce, pose_state):
         """更新晃动"""
         error = target_bounce - pose_state.bounce
         spring_force = error * self.bounce_stiffness
         damper_force = -pose_state.bounce_velocity * self.bounce_damping
         total_force = spring_force + damper_force
         
         accel = total_force / self.vehicle_mass
         pose_state.bounce_velocity += accel * dt
         pose_state.bounce += pose_state.bounce_velocity * dt
         pose_state.bounce_velocity *= 0.95
 ```
 
 ## 五、系统集成
 
 ### 5.1 VehicleEntity 中的系统协调
 
 ```python
 # src/business/vehicle_entity.py
 class VehicleEntity:
     def __init__(self, vehicle_id: str, config: dict):
         # ... 初始化代码 ...
         
         # 注册所有系统
         self._register_systems(config)
     
     def _register_systems(self, config: dict):
         """注册所有子系统"""
         
         # 1. 物理系统
         self.register_system('physics', PhysicsSystem(config.get('physics', {})))
         
         # 2. 车轮系统
         self.register_system('wheels', WheelSystem(config.get('wheels', {})))
         
         # 3. 悬挂系统（依赖车轮系统）
         suspension_system = SuspensionSystem(config.get('suspension', {}))
         self.register_system('suspension', suspension_system)
         
         # 4. 轮胎系统（依赖悬挂系统）
         tire_system = TireSystem(config.get('tires', {}))
         self.register_system('tires', tire_system)
         
         # 5. 传动系统
         transmission_system = TransmissionSystem(config.get('transmission', {}))
         self.register_system('transmission', transmission_system)
         
         # 6. 姿态系统（依赖悬挂系统）
         pose_system = PoseSystem(config.get('pose', {}))
         self.register_system('pose', pose_system)
     
     def update(self, dt: float):
         """
         更新车辆
         
         系统更新顺序（按依赖关系）：
         """
         # 1. 物理系统 - 计算基础运动
         physics = self.get_system('physics')
         if physics:
             physics.update(dt, self.current_input, self.state)
         
         # 2. 车轮系统 - 更新车轮状态
         wheels = self.get_system('wheels')
         if wheels:
             wheels.update(dt, self.state, self.wheels_state)
         
         # 3. 传动系统 - 计算发动机扭矩
         transmission = self.get_system('transmission')
         if transmission:
             wheel_torques = transmission.update(dt, self.state, self.current_input)
             # 应用扭矩到车轮
             for i, torque in enumerate(wheel_torques):
                 if i < len(self.wheels_state.wheels):
                     self.wheels_state.wheels[i].drive_torque = torque
         
         # 4. 悬挂系统 - 计算悬挂状态
         suspension = self.get_system('suspension')
         if suspension:
             suspension.update(dt, self.state, self.wheels_state, self.suspension_state)
         
         # 5. 轮胎系统 - 计算轮胎力
         tires = self.get_system('tires')
         if tires:
             tires.update(dt, self.state, self.wheels_state, self.suspension_state, self.tire_states)
         
         # 6. 姿态系统 - 计算车身姿态
         pose = self.get_system('pose')
         if pose:
             pose.update(dt, self.state, self.suspension_state, self.pose_state)
         
         # 7. 应用轮胎力到车辆（简化）
         self._apply_tire_forces()
     
     def _apply_tire_forces(self):
         """将轮胎力应用到车辆运动"""
         # 简化的力应用
         total_long_force = sum(t.long_force for t in self.tire_states)
         total_lat_force = sum(t.lat_force for t in self.tire_states)
         
         # 更新加速度（简化）
         mass = 1500.0
         self.state.acceleration.x = total_long_force / mass
         self.state.acceleration.y = total_lat_force / mass
 ```
 
 ## 六、配置示例（完整版）
 
 ```yaml
 # config/vehicle_complete.yaml
 vehicle:
   name: "Sports Car"
   position: [0, 0, 0.6]
   heading: 0
   
   # 物理配置
   physics:
     max_speed: 200.0
     mass: 1500.0
     drag_coefficient: 0.3
     acceleration: 80.0
     deceleration: 40.0
     brake_deceleration: 120.0
     turn_speed: 200.0
     max_steering_angle: 40.0
     
     input_smoothing:
       throttle_rise: 8.0
       throttle_fall: 12.0
       brake_rise: 8.0
       brake_fall: 12.0
       steering_rise: 3.0
       steering_fall: 6.0
   
   # 悬挂配置
   suspension:
     vehicle_mass: 1500.0
     com_position: [0, 0, 0.3]
     
     wheels:
       - position: [-0.8, 1.4, -0.3]
         natural_frequency: 8.0
         damping_ratio: 0.9
         max_compression: 0.08
         max_droop: 0.08
         force_offset: 0.0
       
       - position: [0.8, 1.4, -0.3]
         natural_frequency: 8.0
         damping_ratio: 0.9
         max_compression: 0.08
         max_droop: 0.08
         force_offset: 0.0
       
       - position: [-0.8, -1.4, -0.3]
         natural_frequency: 7.0
         damping_ratio: 1.0
         max_compression: 0.1
         max_droop: 0.1
         force_offset: 0.0
       
       - position: [0.8, -1.4, -0.3]
         natural_frequency: 7.0
         damping_ratio: 1.0
         max_compression: 0.1
         max_droop: 0.1
         force_offset: 0.0
   
   # 轮胎配置
   tires:
     - lat_stiff_max_load: 2.0
       lat_stiff_value: 17.0
       long_stiff_value: 1000.0
       friction: 1.0
     
     - lat_stiff_max_load: 2.0
       lat_stiff_value: 17.0
       long_stiff_value: 1000.0
       friction: 1.0
     
     - lat_stiff_max_load: 2.0
       lat_stiff_value: 17.0
       long_stiff_value: 1200.0
       friction: 1.1
     
     - lat_stiff_max_load: 2.0
       lat_stiff_value: 17.0
       long_stiff_value: 1200.0
       friction: 1.1
   
   # 传动配置
   transmission:
     engine:
       moi: 1.0
       max_rpm: 7000.0
       torque_curve:
         - [0, 300]
         - [1000, 350]
         - [3000, 450]
         - [5000, 420]
         - [6500, 380]
         - [7000, 0]
       damping_full_throttle: 0.15
       damping_zero_throttle_clutch_engaged: 2.0
       damping_zero_throttle_clutch_disengaged: 0.35
     
     gear_ratios: [0, 3.5, 2.5, 1.8, 1.4, 1.0, 0.8]
     final_ratio: 3.5
     reverse_ratio: -3.5
     auto_shift: true
     
     differential:
       type: 'limited_slip'
       front_rear_split: 0.5
       front_bias: 1.5
       rear_bias: 2.0
   
   # 姿态配置
   pose:
     vehicle_mass: 1500.0
     track_width: 1.6
     wheelbase: 2.8
     cg_height: 0.5
     
     max_roll: 6.0
     max_pitch: 4.0
     
     roll_stiffness: 12000.0
     pitch_stiffness: 12000.0
     bounce_stiffness: 18000.0
     
     roll_damping: 600.0
     pitch_damping: 600.0
     bounce_damping: 900.0
     
     front_anti_roll: 1500.0
     rear_anti_roll: 1200.0
   
   # 车轮配置
   wheels:
     - position: [-0.8, 1.4, -0.3]
       radius: 0.35
       can_steer: true
       is_driven: true
     
     - position: [0.8, 1.4, -0.3]
       radius: 0.35
       can_steer: true
       is_driven: true
     
     - position: [-0.8, -1.4, -0.3]
       radius: 0.35
       can_steer: false
       is_driven: true
     
     - position: [0.8, -1.4, -0.3]
       radius: 0.35
       can_steer: false
       is_driven: true
 ```
 
 ## 七、实现优先级
 
 ### 高优先级（必须实现）
 1. ✅ 物理系统（PhysicsSystem）
 2. ✅ 悬挂系统（SuspensionSystem）
 3. ✅ 姿态系统（PoseSystem）
 4. ✅ 车轮系统（WheelSystem）
 
 ### 中优先级（推荐实现）
 5. ⏳ 轮胎系统（TireSystem）
 6. ⏳ 传动系统（TransmissionSystem）
 
 ### 低优先级（可选实现）
 7. ⏳ 动画系统（AnimationSystem）
 8. ⏳ 输入系统（InputSystem）
 9. ⏳ 渲染系统（RenderSystem）
 
 ## 八、关键算法总结
 
 | 系统 | 核心算法 | 输入 | 输出 |
 |------|----------|------|------|
 | 物理 | 运动学积分 | 控制输入、轮胎力 | 位置、速度、航向 |
 | 悬挂 | 弹簧-阻尼 | 车辆状态、车轮速度 | 压缩量、悬挂力 |
 | 轮胎 | Pacejka 公式 | 打滑、负载、摩擦 | 纵向力、侧向力 |
 | 传动 | 扭矩传递 | 油门、档位 | 轮上扭矩、发动机转速 |
 | 姿态 | 角动力学 | 加速度、悬挂差异 | 侧倾、俯仰、晃动 |
 
 ## 九、下一步工作
 
 1. **修复现有代码**：解决文件缩进问题，确保可运行
 2. **实现轮胎系统**：使用简化的 Pacejka 模型
 3. **实现传动系统**：发动机、变速箱、差速器
 4. **集成测试**：测试系统间协作
 5. **性能优化**：缓存、简化计算
 6. **渲染集成**：将状态应用到 Panda3D 场景
