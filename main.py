"""
Panda3D Racing Game - Main Entry Point
Complete vehicle physics system integration
"""
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import *
import math
import sys

# Import our vehicle systems
from src.business.vehicle_entity import VehicleEntity
from src.business.game_world import GameWorld
from src.systems.physics_system import PhysicsSystem
from src.systems.suspension_system import SuspensionSystem
from src.systems.pose_system import PoseSystem
from src.systems.wheel_system import WheelSystem
from src.systems.tire_system import TireSystem
from src.systems.transmission_system import TransmissionSystem

class RacingGame(ShowBase):
    """
    Main game class using the vehicle physics system
    """
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.setBackgroundColor(0.15, 0.18, 0.22)
        
        # Setup display
        props = WindowProperties()
        props.setSize(1280, 720)
        props.setTitle("Panda3D Racing Game")
        self.win.requestProperties(props)
        
        # Initialize game world
        self.world = GameWorld()
        
        # Create vehicle configuration
        self.vehicle_config = self._create_vehicle_config()
        
        # Create player vehicle
        self.player_vehicle = VehicleEntity("player", self.vehicle_config)
        
        # Register all systems
        self._register_systems()
        
        # Add to world
        self.world.add_vehicle(self.player_vehicle)
        self.world.set_player_vehicle("player")
        
        # Initialize all systems
        for name, system in self.player_vehicle._systems.items():
            system.initialize()
        
        # Setup visuals
        self.setup_lights()
        self.setup_scene()
        self.create_vehicle_visuals()
        self.setup_camera()
        self.setup_inputs()
        self.setup_ui()
        
        # Add update task
        self.taskMgr.add(self.update, "UpdateTask")
        
        print("Racing Game Initialized!")
        print("Controls: W/S - Throttle/Brake, A/D - Steering, ESC - Exit")
    
    def _create_vehicle_config(self):
        """Create vehicle configuration"""
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
                    {'position': [-0.9, 1.3, -0.35], 'natural_frequency': 7.0, 'damping_ratio': 1.0, 
                     'rest_length': 0.3, 'max_compression': 0.1, 'max_droop': 0.1},
                    {'position': [0.9, 1.3, -0.35], 'natural_frequency': 7.0, 'damping_ratio': 1.0,
                     'rest_length': 0.3, 'max_compression': 0.1, 'max_droop': 0.1},
                    {'position': [-0.9, -1.3, -0.35], 'natural_frequency': 7.0, 'damping_ratio': 1.0,
                     'rest_length': 0.3, 'max_compression': 0.1, 'max_droop': 0.1},
                    {'position': [0.9, -1.3, -0.35], 'natural_frequency': 7.0, 'damping_ratio': 1.0,
                     'rest_length': 0.3, 'max_compression': 0.1, 'max_droop': 0.1},
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
    
    def _register_systems(self):
        """Register all vehicle systems"""
        config = self.vehicle_config
        self.player_vehicle.register_system('physics', PhysicsSystem(config['physics']))
        self.player_vehicle.register_system('suspension', SuspensionSystem(config['suspension']))
        self.player_vehicle.register_system('pose', PoseSystem(config['pose']))
        self.player_vehicle.register_system('wheels', WheelSystem(config['wheels']))
        self.player_vehicle.register_system('tires', TireSystem(config['tires']))
        self.player_vehicle.register_system('transmission', TransmissionSystem(config['transmission']))
    
    def setup_lights(self):
        """Setup scene lighting"""
        # Ambient light
        ambient_light = AmbientLight("ambient_light")
        ambient_light.setColor((0.4, 0.4, 0.45, 1))
        ambient_np = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_np)
        
        # Directional light
        directional_light = DirectionalLight("directional_light")
        directional_light.setColor((0.9, 0.85, 0.8, 1))
        directional_light.setDirection((0.5, -0.8, -0.3))
        directional_np = self.render.attachNewNode(directional_light)
        self.render.setLight(directional_np)
        
        self.render.setShaderAuto()
    
    def setup_scene(self):
        """Setup the racing track and ground"""
        # Ground
        cm = CardMaker("ground")
        cm.setFrame(-500, 500, -500, 500)
        self.ground = self.render.attachNewNode(cm.generate())
        self.ground.setP(-90)
        self.ground.setPos(0, 0, 0)
        self.ground.setColor(0.15, 0.18, 0.15, 1)
        
        # Track center line
        cm_line = CardMaker("track_line")
        cm_line.setFrame(-1.2, 1.2, -500, 500)
        self.track_line = self.render.attachNewNode(cm_line.generate())
        self.track_line.setP(-90)
        self.track_line.setPos(0, 0, 0.01)
        self.track_line.setColor(0.25, 0.25, 0.3, 1)
        
        # Track borders
        for x_offset in [-15, 15]:
            cm_border = CardMaker(f"border_{x_offset}")
            cm_border.setFrame(-1.5, 1.5, -500, 500)
            border = self.render.attachNewNode(cm_border.generate())
            border.setP(-90)
            border.setPos(x_offset, 0, 0.02)
            border.setColor(0.7, 0.1, 0.1, 1)
        
        # Track markers
        for i in range(-200, 201, 30):
            marker = self.loader.loadModel("box")
            marker.reparentTo(self.render)
            marker.setScale(1, 1, 1)
            marker.setPos(15, i, 0.5)
            marker.setColor(0.9, 0.15, 0.15, 1)
            
            marker2 = self.loader.loadModel("box")
            marker2.reparentTo(self.render)
            marker2.setScale(1, 1, 1)
            marker2.setPos(-15, i, 0.5)
            marker2.setColor(0.1, 0.15, 0.9, 1)
    
    def create_vehicle_visuals(self):
        """Create the vehicle 3D model"""
        # Main vehicle node
        self.vehicle_node = self.render.attachNewNode("vehicle")
        
        # Body node
        self.body_node = self.vehicle_node.attachNewNode("body")
        
        # Chassis
        chassis = self.loader.loadModel("box")
        chassis.reparentTo(self.body_node)
        chassis.setScale(1.6, 3.2, 0.5)
        chassis.setPos(0, 0, -0.2)
        chassis.setColor(0.8, 0.1, 0.1, 1)
        
        # Cabin
        cabin = self.loader.loadModel("box")
        cabin.reparentTo(self.body_node)
        cabin.setScale(1.0, 1.4, 0.5)
        cabin.setPos(0, -0.3, 0.6)
        cabin.setColor(0.2, 0.2, 0.3, 1)
        
        # Hood
        hood = self.loader.loadModel("box")
        hood.reparentTo(self.body_node)
        hood.setScale(1.3, 0.8, 0.15)
        hood.setPos(0, 1.0, 0.35)
        hood.setColor(0.8, 0.1, 0.1, 1)
        
        # Trunk
        trunk = self.loader.loadModel("box")
        trunk.reparentTo(self.body_node)
        trunk.setScale(1.3, 0.6, 0.15)
        trunk.setPos(0, -1.1, 0.35)
        trunk.setColor(0.8, 0.1, 0.1, 1)
        
        # Wheels
        self.wheel_nodes = []
        wheel_positions = [
            (-0.9, 1.3, -0.35),   # Front left
            (0.9, 1.3, -0.35),    # Front right
            (-0.9, -1.3, -0.35),  # Rear left
            (0.9, -1.3, -0.35),   # Rear right
        ]
        
        for i, pos in enumerate(wheel_positions):
            wheel = self.loader.loadModel("box")
            wheel.reparentTo(self.vehicle_node)
            wheel.setScale(0.25, 0.5, 0.5)
            wheel.setPos(pos)
            wheel.setColor(0.1, 0.1, 0.1, 1)
            self.wheel_nodes.append(wheel)
    
    def setup_camera(self):
        """Setup the camera"""
        self.camera_distance = 20.0
        self.camera_height = 12.0
        self.camera_smooth = 0.1
    
    def setup_inputs(self):
        """Setup keyboard input handling"""
        self.keys = {
            "throttle": 0.0,
            "brake": 0.0,
            "steering": 0.0,
            "handbrake": False
        }
        
        # Throttle
        self.accept("w", self.set_key, ["throttle", 1.0])
        self.accept("w-up", self.set_key, ["throttle", 0.0])
        self.accept("arrow_up", self.set_key, ["throttle", 1.0])
        self.accept("arrow_up-up", self.set_key, ["throttle", 0.0])
        
        # Brake
        self.accept("s", self.set_key, ["brake", 1.0])
        self.accept("s-up", self.set_key, ["brake", 0.0])
        self.accept("arrow_down", self.set_key, ["brake", 1.0])
        self.accept("arrow_down-up", self.set_key, ["brake", 0.0])
        
        # Steering
        self.accept("a", self.set_key, ["steering", -1.0])
        self.accept("a-up", self.set_key, ["steering", 0.0])
        self.accept("arrow_left", self.set_key, ["steering", -1.0])
        self.accept("arrow_left-up", self.set_key, ["steering", 0.0])
        
        self.accept("d", self.set_key, ["steering", 1.0])
        self.accept("d-up", self.set_key, ["steering", 0.0])
        self.accept("arrow_right", self.set_key, ["steering", 1.0])
        self.accept("arrow_right-up", self.set_key, ["steering", 0.0])
        
        # Handbrake
        self.accept("space", self.set_key, ["handbrake", True])
        self.accept("space-up", self.set_key, ["handbrake", False])
        
        # Exit
        self.accept("escape", self.exit_game)
    
    def set_key(self, key, value):
        """Handle key input"""
        self.keys[key] = value
    
    def setup_ui(self):
        """Setup UI elements"""
        # Speed display
        self.speed_text = OnscreenText(
            text="Speed: 0 km/h",
            pos=(-0.9, 0.9),
            scale=0.07,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )
        
        # RPM display
        self.rpm_text = OnscreenText(
            text="RPM: 0",
            pos=(-0.9, 0.8),
            scale=0.06,
            fg=(1, 0.8, 0.2, 1),
            align=TextNode.ALeft
        )
        
        # Gear display
        self.gear_text = OnscreenText(
            text="Gear: N",
            pos=(-0.9, 0.7),
            scale=0.06,
            fg=(0.5, 0.8, 1, 1),
            align=TextNode.ALeft
        )
        
        # Instructions
        self.instructions = OnscreenText(
            text="W/S - Throttle/Brake | A/D - Steer | ESC - Exit",
            pos=(0, -0.9),
            scale=0.05,
            fg=(0.8, 0.8, 0.8, 1),
            align=TextNode.ACenter
        )
    
    def update(self, task):
        """Main update loop"""
        dt = globalClock.getDt()
        
        # Update vehicle controls
        self.player_vehicle.set_throttle(self.keys["throttle"])
        self.player_vehicle.set_brake(self.keys["brake"])
        self.player_vehicle.set_steering(self.keys["steering"])
        self.player_vehicle.set_handbrake(self.keys["handbrake"])
        
        # Update vehicle physics
        self.player_vehicle.update(dt)
        self.world.update(dt)
        
        # Get vehicle state
        state = self.player_vehicle.get_state()
        pose = self.player_vehicle.get_pose_state()
        trans = self.player_vehicle.get_transmission_state()
        wheels = self.player_vehicle.get_wheels_state()
        
        # Update visual position
        self._update_visuals(state, pose, wheels)
        
        # Update camera
        self._update_camera(state)
        
        # Update UI
        self._update_ui(state, trans)
        
        return Task.cont
    
    def _update_visuals(self, state, pose, wheels):
        """Update vehicle visual representation"""
        # Update body position and rotation
        pos = state.position
        self.vehicle_node.setPos(pos.x, pos.y, pos.z + pose.bounce)
        self.vehicle_node.setHpr(state.heading, pose.pitch, pose.roll)
        
        # Update wheels
        for i, wheel_node in enumerate(self.wheel_nodes):
            if i < len(wheels.wheels):
                wheel_state = wheels.wheels[i]
                
                # Get suspension offset
                suspension = self.player_vehicle.get_wheel_suspension_state(i)
                z_offset = suspension.wheel_offset.z if suspension else 0
                
                # Get wheel position
                pos = wheel_state.local_position
                wheel_node.setPos(pos.x, pos.y, pos.z + z_offset)
                
                # Set rotation
                wheel_node.setHpr(wheel_state.steering_angle, 0, wheel_state.rotation_angle)
    
    def _update_camera(self, state):
        """Update camera to follow vehicle"""
        # Calculate desired camera position
        heading_rad = math.radians(state.heading)
        cam_x = state.position.x - math.sin(heading_rad) * self.camera_distance
        cam_y = state.position.y + math.cos(heading_rad) * self.camera_distance
        cam_z = state.position.z + self.camera_height
        
        # Smooth camera movement
        current_pos = self.camera.getPos()
        new_x = current_pos[0] + (cam_x - current_pos[0]) * self.camera_smooth
        new_y = current_pos[1] + (cam_y - current_pos[1]) * self.camera_smooth
        new_z = current_pos[2] + (cam_z - current_pos[2]) * self.camera_smooth
        
        self.camera.setPos(new_x, new_y, new_z)
        self.camera.lookAt(state.position.x, state.position.y, state.position.z + 1)
    
    def _update_ui(self, state, trans):
        """Update UI elements"""
        self.speed_text.setText(f"Speed: {int(state.speed)} km/h")
        self.rpm_text.setText(f"RPM: {int(state.engine_rpm)}")
        
        # Gear display
        gear = trans.current_gear
        if gear == 0:
            gear_str = "N"
        elif gear < 0:
            gear_str = "R"
        else:
            gear_str = str(gear)
        self.gear_text.setText(f"Gear: {gear_str}")
    
    def exit_game(self):
        """Exit the game"""
        print("Exiting game...")
        for name, system in self.player_vehicle._systems.items():
            system.shutdown()
        sys.exit()

if __name__ == "__main__":
    game = RacingGame()
    game.run()
