"""
传动状态数据定义
"""
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class EngineConfig:
    """发动机配置"""
    moi: float = 1.0                     # 转动惯量 (kg*m²)
    max_rpm: float = 6000.0              # 最大转速
    torque_curve: List[Tuple[float, float]] = None  # [(RPM, Torque), ...]
    damping_full_throttle: float = 0.15  # 全油门阻尼
    damping_zero_throttle_clutch_engaged: float = 2.0
    damping_zero_throttle_clutch_disengaged: float = 0.35
    
    def __post_init__(self):
        if self.torque_curve is None:
            # 默认扭矩曲线
            self.torque_curve = [
                (0, 300),
                (3000, 400),
                (5000, 350),
                (6000, 0)
            ]

@dataclass
class DifferentialConfig:
    """差速器配置"""
    diff_type: str = 'limited_slip'      # 类型: 'open', 'limited_slip'
    front_rear_split: float = 0.5        # 前后扭矩分配 (0.5=均衡)
    front_bias: float = 1.5              # 前轴限滑比
    rear_bias: float = 2.0               # 后轴限滑比

@dataclass
class TransmissionState:
    """传动状态"""
    engine_rpm: float = 800.0            # 发动机转速
    current_gear: int = 1                # 当前档位
    clutch_position: float = 0.0         # 离合器位置 (0-1)
    wheel_torques: List[float] = None    # 各车轮扭矩
    is_shifting: bool = False            # 是否正在换档
    shift_timer: float = 0.0             # 换档计时器
    
    def __post_init__(self):
        if self.wheel_torques is None:
            self.wheel_torques = [0.0, 0.0, 0.0, 0.0]
