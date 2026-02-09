"""
游戏世界 - 业务层
管理所有车辆实体和场景环境
"""
from typing import Dict, List, Optional
from .vehicle_entity import VehicleEntity

class GameWorld:
    """
    游戏世界
    
    职责：
    - 管理所有车辆实体
    - 管理场景环境
    - 处理车辆间交互
    """
    
    def __init__(self):
        # 所有车辆实体
        self._vehicles: Dict[str, VehicleEntity] = {}
        
        # 玩家控制的车辆
        self._player_vehicle_id: Optional[str] = None
        
        # 场景配置
        self._scene_config = {}
    
    def add_vehicle(self, vehicle: VehicleEntity) -> None:
        """添加车辆到世界"""
        self._vehicles[vehicle.vehicle_id] = vehicle
    
    def remove_vehicle(self, vehicle_id: str) -> None:
        """从世界移除车辆"""
        if vehicle_id in self._vehicles:
            del self._vehicles[vehicle_id]
    
    def get_vehicle(self, vehicle_id: str) -> Optional[VehicleEntity]:
        """获取指定车辆"""
        return self._vehicles.get(vehicle_id)
    
    def get_all_vehicles(self) -> List[VehicleEntity]:
        """获取所有车辆"""
        return list(self._vehicles.values())
    
    def set_player_vehicle(self, vehicle_id: str) -> None:
        """设置玩家控制的车辆"""
        if vehicle_id in self._vehicles:
            self._player_vehicle_id = vehicle_id
    
    def get_player_vehicle(self) -> Optional[VehicleEntity]:
        """获取玩家控制的车辆"""
        if self._player_vehicle_id:
            return self._vehicles.get(self._player_vehicle_id)
        return None
    
    def update(self, dt: float) -> None:
        """更新世界中所有车辆"""
        for vehicle in self._vehicles.values():
            vehicle.update(dt)
    
    def set_scene_config(self, config: dict) -> None:
        """设置场景配置"""
        self._scene_config = config
    
    def get_scene_config(self) -> dict:
        """获取场景配置"""
        return self._scene_config
