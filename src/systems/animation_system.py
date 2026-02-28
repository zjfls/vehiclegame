"""
动画系统 - 系统层
将物理状态应用到 Panda3D 渲染
"""
import math
from panda3d.core import Vec3, LQuaternionf
from .base_system import SystemBase
from .update_context import SystemUpdateContext
from ..data.vehicle_state import VehicleState

class AnimationSystem(SystemBase):
    """
    动画系统
    
    职责：
    - 驱动车身动画（晃动、颠簸）
    - 驱动悬挂动画（压缩/回弹）
    - 驱动车轮动画（旋转、转向）
    """
    
    def __init__(self, game, config: dict = None):
        super().__init__(config)
        self.game = game
        # Panda3D 节点
        self.vehicle_node = None
        self.body_node = None
        self.wheel_nodes = []
        
        # 配置
        self.wheel_configs = config.get('wheels', []) if config else []
        
        # 平滑因子
        self.smooth_factor = 0.3
    
    def set_vehicle_node(self, vehicle_node):
        """设置车辆节点"""
        self.vehicle_node = vehicle_node
        
        # 查找车身节点
        if vehicle_node:
            self.body_node = vehicle_node.find("body") or vehicle_node
            
            # 查找车轮节点
            self.wheel_nodes = []
            for i in range(4):
                wheel = vehicle_node.find(f"wheel_{i}") or vehicle_node.find(f"wheel{i}")
                self.wheel_nodes.append(wheel)
    
    def update(self, ctx: SystemUpdateContext) -> None:
        """更新动画"""
        vehicle_state = ctx.vehicle_state
        pose_state = ctx.pose_state
        suspension_state = ctx.suspension_state
        wheels_state = ctx.wheels_state
        if pose_state is None or suspension_state is None or wheels_state is None:
            return
        if not self.vehicle_node:
            return
        
        # 1. 更新车身位置和旋转
        self._update_body_transform(vehicle_state, pose_state)
        
        # 2. 更新车轮
        for i, wheel_node in enumerate(self.wheel_nodes):
            if i < len(wheels_state.wheels) and wheel_node:
                self._update_wheel(i, wheel_node, wheels_state.wheels[i], 
                                  suspension_state.wheels[i] if i < len(suspension_state.wheels) else None)
    
    def _update_body_transform(self, vehicle_state: VehicleState, pose_state: PoseState):
        """更新车身变换"""
        # 位置
        pos = vehicle_state.position
        # 加上晃动偏移
        bounce = pose_state.bounce
        
        # 平滑位置
        current_pos = self.vehicle_node.getPos()
        target_x = current_pos[0] + (pos.x - current_pos[0]) * self.smooth_factor
        target_y = current_pos[1] + (pos.y - current_pos[1]) * self.smooth_factor
        target_z = current_pos[2] + ((pos.z + bounce) - current_pos[2]) * self.smooth_factor
        
        self.vehicle_node.setPos(target_x, target_y, target_z)
        
        # 旋转
        # 航向角
        heading = vehicle_state.heading
        
        # 姿态角
        roll = pose_state.roll
        pitch = pose_state.pitch
        
        # 应用旋转
        self.vehicle_node.setHpr(heading, pitch, roll)
    
    def _update_wheel(self, index: int, wheel_node, wheel_state, suspension_state):
        """更新单个车轮"""
        # 1. 更新位置（考虑悬挂压缩）
        if suspension_state:
            # 悬挂压缩导致的车轮垂直偏移
            compression_offset = suspension_state.wheel_offset.z
            
            # 获取原始位置
            original_pos = self.wheel_configs[index].get('position', [0, 0, 0]) if index < len(self.wheel_configs) else [0, 0, 0]
            
            # 应用悬挂偏移
            wheel_node.setPos(
                original_pos[0],
                original_pos[1],
                original_pos[2] + compression_offset
            )
        
        # 2. 更新旋转
        # 转向角（只影响航向）
        steering = wheel_state.steering_angle
        
        # 旋转角（车轮滚动）
        rotation = wheel_state.rotation_angle
        
        # 应用旋转
        wheel_node.setHpr(steering, 0, rotation)
    
    def create_wheel_visual(self, parent_node, wheel_index: int, radius: float = 0.35):
        """创建车轮可视化（使用简单的几何体）"""
        from panda3d.core import GeomNode, Geom, GeomVertexData, GeomVertexFormat
        from panda3d.core import GeomTriangles, GeomVertexWriter
        
        # 创建车轮节点
        wheel = parent_node.attachNewNode(f"wheel_{wheel_index}")
        
        # 使用简单的圆柱体（box）表示车轮
        wheel_model = self.game.loader.loadModel("box")
        wheel_model.reparentTo(wheel)
        wheel_model.setScale(0.1, radius, radius)
        wheel_model.setColor(0.1, 0.1, 0.1, 1.0)
        
        return wheel
    
    def create_body_visual(self, parent_node):
        """创建车身可视化"""
        # 车身节点
        body = parent_node.attachNewNode("body")
        
        # 底盘
        chassis = self.game.loader.loadModel("box")
        chassis.reparentTo(body)
        chassis.setScale(1.6, 3.2, 0.5)
        chassis.setPos(0, 0, -0.2)
        chassis.setColor(0.8, 0.1, 0.1, 1.0)
        
        # 车顶
        cabin = self.game.loader.loadModel("box")
        cabin.reparentTo(body)
        cabin.setScale(1.0, 1.4, 0.5)
        cabin.setPos(0, -0.3, 0.6)
        cabin.setColor(0.2, 0.2, 0.3, 1.0)
        
        # 引擎盖
        hood = self.game.loader.loadModel("box")
        hood.reparentTo(body)
        hood.setScale(1.3, 0.8, 0.15)
        hood.setPos(0, 1.0, 0.35)
        hood.setColor(0.8, 0.1, 0.1, 1.0)
        
        return body
