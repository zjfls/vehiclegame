 # PhysXVehicles 业务模型深度分析
 
 ## 概述
 
 基于 PhysX SDK 的车辆模拟系统，包含复杂的悬挂、轮胎、传动和车身姿态模型。
 
 ---
 
 ## 1. 悬挂系统模型
 
 ### 1.1 悬挂参数计算
 
 **核心公式**：
 ```cpp
 // 弹簧刚度
 mSpringStrength = Square(SuspensionNaturalFrequency) * mSprungMass;
 
 // 阻尼率
 mSpringDamperRate = SuspensionDampingRatio * 2.0f * sqrt(mSpringStrength * mSprungMass);
 ```
 
 **参数说明**：
 - `SuspensionNaturalFrequency`：悬挂自然频率（标准车 5-10 Hz）
 - `SuspensionDampingRatio`：阻尼比（标准车 0.8-1.2）
 - `mSprungMass`：弹簧质量（由车辆质量和车轮位置自动计算）
 
 **物理意义**：
 - 自然频率决定了悬挂的"硬度"：频率越高，悬挂越硬
 - 阻尼比决定了悬挂的"响应"：阻尼越大，悬挂反应越快
 - 弹簧质量是分配到每个车轮的质量
 
 ### 1.2 弹簧质量计算
 
 **算法**：`PxVehicleComputeSprungMasses`
 ```cpp
 // 根据车辆质量、重心位置、车轮位置计算每个车轮的弹簧质量
 // 确保四个车轮的弹簧质量之和等于车辆质量
 PxVehicleComputeSprungMasses(
     NumWheels, 
     WheelOffsets,        // 车轮相对于重心的偏移
     COMPosition,         // 重心位置
     VehicleMass,         // 车辆质量
     GravityDirection,    // 重力方向（Z轴向上）
     SprungMasses         // 输出的弹簧质量
 );
 ```
 
 **关键点**：
 - 重心偏前的车辆，前轮弹簧质量更大
 - 重心偏后的车辆，后轮弹簧质量更大
 - 弹簧质量影响悬挂的压缩量和响应速度
 
 ### 1.3 悬挂力计算
 
 **弹簧力**：
 ```
 F_spring = -mSpringStrength * compression
 ```
 
 **阻尼力**：
 ```
 F_damper = -mSpringDamperRate * compression_velocity
 ```
 
 **总悬挂力**：
 ```
 F_total = F_spring + F_damper
 ```
 
 **压缩量限制**：
 - `mMaxCompression`：最大压缩量（车轮向上）
 - `mMaxDroop`：最大伸长量（车轮向下）
 - 超出范围时力为 0（车轮悬空）
 
 ### 1.4 悬挂力应用点
 
 **关键偏移**：
 ```cpp
 // 悬挂力应用点相对于重心的偏移
 PSuspForceAppCMOffset = PWheelCentreCMOffset + SuspensionForceOffset;
 
 // 轮胎力应用点（通常与悬挂相同）
 PTireForceAppCMOffset = PSuspForceAppCMOffset;
 ```
 
 **物理意义**：
 - 悬挂力应用点偏移会影响车身的俯仰和侧倾
 - 向上偏移会增加俯仰力矩
 - 向外偏移会增加侧倾力矩
 
 ### 1.5 防倾杆
 
 **作用**：减少车身侧倾
 ```cpp
 PxVehicleAntiRollBarData Data;
 Data.mWheel0 = 0;  // 左前轮
 Data.mWheel1 = 1;  // 右前轮
 Data.mStiffness = FrontAntiRollStiffness;
 ```
 
 **原理**：
 - 连接左右车轮
 - 当一个车轮压缩时，另一个车轮被拉起
 - 减少车身侧倾，提高稳定性
 
 ---
 
 ## 2. 轮胎模型
 
 ### 2.1 轮胎力计算（Pacejka-like 模型）
 
 **输入参数**：
 ```cpp
 const PxF32 tireFriction;           // 轮胎摩擦系数
 const PxF32 longSlip;                // 纵向打滑
 const PxF32 latSlip;                 // 侧向打滑
 const PxF32 camber;                  // 外倾角
 const PxF32 wheelOmega;              // 车轮角速度
 const PxF32 wheelRadius;             // 车轮半径
 const PxF32 restTireLoad;            // 静止时轮胎负载
 const PxF32 normalisedTireLoad;      // 归一化轮胎负载
 const PxF32 tireLoad;                // 当前轮胎负载
 const PxF32 gravity;                 // 重力加速度
 ```
 
 **输出参数**：
 ```cpp
 PxF32& wheelTorque;      // 车轮扭矩
 PxF32& tireLongForceMag; // 纵向力
 PxF32& tireLatForceMag;  // 侧向力
 PxF32& tireAlignMoment;  // 回正力矩
 ```
 
 ### 2.2 轮胎刚度计算
 
 **侧向刚度**：
 ```cpp
 const PxF32 latStiff = restTireLoad * tireData.mLatStiffY * 
                       smoothingFunction1(normalisedTireLoad * 3.0f / tireData.mLatStiffX);
 ```
 
 **纵向刚度**：
 ```cpp
 const PxF32 longStiff = tireData.mLongitudinalStiffnessPerUnitGravity * gravity;
 ```
 
 **外倾刚度**：
 ```cpp
 const PxF32 camberStiff = tireData.mCamberStiffnessPerUnitGravity * gravity;
 ```
 
 **关键点**：
 - 侧向刚度随负载非线性变化
 - 使用平滑函数 `smoothingFunction1` 处理非线性
 - 负载越大，刚度越大
 
 ### 2.3 平滑函数
 
 **smoothingFunction1**（用于力）：
 ```cpp
 PxF32 smoothingFunction1(PxF32 K) {
     // 在 K=0.75 处达到峰值，在 K=3 处降为 0
     return (K - K*K + ONE_THIRD*K*K*K - ONE_TWENTYSEVENTH*K*K*K*K);
 }
 ```
 
 **smoothingFunction2**（用于力矩）：
 ```cpp
 PxF32 smoothingFunction2(PxF32 K) {
     // 类似的平滑函数，用于力矩计算
     return (K - K*K + ONE_THIRD*K*K*K - ONE_TWENTYSEVENTH*K*K*K*K);
 }
 ```
 
 **物理意义**：
 - 轮胎力不是线性的，随着打滑增加先增大后减小
 - 峰值打滑率通常在 0.1-0.2 之间
 - 超过峰值后，轮胎开始滑动，力减小
 
 ### 2.4 轮胎力计算流程
 
 **步骤 1**：计算有效侧向角
 ```cpp
 const PxF32 TEff = PxTan(latSlip - camber * camberStiff / latStiff);
 ```
 
 **步骤 2**：计算力的大小
 ```cpp
 const PxF32 K = PxSqrt(latStiff * TEff * latStiff * TEff + 
                        longStiff * longSlip * longSlip * longSlip) / 
                        (tireFriction * tireLoad);
 ```
 
 **步骤 3**：应用平滑函数
 ```cpp
 PxF32 FBar = smoothingFunction1(K);
 PxF32 MBar = smoothingFunction2(K);
 ```
 
 **步骤 4**：计算纵向力和侧向力
 ```cpp
 const PxF32 FZero = tireFriction * tireLoad / 
                     PxSqrt(longSlip * longSlip + nu * TEff * nu * TEff);
 const PxF32 fz = longSlip * FBar * FZero;      // 纵向力
 const PxF32 fx = -nu * TEff * FBar * FZero;    // 侧向力
 ```
 
 **步骤 5**：计算车轮扭矩
 ```cpp
 wheelTorque = -fz * wheelRadius;
 ```
 
 ---
 
 ## 3. 传动系统模型
 
 ### 3.1 发动机模型
 
 **发动机配置**：
 ```cpp
 struct PxVehicleEngineData {
     PxF32 mMOI;                              // 转动惯量
     PxF32 mPeakTorque;                       // 峰值扭矩
     PxF32 mMaxOmega;                         // 最大转速
     PxF32 mDampingRateFullThrottle;          // 全油门阻尼
     PxF32 mDampingRateZeroThrottleClutchEngaged;     // 零油门阻尼（离合器接合）
     PxF32 mDampingRateZeroThrottleClutchDisengaged;   // 零油门阻尼（离合器分离）
     PxVehicleEngineDriveTypeEnum mDriveType;  // 驱动类型（前驱、后驱、四驱）
     PxF32 mTorqueCurve[4];                   // 扭矩曲线（控制点）
 };
 ```
 
 **扭矩曲线**：
 - 使用贝塞尔曲线或查找表
 - 典型形状：低转速扭矩上升，中转速达到峰值，高转速下降
 - UE 中使用 `FRuntimeFloatCurve` 编辑
 
 ### 3.2 变速箱模型
 
 **档位配置**：
 ```cpp
 struct PxVehicleGearsData {
     PxF32 mRatios[PxVehicleGearsData::eGEARSRATIO_COUNT];  // 档位比
     PxF32 mFinalRatio;                      // 主减速比
     PxU32 mNbRatios;                        // 档位数量
 };
 ```
 
 **档位比示例**：
 - 1档：3.5
 - 2档：2.5
 - 3档：1.8
 - 4档：1.4
 - 5档：1.0
 - 倒档：-3.5
 - 主减速比：3.5
 
 **总传动比**：
 ```
 total_ratio = gear_ratio * final_ratio
 ```
 
 ### 3.3 差速器模型
 
 **差速器类型**：
 ```cpp
 enum PxVehicleDifferential4WData::Enum {
     eDIFF_TYPE_LS_4WD,           // 限滑差速（四驱）
     eDIFF_TYPE_LS_FRONTWD,       // 限滑差速（前驱）
     eDIFF_TYPE_LS_REARWD,        // 限滑差速（后驱）
     eDIFF_TYPE_OPEN_4WD,         // 开放差速（四驱）
     eDIFF_TYPE_OPEN_FRONTWD,     // 开放差速（前驱）
     eDIFF_TYPE_OPEN_REARWD,      // 开放差速（后驱）
 };
 ```
 
 **扭矩分配**：
 - 前后分配：`mFrontRearSplit`（0.5 = 50:50）
 - 左前分配：`mFrontLeftRightSplit`
 - 左后分配：`mRearLeftRightSplit`
 - 限滑系数：`mFrontBias`、`mRearBias`
 
 ### 3.4 离合器模型
 
 **离合器配置**：
 ```cpp
 struct PxVehicleClutchData {
     PxF32 mStrength;  // 离合器强度
 };
 ```
 
 **离合器作用**：
 - 平滑扭矩传递
 - 防止换档冲击
 - 强度越高，换档越快
 
 ### 3.5 自动变速箱
 
 **自动换档配置**：
 ```cpp
 struct PxVehicleAutoBoxData {
     PxF32 mUpRatios[PxVehicleGearsData::eGEARSRATIO_COUNT];  // 升档转速比
     PxF32 mDownRatios[PxVehicleGearsData::eGEARSRATIO_COUNT]; // 降档转速比
     PxU32 mLatency;  // 换档延迟（帧数）
 };
 ```
 
 **换档逻辑**：
 - 升档：发动机转速 > 最大转速 * 升档比
 - 降档：发动机转速 < 最大转速 * 降档比
 - 延迟：防止频繁换档
 
 ---
 
 ## 4. Ackermann 转向几何
 
 **Ackermann 配置**：
 ```cpp
 struct PxVehicleAckermannGeometryData {
     PxF32 mAccuracy;      // Ackermann 精度（0-1）
     PxF32 mAxleSeparation; // 轴距（前后轮距离）
     PxF32 mFrontWidth;    // 前轮距
     PxF32 mRearWidth;     // 后轮距
 };
 ```
 
 **Ackermann 转向原理**：
 - 内侧车轮转向角 > 外侧车轮转向角
 - 减少轮胎磨损
 - 提高转向稳定性
 
 **转向角计算**：
 ```
 cot(δ_outer) - cot(δ_inner) = track_width / wheelbase
 ```
 
 ---
 
 ## 5. 车身姿态影响
 
 ### 5.1 悬挂压缩差异导致姿态
 
 **俯仰**：
 ```
 pitch ∝ (front_compression - rear_compression)
 ```
 
 **侧倾**：
 ```
 roll ∝ (left_compression - right_compression)
 ```
 
 ### 5.2 加速度导致姿态
 
 **纵向加速度 → 俯仰**：
 - 加速：车头抬起（负俯仰）
 - 刹车：车头下沉（正俯仰）
 
 **横向加速度 → 侧倾**：
 - 左转：车身向右倾斜（正侧倾）
 - 右转：车身向左倾斜（负侧倾）
 
 ### 5.3 防倾杆影响
 
 **防倾杆作用**：
 - 减少侧倾
 - 提高转向响应
 - 增加转向不足/过度特性
 
 ---
 
 ## 6. 输入平滑
 
 **平滑配置**：
 ```cpp
 struct PxVehiclePadSmoothingData {
     PxF32 mRiseRates[5];  // 上升速率（油门、刹车、手刹、转向左、转向右）
     PxF32 mFallRates[5];  // 下降速率
 };
 ```
 
 **平滑算法**：
 ```
 if (rising) {
     value += rise_rate * dt;
 } else {
     value -= fall_rate * dt;
 }
 value = clamp(value, 0.0, 1.0);
 ```
 
 **转向速度曲线**：
 - 使用查找表
 - 速度越快，转向角越小
 - 提高高速稳定性
 
 ---
 ## 7. 子步控制
 
 **子步配置**：
 ```cpp
 PWheelsSimData->setSubStepCount(
     ThresholdLongitudinalSpeed,  // 阈值速度
     LowForwardSpeedSubStepCount,   // 低速时子步数
     HighForwardSpeedSubStepCount   // 高速时子步数
 );
 ```
 
 **子步作用**：
 - 低速时使用更多子步，提高稳定性
 - 高速时使用较少子步，提高性能
 - 典型值：低速 3 子步，高速 1 子步
 
 ---
 ## 8. 关键业务模型总结
 
 ### 悬挂系统
 | 参数 | 计算公式 | 物理意义 |
 |------|----------|----------|
 | 弹簧刚度 | ω² × m | 悬挂硬度 |
 | 阻尼率 | 2ζ√(k×m) | 悬挂响应速度 |
 | 弹簧质量 | 自动计算 | 分配到每个车轮的质量 |
 
 ### 轮胎系统
 | 参数 | 计算公式 | 物理意义 |
 |------|----------|----------|
 | 侧向刚度 | F₀ × LatStiffY × f(K) | 轮胎侧向抓地力 |
 | 纵向刚度 | LongStiff × g | 轮胎纵向抓地力 |
 | 轮胎力 | F = μ × N × f(slip) | 轮胎产生的力 |
 
 ### 传动系统
 | 参数 | 计算公式 | 物理意义 |
 |------|----------|----------|
 | 总传动比 | gear_ratio × final_ratio | 扭矩放大倍数 |
 | 轮上扭矩 | engine_torque × total_ratio | 实际驱动力 |
 | 发动机转速 | wheel_speed × total_ratio | 发动机转速 |
 
 ### 姿态系统
 | 参数 | 影响因素 | 物理意义 |
 |------|----------|----------|
 | 俯仰 | 悬挂差异 + 纵向加速度 | 车头上下 |
 | 侧倾 | 悬挂差异 + 横向加速度 | 车身左右倾斜 |
 | 晃动 | 悬挂压缩平均值 | 车身上下运动 |
 
 ---
 ## 9. 对实现的建议
 
 1. **悬挂系统**：
    - 使用自然频率和阻尼比作为配置参数
    - 自动计算弹簧质量
    - 实现防倾杆
    - 考虑悬挂力应用点偏移
 
 2. **轮胎系统**：
    - 实现简化的 Pacejka 模型
    - 考虑轮胎刚度随负载变化
    - 实现平滑函数
    - 计算纵向和侧向力
 
 3. **传动系统**：
    - 实现扭矩曲线
    - 实现档位比和主减速比
    - 实现差速器扭矩分配
    - 实现自动换档逻辑
 
 4. **姿态系统**：
    - 基于悬挂压缩差异计算姿态
    - 基于加速度计算姿态
    - 考虑防倾杆影响
    - 实现姿态阻尼
 
 5. **输入平滑**：
    - 实现上升/下降速率控制
    - 实现转向速度曲线
    - 使用平滑插值
 
 6. **子步控制**：
    - 低速时使用更多子步
    - 高速时使用较少子步
    - 提高稳定性
