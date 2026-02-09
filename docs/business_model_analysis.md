 # PhysXVehicles 业务模型深度分析
 
 ## 1. 悬挂系统 (Suspension System)
 
 ### 1.1 核心概念
 
 悬挂系统是车辆与地面之间的连接，主要功能：
 - 支撑车身重量
 - 吸收路面冲击
 - 保持轮胎与地面的接触
 - 影响车身姿态（侧倾、俯仰）
 
 ### 1.2 物理模型
 
 #### 弹簧-阻尼模型
 
 ```
 悬挂力 = 弹簧力 + 阻尼力
 
 弹簧力 = -弹簧刚度 × 压缩量
 阻尼力 = -阻尼系数 × 压缩速度
 ```
 
 #### 关键参数
 
 | 参数 | 符号 | 单位 | 说明 |
 |------|------|------|------|
 | 弹簧刚度 | k | N/m | 悬挂的硬度 |
 | 阻尼系数 | c | N·s/m | 悬挂的减震能力 |
 | 自然频率 | ωn | rad/s | 悬挂的固有振动频率 |
 | 阻尼比 | ζ | 无量纲 | 阻尼程度（<1欠阻尼，=1临界阻尼，>1过阻尼）|
 | 悬挂质量 | ms | kg | 每个车轮支撑的车身质量 |
 | 最大压缩 | max_compression | m | 悬挂最大压缩量 |
 | 最大伸长 | max_droop | m | 悬挂最大伸长量 |
 
 ### 1.3 计算公式
 
 #### 弹簧刚度计算
 
 ```python
 # 从自然频率计算弹簧刚度
 k = (ωn)^2 × ms
 
 # 从刚度计算自然频率
 ωn = sqrt(k / ms)
 
 # 转换为 Hz
 fn = ωn / (2π)
 ```
 
 #### 阻尼系数计算
 
 ```python
 # 临界阻尼系数
 cc = 2 × sqrt(k × ms)
 
 # 实际阻尼系数
 c = ζ × cc = ζ × 2 × sqrt(k × ms)
 ```
 
 #### 悬挂力计算
 
 ```python
 # 弹簧力（胡克定律）
 F_spring = -k × x
 
 # 阻尼力
 F_damper = -c × v
 
 # 总悬挂力
 F_total = F_spring + F_damper
 ```
 
 其中：
 - x: 悬挂压缩量（正=压缩，负=伸长）
 - v: 悬挂压缩速度
 
 ### 1.4 悬挂质量计算
 
 PhysX 使用 `PxVehicleComputeSprungMasses` 计算每个车轮的悬挂质量：
 
 ```python
 # 输入
 - 车轮数量
 - 车轮相对于质心的位置
 - 车辆总质量
 - 重力方向
 
 # 输出
 - 每个车轮的悬挂质量
 
 # 约束条件
 - 所有悬挂质量之和 = 车辆总质量
 - 质心位置平衡
 ```
 
 ### 1.5 悬挂压缩计算
 
 悬挂压缩量由以下因素决定：
 
 1. **静态压缩**（重力引起）
    ```
    x_static = (ms × g) / k
    ```
 
 2. **动态压缩**（加速度引起）
    ```
    x_dynamic = (ms × a) / k
    ```
 
 3. **路面不平度**（射线检测）
    - 发射射线检测地面高度
    - 计算车轮应处位置与实际位置的差
 
 4. **阻尼效应**
    - 根据压缩速度产生阻尼力
    - 减少振荡
 
 ### 1.6 车身姿态影响
 
 #### 侧倾（Roll）
 
 侧倾由左右悬挂压缩差异引起：
 
 ```python
 # 左右悬挂压缩差
 delta_x = x_left - x_right
 
 # 侧倾角（近似）
 roll_angle ≈ arctan(delta_x / track_width)
 
 # 其中 track_width 是轮距（左右轮距离）
 ```
 
 #### 俯仰（Pitch）
 
 俯仰由前后悬挂压缩差异引起：
 
 ```python
 # 前后悬挂压缩差
 delta_x = x_front - x_rear
 
 # 俯仰角（近似）
 pitch_angle ≈ arctan(delta_x / wheelbase)
 
 # 其中 wheelbase 是轴距（前后轮距离）
 ```
 
 ### 1.7 防倾杆（Anti-Roll Bar）
 
 防倾杆连接左右悬挂，减少侧倾：
 
 ```python
 # 防倾杆力
 F_antiroll = k_antiroll × (x_left - x_right)
 
 # 附加到左侧的力
 F_left += F_antiroll
 
 # 附加到右侧的力
 F_right -= F_antiroll
 ```
 
 ## 2. 轮胎模型 (Tire Model)
 
 ### 2.1 核心概念
 
 轮胎是车辆与地面交互的唯一部件，主要功能：
 - 产生纵向力（加速、刹车）
 - 产生侧向力（转向）
 - 产生回正力矩
 
 ### 2.2 轮胎力计算流程
 
 ```
 输入参数 → 计算刚度 → 计算打滑 → 计算轮胎力
 ```
 
 ### 2.3 关键参数
 
 | 参数 | 符号 | 单位 | 说明 |
 |------|------|------|------|
 | 纵向刚度 | Cx | N | 轮胎纵向刚度 |
 | 侧向刚度 | Cy | N | 轮胎侧向刚度 |
 | 外倾刚度 | Cγ | N/rad | 轮胎外倾刚度 |
 | 摩擦系数 | μ | 无量纲 | 轮胎与地面的摩擦系数 |
 | 轮胎负载 | Fz | N | 垂直作用在轮胎上的力 |
 | 静止负载 | Fz0 | N | 车辆静止时的轮胎负载 |
 
 ### 2.4 刚度计算
 
 #### 纵向刚度
 
 ```python
 # 基于重力单位的纵向刚度
 Cx = long_stiffness_per_unit_gravity × g
 
 # 或从轮胎数据直接获取
 Cx = tire_data.mLongitudinalStiffnessPerUnitGravity × 9.81
 ```
 
 #### 侧向刚度
 
 ```python
 # 基于负载的侧向刚度（Pacejka 公式简化）
 Cy = Fz0 × lat_stiff_y × smoothing_function(Fz / Fz0 × 3.0 / lat_stiff_x)
 
 # 平滑函数
 def smoothing_function1(K):
     return K - K^2 + (1/3)×K^3 - (1/27)×K^4
 ```
 
 ### 2.5 打滑计算
 
 #### 纵向打滑（Longitudinal Slip）
 
 纵向打滑表示轮胎旋转速度与车辆前进速度的差异：
 
 ```python
 # 定义
 κ = (ω×r - Vx) / |Vx|  （当 |Vx| > 阈值时）
 
 # 其中
 # ω: 车轮角速度
 # r: 车轮半径
 # Vx: 车辆纵向速度
 # 
 # κ > 0: 驱动（轮胎转得比车快）
 # κ < 0: 刹车（轮胎转得比车慢）
 ```
 
 #### 侧向打滑（Lateral Slip）
 
 侧向打滑表示轮胎侧偏角：
 
 ```python
 # 侧偏角
 α = arctan(Vy / |Vx|)
 
 # 其中
 # Vy: 车辆侧向速度
 # Vx: 车辆纵向速度
 ```
 
 #### 外倾角（Camber）
 
 轮胎相对于垂直方向的倾斜角。
 
 ### 2.6 轮胎力计算（Pacejka 简化模型）
 
 PhysX 使用简化的 Pacejka "魔术公式"：
 
 ```python
 # 1. 计算有效侧偏
 T_eff = tan(α - γ × Cγ / Cy)
 
 # 2. 计算综合打滑参数 K
 K = sqrt(Cy^2 × T_eff^2 + Cx^2 × κ^2) / (μ × Fz)
 
 # 3. 计算归一化力
 F_bar = smoothing_function1(K)
 M_bar = smoothing_function2(K)
 
 # 4. 计算修正因子 ν
 if K <= 2π:
     ν = 0.5 × (1 + Cy/Cx - (1 - Cy/Cx) × cos(K/2))
 else:
     ν = 1.0
 
 # 5. 计算零滑移力
 F0 = μ × Fz / sqrt(κ^2 + ν^2 × T_eff^2)
 
 # 6. 计算最终轮胎力
 # 纵向力（加速/刹车）
 F_long = κ × F_bar × F0
 
 # 侧向力（转向）
 F_lat = -ν × T_eff × F_bar × F0
 
 # 回正力矩
 M_align = ν × pneumatic_trail × T_eff × M_bar × F0
 
 # 7. 计算车轮扭矩
 wheel_torque = -F_long × r
 ```
 
 ### 2.7 轮胎负载计算
 
 ```python
 # 静态负载（重力分配）
 Fz0 = (vehicle_mass × g) / num_wheels
 
 # 动态负载（加速度影响）
 Fz = Fz0 + (mass_transfer × a) / (track_width / 2)
 
 # 负载转移
 # 加速：后轮负载增加，前轮减少
 # 刹车：前轮负载增加，后轮减少
 # 转向：外侧轮负载增加，内侧减少
 ```
 
 ### 2.8 摩擦系数
 
 摩擦系数由轮胎类型和地面材质决定：
 
 ```python
 # 基础摩擦系数
 μ_base = tire_friction × surface_friction
 
 # 考虑负载的摩擦系数修正
 μ_effective = μ_base × friction_multiplier(Fz / Fz0)
 ```
 
 ## 3. 传动系统 (Transmission System)
 
 ### 3.1 系统组成
 
 ```
 发动机 → 离合器 → 变速箱 → 差速器 → 驱动轮
 ```
 
 ### 3.2 发动机模型
 
 #### 扭矩曲线
 
 发动机输出扭矩随转速变化：
 
 ```python
 # 扭矩曲线（RPM vs Torque）
 torque = interpolate(torque_curve, engine_rpm)
 
 # 常见曲线形状
 # 低转速：扭矩较低
 # 中转速：扭矩峰值
 # 高转速：扭矩下降
 ```
 
 #### 发动机动力学
 
 ```python
 # 发动机角加速度
 α_engine = (T_engine - T_load) / I_engine
 
 # 其中
 # T_engine: 发动机输出扭矩
 # T_load: 负载扭矩（离合器、附件等）
 # I_engine: 发动机转动惯量
 ```
 
 ### 3.3 离合器模型
 
 离合器连接发动机和变速箱：
 
 ```python
 # 离合器传递扭矩
 T_clutch = clutch_strength × (ω_engine - ω_gearbox)
 
 # 离合器状态
 # 完全接合：ω_engine = ω_gearbox
 # 滑动：ω_engine ≠ ω_gearbox
 # 分离：T_clutch = 0
 ```
 
 ### 3.4 变速箱模型
 
 #### 档位比
 
 ```python
 # 总传动比
 ratio_total = gear_ratio[gear] × final_drive_ratio
 
 # 轮上扭矩
 T_wheel = T_engine × ratio_total × efficiency
 
 # 轮上转速
 ω_wheel = ω_engine / ratio_total
 ```
 
 #### 自动换档逻辑
 
 ```python
 # 升档条件
 if engine_rpm > up_shift_rpm and throttle > 0.5:
     gear += 1
 
 # 降档条件
 if engine_rpm < down_shift_rpm and throttle < 0.3:
     gear -= 1
 
 # 延迟保护
 if time_since_last_shift > gear_switch_time:
     allow_shift()
 ```
 
 ### 3.5 差速器模型
 
 #### 开放式差速器
 
 ```python
 # 左右轮扭矩相等
 T_left = T_right = T_input / 2
 
 # 允许左右轮转速不同
 ω_left ≠ ω_right
 ```
 
 #### 限滑差速器（LSD）
 
 ```python
 # 差速器锁止力矩
 T_diff = bias × (ω_left - ω_right)
 
 # 左右轮扭矩
 T_left = T_input / 2 + T_diff
 T_right = T_input / 2 - T_diff
 
 # 限制差速
 if |ω_left - ω_right| > max_diff_speed:
     apply_clutch()
 ```
 
 #### 扭矩分配（4WD）
 
 ```python
 # 前后扭矩分配
 T_front = T_total × front_rear_split
 T_rear = T_total × (1 - front_rear_split)
 
 # 左右扭矩分配（限滑）
 T_front_left = T_front × front_left_right_split
 T_front_right = T_front × (1 - front_left_right_split)
 ```
 
 ### 3.6 Ackermann 转向几何
 
 优化转向时内外轮转向角差异：
 
 ```python
 # 理想 Ackermann 转向
 cot(δ_outer) - cot(δ_inner) = track_width / wheelbase
 
 # 其中
 # δ_outer: 外侧轮转向角
 # δ_inner: 内侧轮转向角
 # track_width: 轮距
 # wheelbase: 轴距
 
 # 实际实现（近似）
 δ_inner = steering_angle × (1 + accuracy)
 δ_outer = steering_angle × (1 - accuracy)
 ```
 
 ## 4. 车身姿态系统 (Vehicle Pose System)
 
 ### 4.1 姿态定义
 
 车身姿态由三个旋转角定义：
 
 - **侧倾（Roll）**：绕 X 轴旋转（左右倾斜）
 - **俯仰（Pitch）**：绕 Y 轴旋转（前后倾斜）
 - **偏航（Yaw）**：绕 Z 轴旋转（水平转向）
 
 ### 4.2 姿态来源
 
 #### 悬挂压缩差异
 
 车身姿态主要由悬挂压缩差异决定：
 
 ```python
 # 侧倾角（基于左右悬挂压缩差）
 roll = arctan((x_left_avg - x_right_avg) / track_width)
 
 # 俯仰角（基于前后悬挂压缩差）
 pitch = arctan((x_front_avg - x_rear_avg) / wheelbase)
 ```
 
 #### 动态姿态（基于加速度）
 
 ```python
 # 横向加速度引起的侧倾
 roll_dynamic = arctan(a_y / g)
 
 # 纵向加速度引起的俯仰
 pitch_dynamic = arctan(a_x / g)
 ```
 
 ### 4.3 姿态动力学
 
 车身姿态不是瞬间变化的，而是有惯性和阻尼：
 
 ```python
 # 姿态运动方程（二阶系统）
 I_roll × α_roll = -k_roll × roll - c_roll × ω_roll + M_external
 
 # 其中
 # I_roll: 侧倾转动惯量
 # k_roll: 侧倾刚度（主要由悬挂几何决定）
 # c_roll: 侧倾阻尼
 # M_external: 外部力矩（离心力等）
 ```
 
 ### 4.4 姿态平滑
 
 姿态变化需要平滑处理，避免突变：
 
 ```python
 # 目标姿态（基于悬挂压缩）
 roll_target = calculate_from_suspension()
 
 # 实际姿态（带阻尼）
 roll_error = roll_target - roll_current
 roll_accel = (roll_error × stiffness - roll_velocity × damping) / inertia
 roll_velocity += roll_accel × dt
 roll_current += roll_velocity × dt
 ```
 
 ### 4.5 车身晃动（Bounce）
 
 车身上下运动：
 
 ```python
 # 平均悬挂压缩
 avg_compression = sum(x_i for all wheels) / num_wheels
 
 # 车身高度偏移
 bounce = avg_compression × rest_length
 
 # 带弹簧阻尼的晃动
 bounce_accel = (bounce_target - bounce) × stiffness - bounce_velocity × damping
 bounce_velocity += bounce_accel × dt
 bounce += bounce_velocity × dt
 ```
 
 ## 5. 车辆动力学综合
 
 ### 5.1 力和力矩平衡
 
 ```python
 # 平动方程
 m × a = ΣF
 
 # 转动方程
 I × α = ΣM
 
 # 其中力包括
 ΣF = F_tire_long + F_tire_lat + F_drag + F_gravity
 
 # 力矩包括
 ΣM = M_tire + M_suspension + M_inertial
 ```
 
 ### 5.2 质量转移
 
 加速度导致轮胎负载转移：
 
 ```python
 # 纵向质量转移（加速/刹车）
 ΔFz_long = (m × a_x × h_cg) / wheelbase
 
 # 横向质量转移（转向）
 ΔFz_lat = (m × a_y × h_cg) / track_width
 
 # 其中
 # h_cg: 质心高度
 # a_x: 纵向加速度
 # a_y: 横向加速度
 ```
 
 ### 5.3 更新顺序
 
 ```
 1. 获取控制输入（油门、刹车、转向）
 2. 计算发动机扭矩
 3. 通过变速箱计算轮上扭矩
 4. 计算轮胎力（基于打滑和负载）
 5. 计算悬挂力（基于压缩和速度）
 6. 计算车身姿态（基于悬挂差异）
 7. 应用力和力矩到车身
 8. 更新车辆位置和旋转
 9. 更新车轮位置和旋转
 ```
 
 ## 6. 简化模型 vs 完整模型
 
 ### 6.1 简化模型（适合轻量级游戏）
 
 ```python
 # 悬挂：简化弹簧模型
 F_suspension = -k × x - c × v
 
 # 轮胎：线性模型
 F_long = Cx × κ
 F_lat = Cy × α
 
 # 姿态：直接计算
 roll = arctan(a_y / g) × max_roll
 pitch = arctan(a_x / g) × max_pitch
 
 # 传动：简单比例
 T_wheel = T_engine × gear_ratio
 ```
 
 ### 6.2 完整模型（适合模拟器）
 
 ```python
 # 悬挂：详细弹簧-阻尼模型
 # - 考虑悬挂几何
 # - 防倾杆
 # - 悬挂质量分布
 
 # 轮胎：Pacejka 模型
 # - 完整的打滑计算
 # - 摩擦系数修正
 # - 回正力矩
 
 # 姿态：动力学模型
 # - 转动惯量
 # - 阻尼和刚度
 # - 多体动力学
 
 # 传动：详细模型
 # - 发动机扭矩曲线
 # - 离合器模型
 # - 差速器模型
 ```
 
 ## 7. 关键配置参数总结
 
 ### 悬挂参数
 
 ```yaml
 suspension:
   sprung_mass: 375.0          # 每个轮的悬挂质量 (kg)
   spring_strength: 18375.0    # 弹簧刚度 (N/m)
   damper_rate: 2625.0         # 阻尼系数 (N·s/m)
   max_compression: 0.1        # 最大压缩 (m)
   max_droop: 0.1              # 最大伸长 (m)
   natural_frequency: 7.0      # 自然频率 (Hz)
   damping_ratio: 1.0          # 阻尼比
 ```
 
 ### 轮胎参数
 
 ```yaml
 tire:
   radius: 0.35                # 轮胎半径 (m)
   width: 0.25                 # 轮胎宽度 (m)
   mass: 25.0                  # 轮胎质量 (kg)
   lat_stiff_x: 2.0            # 侧向刚度 X
   lat_stiff_y: 17.0           # 侧向刚度 Y
   long_stiff: 1000.0          # 纵向刚度
   friction: 1.0               # 摩擦系数
 ```
 
 ### 传动参数
 
 ```yaml
 transmission:
   engine:
     max_torque: 400.0         # 最大扭矩 (Nm)
     max_rpm: 7000.0           # 最大转速
     torque_curve: [...]       # 扭矩曲线
   
   gearbox:
     gear_ratios: [3.5, 2.5, 1.8, 1.4, 1.0, 0.8]
     final_drive: 3.5
   
   differential:
     type: limited_slip_4w
     front_rear_split: 0.5
 ```
 
 ### 姿态参数
 
 ```yaml
 pose:
   roll_stiffness: 10000.0     # 侧倾刚度
   roll_damping: 500.0         # 侧倾阻尼
   pitch_stiffness: 10000.0    # 俯仰刚度
   pitch_damping: 500.0        # 俯仰阻尼
   bounce_stiffness: 15000.0   # 晃动刚度
   bounce_damping: 800.0       # 晃动阻尼
 ```
