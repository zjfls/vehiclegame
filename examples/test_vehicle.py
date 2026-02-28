"""
测试车辆实体和系统
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.business.vehicle_entity import VehicleEntity
from src.business.game_world import GameWorld
from src.systems.physics_system import PhysicsSystem
from src.systems.suspension_system import SuspensionSystem
from src.systems.pose_system import PoseSystem
from src.systems.wheel_system import WheelSystem

def create_vehicle_config():
    """创建车辆配置"""
    return {
        'name': 'Sports Car',
        'position': [0, 0, 0.6],
        'heading': 0,
        
        'physics': {
            'max_speed': 120.0,
            'mass': 1500.0,
            'drag_coefficient': 0.3,
            'acceleration': 60.0,
            'deceleration': 30.0,
            'brake_deceleration': 100.0,
            'turn_speed': 180.0,
            'max_steering_angle': 35.0,
            'input_smoothing': {
                'throttle_rise': 8.0,
                'throttle_fall': 12.0,
                'brake_rise': 8.0,
                'brake_fall': 12.0,
                'steering_rise': 3.0,
                'steering_fall': 6.0,
            }
        },
        
        'suspension': {
            'vehicle_mass': 1500.0,
            'com_position': [0, 0, 0.3],
            'wheels': [
                {
                    'position': [-0.9, 1.3, -0.35],
                    'natural_frequency': 7.0,
                    'damping_ratio': 1.0,
                    'rest_length': 0.3,
                    'max_compression': 0.1,
                    'max_droop': 0.1,
                },
                {
                    'position': [0.9, 1.3, -0.35],
                    'natural_frequency': 7.0,
                    'damping_ratio': 1.0,
                    'rest_length': 0.3,
                    'max_compression': 0.1,
                    'max_droop': 0.1,
                },
                {
                    'position': [-0.9, -1.3, -0.35],
                    'natural_frequency': 7.0,
                    'damping_ratio': 1.0,
                    'rest_length': 0.3,
                    'max_compression': 0.1,
                    'max_droop': 0.1,
                },
                {
                    'position': [0.9, -1.3, -0.35],
                    'natural_frequency': 7.0,
                    'damping_ratio': 1.0,
                    'rest_length': 0.3,
                    'max_compression': 0.1,
                    'max_droop': 0.1,
                },
            ]
        },
        
        'pose': {
            'vehicle_mass': 1500.0,
            'track_width': 1.8,
            'wheelbase': 2.6,
            'cg_height': 0.5,
            'max_roll': 5.0,
            'max_pitch': 3.0,
            'roll_stiffness': 10000.0,
            'pitch_stiffness': 10000.0,
            'bounce_stiffness': 15000.0,
            'roll_damping': 500.0,
            'pitch_damping': 500.0,
            'bounce_damping': 800.0,
            'front_anti_roll': 1000.0,
            'rear_anti_roll': 1000.0,
        },
        
        'wheels': [
            {'position': [-0.9, 1.3, -0.35], 'radius': 0.35, 'can_steer': True, 'is_driven': True},
            {'position': [0.9, 1.3, -0.35], 'radius': 0.35, 'can_steer': True, 'is_driven': True},
            {'position': [-0.9, -1.3, -0.35], 'radius': 0.35, 'can_steer': False, 'is_driven': True},
            {'position': [0.9, -1.3, -0.35], 'radius': 0.35, 'can_steer': False, 'is_driven': True},
        ],
    }

def main():
    """主函数"""
    print("=" * 60)
    print("Panda3D 赛车游戏 - 车辆系统测试")
    print("=" * 60)
    
    # 创建游戏世界
    world = GameWorld()
    
    # 创建车辆配置
    config = create_vehicle_config()
    
    # 创建车辆实体
    vehicle = VehicleEntity("player_car", config)
    
    # 注册系统
    vehicle.register_system('physics', PhysicsSystem(config['physics']))
    vehicle.register_system('suspension', SuspensionSystem(config['suspension']))
    vehicle.register_system('pose', PoseSystem(config['pose']))
    vehicle.register_system('wheels', WheelSystem(config['wheels']))
    
    # 添加到世界
    world.add_vehicle(vehicle)
    world.set_player_vehicle(vehicle)
    
    # 初始化系统
    vehicle.initialize_systems()
    
    # 模拟游戏循环
    dt = 0.016  # 60 FPS
    total_time = 0.0
    max_time = 5.0  # 模拟 5 秒
    
    print("\n开始模拟...")
    print("-" * 60)
    
    while total_time < max_time:
        # 设置控制输入
        if total_time < 2.0:
            vehicle.set_throttle(1.0)
            vehicle.set_steering(0.0)
        elif total_time < 3.5:
            vehicle.set_throttle(0.8)
            vehicle.set_steering(0.5)
        else:
            vehicle.set_throttle(0.0)
            vehicle.set_brake(0.5)
            vehicle.set_steering(0.0)
        
        # 更新车辆
        vehicle.update(dt)
        
        # 每 0.5 秒打印一次状态
        if int(total_time * 2) > int((total_time - dt) * 2):
            state = vehicle.get_state()
            pose = vehicle.get_pose_state()
            suspension = vehicle.get_wheel_suspension_state(0)
            
            print(f"\n时间: {total_time:.2f}s")
            print(f"  速度: {state.speed:.1f} km/h")
            print(f"  位置: ({state.position.x:.1f}, {state.position.y:.1f})")
            print(f"  航向: {state.heading:.1f}°")
            print(f"  转向角: {state.steering_angle:.1f}°")
            print(f"  侧倾: {pose.roll:.2f}°")
            print(f"  俯仰: {pose.pitch:.2f}°")
            print(f"  晃动: {pose.bounce:.3f}m")
            print(f"  左前悬挂压缩: {suspension.compression:.3f}m")
        
        total_time += dt
    
    print("\n" + "-" * 60)
    print("模拟完成！")
    print("=" * 60)
    
    # 关闭系统
    vehicle.shutdown_systems()

if __name__ == "__main__":
    main()
