"""
Complete Vehicle System Test
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.business.vehicle_entity import VehicleEntity
from src.business.game_world import GameWorld
from src.systems.physics_system import PhysicsSystem
from src.systems.suspension_system import SuspensionSystem
from src.systems.pose_system import PoseSystem
from src.systems.wheel_system import WheelSystem
from src.systems.tire_system import TireSystem
from src.systems.transmission_system import TransmissionSystem

def create_config():
    return {
        'name': 'Sports Car',
        'position': [0, 0, 0.6],
        'heading': 0,
        
        'physics': {
            'max_speed': 200.0,
            'mass': 1500.0,
            'drag_coefficient': 0.3,
            'acceleration': 80.0,
            'deceleration': 40.0,
            'brake_deceleration': 120.0,
            'turn_speed': 200.0,
            'max_steering_angle': 40.0,
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
                {'position': [-0.9, 1.3, -0.35], 'natural_frequency': 7.0, 'damping_ratio': 1.0, 'rest_length': 0.3, 'max_compression': 0.1, 'max_droop': 0.1},
                {'position': [0.9, 1.3, -0.35], 'natural_frequency': 7.0, 'damping_ratio': 1.0, 'rest_length': 0.3, 'max_compression': 0.1, 'max_droop': 0.1},
                {'position': [-0.9, -1.3, -0.35], 'natural_frequency': 7.0, 'damping_ratio': 1.0, 'rest_length': 0.3, 'max_compression': 0.1, 'max_droop': 0.1},
                {'position': [0.9, -1.3, -0.35], 'natural_frequency': 7.0, 'damping_ratio': 1.0, 'rest_length': 0.3, 'max_compression': 0.1, 'max_droop': 0.1},
            ]
        },
        
        'tires': [
            {'lat_stiff_max_load': 2.0, 'lat_stiff_value': 17.0, 'long_stiff_value': 1000.0, 'friction': 1.0},
            {'lat_stiff_max_load': 2.0, 'lat_stiff_value': 17.0, 'long_stiff_value': 1000.0, 'friction': 1.0},
            {'lat_stiff_max_load': 2.0, 'lat_stiff_value': 17.0, 'long_stiff_value': 1200.0, 'friction': 1.1},
            {'lat_stiff_max_load': 2.0, 'lat_stiff_value': 17.0, 'long_stiff_value': 1200.0, 'friction': 1.1},
        ],
        
        'transmission': {
            'engine': {
                'moi': 1.0,
                'max_rpm': 7000.0,
                'torque_curve': [(0, 300), (1000, 350), (3000, 450), (5000, 420), (6500, 380), (7000, 0)],
                'damping_full_throttle': 0.15,
                'damping_zero_throttle_clutch_engaged': 2.0,
                'damping_zero_throttle_clutch_disengaged': 0.35,
            },
            'gear_ratios': [0, 3.5, 2.5, 1.8, 1.4, 1.0, 0.8],
            'final_ratio': 3.5,
            'reverse_ratio': -3.5,
            'auto_shift': True,
            'shift_time': 0.3,
            'clutch_strength': 10.0,
            'differential': {
                'diff_type': 'limited_slip',
                'front_rear_split': 0.5,
                'front_bias': 1.5,
                'rear_bias': 2.0,
            }
        },
        
        'pose': {
            'vehicle_mass': 1500.0,
            'track_width': 1.8,
            'wheelbase': 2.6,
            'cg_height': 0.5,
            'max_roll': 6.0,
            'max_pitch': 4.0,
            'roll_stiffness': 12000.0,
            'pitch_stiffness': 12000.0,
            'bounce_stiffness': 18000.0,
            'roll_damping': 600.0,
            'pitch_damping': 600.0,
            'bounce_damping': 900.0,
            'front_anti_roll': 1500.0,
            'rear_anti_roll': 1200.0,
        },
        
        'wheels': [
            {'position': [-0.9, 1.3, -0.35], 'radius': 0.35, 'can_steer': True, 'is_driven': True},
            {'position': [0.9, 1.3, -0.35], 'radius': 0.35, 'can_steer': True, 'is_driven': True},
            {'position': [-0.9, -1.3, -0.35], 'radius': 0.35, 'can_steer': False, 'is_driven': True},
            {'position': [0.9, -1.3, -0.35], 'radius': 0.35, 'can_steer': False, 'is_driven': True},
        ],
    }

def main():
    print("=" * 70)
    print("Complete Vehicle System Test")
    print("=" * 70)
    
    world = GameWorld()
    config = create_config()
    vehicle = VehicleEntity("player_car", config)
    
    print("\nRegistering systems...")
    vehicle.register_system('physics', PhysicsSystem(config['physics']))
    vehicle.register_system('suspension', SuspensionSystem(config['suspension']))
    vehicle.register_system('pose', PoseSystem(config['pose']))
    vehicle.register_system('wheels', WheelSystem(config['wheels']))
    vehicle.register_system('tires', TireSystem(config['tires']))
    vehicle.register_system('transmission', TransmissionSystem(config['transmission']))
    print("[OK] All systems registered")
    
    world.add_vehicle(vehicle)
    world.set_player_vehicle(vehicle)
    
    for name, system in vehicle._systems.items():
        system.initialize()
        print(f"[OK] {name} initialized")
    
    dt = 0.016
    total_time = 0.0
    max_time = 8.0
    
    print("\n" + "-" * 70)
    print("Starting simulation...")
    print("-" * 70)
    print(f"{'Time':>6} {'Speed':>8} {'Gear':>4} {'RPM':>6} {'Roll':>6} {'Pitch':>6} {'Status'}")
    print("-" * 70)
    
    while total_time < max_time:
        if total_time < 2.0:
            vehicle.set_throttle(1.0)
            vehicle.set_steering(0.0)
            status = "Accelerate"
        elif total_time < 4.0:
            vehicle.set_throttle(0.8)
            vehicle.set_steering(0.6)
            status = "Right"
        elif total_time < 6.0:
            vehicle.set_throttle(0.8)
            vehicle.set_steering(-0.6)
            status = "Left"
        else:
            vehicle.set_throttle(0.0)
            vehicle.set_brake(0.7)
            vehicle.set_steering(0.0)
            status = "Brake"
        
        vehicle.update(dt)
        
        if int(total_time * 2) > int((total_time - dt) * 2):
            state = vehicle.get_state()
            pose = vehicle.get_pose_state()
            trans = vehicle.get_transmission_state()
            
            print(f"{total_time:6.2f} {state.speed:8.1f} {trans.current_gear:4d} "
                  f"{state.engine_rpm:6.0f} {pose.roll:6.2f} {pose.pitch:6.2f}  {status}")
        
        total_time += dt
    
    print("-" * 70)
    print("Simulation complete!")
    print("=" * 70)
    
    print("\nFinal vehicle state:")
    state = vehicle.get_state()
    pose = vehicle.get_pose_state()
    trans = vehicle.get_transmission_state()
    
    print(f"  Position: ({state.position.x:.1f}, {state.position.y:.1f}, {state.position.z:.1f})")
    print(f"  Heading: {state.heading:.1f} deg")
    print(f"  Speed: {state.speed:.1f} km/h")
    print(f"  Engine RPM: {state.engine_rpm:.0f}")
    print(f"  Current Gear: {trans.current_gear}")
    print(f"  Roll: {pose.roll:.2f} deg")
    print(f"  Pitch: {pose.pitch:.2f} deg")
    print(f"  Bounce: {pose.bounce:.3f} m")
    
    print("\nTire states:")
    tires = vehicle.get_tire_states()
    for i, tire in enumerate(tires.tires):
        print(f"  Wheel {i}: LongForce={tire.long_force:.0f}N, LatForce={tire.lat_force:.0f}N, Slip={tire.long_slip:.2f}")
    
    print("\nShutting down...")
    for name, system in vehicle._systems.items():
        system.shutdown()
        print(f"[OK] {name} shutdown")
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
