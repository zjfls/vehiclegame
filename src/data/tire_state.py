"""
轮胎状态数据定义
"""
from dataclasses import dataclass
from typing import List

@dataclass
class TireConfig:
    """轮胎配置"""
    # 侧向刚度
    lat_stiff_max_load: float = 2.0    # 最大负载时的侧向刚度
    lat_stiff_value: float = 17.0      # 侧向刚度值
    
    # 纵向刚度
    long_stiff_value: float = 1000.0   # 纵向刚度
    
    # 摩擦
    friction: float = 1.0              # 摩擦系数

@dataclass
class TireState:
    """轮胎状态"""
    # 打滑
    long_slip: float = 0.0             # 纵向打滑率
    lat_slip: float = 0.0              # 侧向打滑角（弧度）
    
    # 力
    long_force: float = 0.0            # 纵向力 (N)
    lat_force: float = 0.0             # 侧向力 (N)
    align_moment: float = 0.0          # 回正力矩 (Nm)
    
    # 负载
    tire_load: float = 0.0             # 轮胎负载 (N)
    normalized_tire_load: float = 1.0  # 归一化负载
    rest_tire_load: float = 0.0        # 静止时轮胎负载
    
    # 车轮扭矩
    wheel_torque: float = 0.0          # 车轮扭矩

@dataclass
class TiresState:
    """所有轮胎状态"""
    tires: List[TireState] = None
    
    def __post_init__(self):
        if self.tires is None:
            self.tires = []
    
    def get_tire_state(self, index: int) -> TireState:
        """获取指定轮胎的状态"""
        if index < len(self.tires):
            return self.tires[index]
        return TireState()
    
    def set_tire_count(self, count: int):
        """设置轮胎数量"""
        while len(self.tires) < count:
            self.tires.append(TireState())
