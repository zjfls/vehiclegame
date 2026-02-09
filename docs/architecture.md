 # Panda3D 赛车游戏架构设计文档
 
 ## 架构分层
 
 ```
 ┌─────────────────────────────────────────┐
 │           应用层             │
 │  - RacingGame (ShowBase)               │
 │  - 游戏流程控制                         │
 └─────────────────────────────────────────┘
                   ↓
 ┌─────────────────────────────────────────┐
 │           业务层          │
 │  - VehicleEntity (车辆实体)             │
 │  - GameWorld (游戏世界)                 │
 │  - PlayerController (玩家控制器)         │
 └─────────────────────────────────────────┘
                   ↓
 ┌─────────────────────────────────────────┐
 │           系统层            │
 │  - PhysicsSystem (物理系统)            │
 │  - RenderSystem (渲染系统)             │
 │  - InputSystem (输入系统)              │
 │  - SuspensionSystem (悬挂系统)          │
 │  - PoseSystem (姿态系统)               │
 │  - AnimationSystem (动画系统)           │
 │  - WheelSystem (车轮系统)               │
 │  - TireSystem (轮胎系统)                │
 │  - TransmissionSystem (变速箱系统)       │
 └─────────────────────────────────────────┘
                   ↓
 ┌─────────────────────────────────────────┐
 │           数据层              │
 │  - VehicleState (车辆状态)             │
 │  - WheelState (车轮状态)                │
 │  - SuspensionState (悬挂状态)            │
 │  - PoseState (姿态状态)                 │
 └─────────────────────────────────────────┘
 ```
 
 ## 业务层设计
 
 ### VehicleEntity (车辆实体)
 
 **职责**：
 - 车辆的业务逻辑抽象
 - 协调各个子系统
 - 不涉及具体实现细节
 
 **核心接口**：
 ```python
 class VehicleEntity:
     def update(self, dt: float) -> None
     def get_state(self) -> VehicleState
     def get_wheel_state(self, index: int) -> WheelState
     def get_suspension_state(self, index: int) -> SuspensionState
     def get_pose_state(self) -> PoseState
 ```
 
 ### GameWorld (游戏世界)
 
 **职责**：
 - 管理所有车辆实体
 - 管理场景环境
 - 处理车辆间交互
 
 **核心接口**：
 ```python
 class GameWorld:
     def add_vehicle(self, vehicle: VehicleEntity) -> None
     def remove_vehicle(self, vehicle: VehicleEntity) -> None
     def get_vehicle(self, id: str) -> VehicleEntity
     def update(self, dt: float) -> None
 ```
 
 ### PlayerController (玩家控制器)
 
 **职责**：
 - 处理玩家输入
 - 将输入转换为车辆控制指令
 - 处理游戏模式（单人/多人）
 
 **核心接口**：
 ```python
 class PlayerController:
     def update(self, dt: float) -> None
     def set_controlled_vehicle(self, vehicle: VehicleEntity) -> None
     def get_control_input(self) -> VehicleControlInput
 ```
 
 ## 系统层设计
 
 ### PhysicsSystem (物理系统)
 
 **职责**：
 - 计算车辆的运动学/动力学
 - 计算速度、加速度、位置变化
 - 处理碰撞检测
 
 **输入**：
 - VehicleControlInput（控制输入）
 - VehicleState（当前状态）
 - WheelState（车轮状态）
 - TireConfig（轮胎配置）
 
 **输出**：
 - VehicleState（新状态）
 - WheelState（新车轮状态）
 
 ### SuspensionSystem (悬挂系统)
 
 **职责**：
 - 计算每个车轮的悬挂压缩量
 - 计算悬挂力（弹力 + 阻尼）
 - 处理悬挂的上下运动
 
 **输入**：
 - VehicleState（车辆状态）
 - WheelState（车轮状态）
 - SuspensionConfig（悬挂配置）
 
 **输出**：
 - SuspensionState（悬挂状态：压缩量、悬挂力等）
 - WheelPosition（车轮相对于车身的偏移）
 
 ### PoseSystem (姿态系统)
 
 **职责**：
 - 计算车身的姿态（侧倾、俯仰）
 - 基于加速度和转向计算姿态变化
 - 处理车身晃动
 
 **输入**：
 - VehicleState（车辆状态）
 - SuspensionState（悬挂状态）
 - PoseConfig（姿态配置）
 
 **输出**：
 - PoseState（姿态状态：侧倾角、俯仰角、晃动等）
 - BodyTransform（车身的变换矩阵）
 
 ### AnimationSystem (动画系统)
 
 **职责**：
 - 驱动车身动画（晃动、颠簸）
 - 驱动悬挂动画（压缩/回弹）
 - 驱动车轮动画（旋转、转向）
 - 处理特效动画（尾气、火花）
 
 **输入**：
 - PoseState（姿态状态）
 - SuspensionState（悬挂状态）
 - WheelState（车轮状态）
 
 **输出**：
 - AnimationState（动画状态：各部件的变换）
 
 ### WheelSystem (车轮系统)
 
 **职责**：
 - 管理所有车轮的状态
 - 计算车轮的旋转角
 - 计算车轮的转向角
 
 **输入**：
 - VehicleState（车辆状态）
 - VehicleControlInput（控制输入）
 
 **输出**：
 - WheelState（车轮状态）
 
 ### TireSystem (轮胎系统)
 
 **职责**：
 - 计算轮胎力（纵向力、侧向力）
 - 计算轮胎打滑
 - 处理轮胎与地面的交互
 
 **输入**：
 - WheelState（车轮状态）
 - TireConfig（轮胎配置）
 - SurfaceType（地面类型）
 
 **输出**：
 - TireForce（轮胎力）
 
 ### TransmissionSystem (变速箱系统)
 
 **职责**：
 - 计算发动机转速
 - 处理自动/手动换档
 - 计算扭矩分配
 
 **输入**：
 - VehicleState（车辆状态）
 - VehicleControlInput（控制输入）
 - TransmissionConfig（变速箱配置）
 
 **输出**：
 - EngineRPM（发动机转速）
 - CurrentGear（当前档位）
 - WheelTorque（轮上扭矩）
 
 ## 数据层设计
 
 ### VehicleState (车辆状态)
 
 ```python
 @dataclass
 class VehicleState:
     # 位置和旋转
     position: Vector3        # 世界坐标位置 (x, y, z)
     heading: float           # 航向角 (度)
     
     # 运动状态
     velocity: Vector3        # 速度向量
     speed: float             # 速度 (km/h)
     acceleration: Vector3    # 加速度向量
     
     # 转向状态
     steering_angle: float     # 转向角 (度)
     
     # 发动机状态
     engine_rpm: float        # 发动机转速
     throttle: float         # 油门 (0.0 ~ 1.0)
     brake: float            # 刹车 (0.0 ~ 1.0)
 ```
 
 ### SuspensionState (悬挂状态)
 
 ```python
 @dataclass
 class SuspensionState:
     # 每个轮子的悬挂状态
     wheels: List[WheelSuspensionState]
 
 @dataclass
 class WheelSuspensionState:
     # 悬挂压缩
     compression: float     # 压缩量 (-1.0 ~ 1.0, 0=静止位置)
     compression_velocity: float  # 压缩速度
     
     # 悬挂力
     spring_force: float      # 弹簧力
     damper_force: float     # 阻尼力
     total_force: float      # 总力
     
     # 车轮位置
     wheel_offset: Vector3   # 车轮相对于车身的偏移
     
     # 接触状态
     is_in_air: bool         # 是否悬空
     contact_point: Vector3  # 接触点
     contact_normal: Vector3 # 接触法线
 ```
 
 ### PoseState (姿态状态)
 
 ```python
 @dataclass
 class PoseState:
     # 姿态角
     roll: float             # 侧倾角 (度)
     pitch: float           # 俯仰角 (度)
     
     # 姿态速度
     roll_velocity: float    # 侧倾角速度
     pitch_velocity: float  # 俯仰角速度
     
     # 晃动
     bounce: float          # 上下晃动
     bounce_velocity: float # 晃动速度
     
     # 车身变换
     body_transform: Matrix4x4  # 车身的变换矩阵
 ```
 
 ### WheelState (车轮状态)
 
 ```python
 @dataclass
 class WheelState:
     # 车轮位置
     position: Vector3       # 车轮世界坐标
     local_position: Vector3 # 车轮相对车身坐标
     
     # 车轮旋转
     rotation_angle: float   # 车轮旋转角 (度)
     rotation_speed: float   # 车轮旋转速度 (度/秒)
     
     # 车轮转向
     steering_angle: float  # 转向角 (度)
     
     # 车轮速度
     linear_velocity: Vector3  # 线速度
     angular_velocity: float    # 角速度
     
     # 轮胎状态
     long_slip: float       # 纵向打滑
     lat_slip: float        # 侧向打滑
     tire_load: float       # 轮胎负载
 ```
 
 ## 系统交互流程
 
 ```
 PlayerControlInput
        ↓
 InputSystem (处理输入)
        ↓
 VehicleEntity.update()
        ↓
        ├─→ PhysicsSystem (计算运动)
        │        ↓
        │   VehicleState (新状态)
        │
        ├─→ SuspensionSystem (计算悬挂)
        │        ↓
        │   SuspensionState (悬挂状态)
        │
        ├─→ WheelSystem (计算车轮)
        │        ↓
        │   WheelState (车轮状态)
        │
        ├─→ TireSystem (计算轮胎力)
        │        ↓
        │   TireForce (轮胎力)
        │
        ├─→ TransmissionSystem (计算变速箱)
        │        ↓
        │   EngineRPM, CurrentGear
        │
        ├─→ PoseSystem (计算姿态)
        │        ↓
        │   PoseState (姿态状态)
        │
        └─→ AnimationSystem (驱动动画)
                 ↓
             AnimationState (动画状态)
 ```
 
 ## 配置系统
 
 ### VehicleConfig (车辆配置)
 
 ```yaml
 vehicle:
   name: "Sports Car"
   
   # 物理配置
   physics:
     mass: 1500.0
     drag_coefficient: 0.3
     max_speed: 200.0
   
   # 悬挂配置
   suspension:
     front:
       stiffness: 50000.0
       damping: 2500.0
       rest_length: 0.3
       max_compression: 0.1
       max_extension: 0.1
     rear:
       stiffness: 50000.0
       damping: 2500.0
       rest_length: 0.3
       max_compression: 0.1
       max_extension: 0.1
   
   # 姿态配置
   pose:
     max_roll: 5.0
     max_pitch: 3.0
     roll_stiffness: 10000.0
     pitch_stiffness: 10000.0
     roll_damping: 500.0
     pitch_damping: 500.0
     bounce_stiffness: 15000.0
     bounce_damping: 800.0
   
   # 车轮配置
   wheels:
     - position: [-0.9, 1.3, -0.35]
       radius: 0.35
       can_steer: true
       is_driven: true
     - position: [0.9, 1.3, -0.35]
       radius: 0.35
       can_steer: true
       is_driven: true
     - position: [-0.9, -1.3, -0.35]
       radius: 0.35
       can_steer: false
       is_driven: true
     - position: [0.9, -1.3, -0.35]
       radius: 0.35
       can_steer: false
       is_driven: true
 ```
 
 ## 扩展性设计
 
 ### 系统接口标准化
 
 所有系统都实现统一的接口：
 
 ```python
 class ISystem:
     def initialize(self) -> None:
         """初始化系统"""
         pass
     
     def update(self, dt: float) -> None:
         """每帧更新"""
         pass
     
     def shutdown(self) -> None:
         """关闭系统"""
         pass
 ```
 
 ### 系统依赖管理
 
 通过依赖注入管理系统间的依赖：
 
 ```python
 class VehicleEntity:
     def __init__(self):
         # 创建系统
         self.physics_system = PhysicsSystem()
         self.suspension_system = SuspensionSystem()
         self.pose_system = PoseSystem()
         self.animation_system = AnimationSystem()
         
         # 设置依赖
         self.pose_system.set_suspension_system(self.suspension_system)
         self.animation_system.set_pose_system(self.pose_system)
         self.animation_system.set_suspension_system(self.suspension_system)
 ```
 
 ## 测试策略
 
 ### 单元测试
 
 每个系统独立测试，使用 Mock 数据：
 
 ```python
 def test_suspension_system():
     config = SuspensionConfig(...)
     system = SuspensionSystem(config)
     
     state = SuspensionState(...)
     vehicle_state = VehicleState(...)
     
     new_state = system.update(vehicle_state, state, dt=0.016)
     
     assert new_state.compression == expected_value
 ```
 
 ### 集成测试
 
 测试系统间的交互：
 
 ```python
 def test_vehicle_entity():
     vehicle = VehicleEntity(config)
     
     # 模拟输入
     vehicle.set_throttle(1.0)
     
     # 更新
     vehicle.update(dt=0.016)
     
     # 验证状态
     assert vehicle.get_state().speed > 0
     assert vehicle.get_suspension_state(0).compression > 0
 ```
