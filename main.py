"""
Panda3D Racing Game - Main Entry Point
With enhanced procedural terrain and shadows
"""
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import *
import math
import sys
import random

# Import our vehicle systems
from src.business.vehicle_entity import VehicleEntity
from src.business.game_world import GameWorld
from src.systems.physics_system import PhysicsSystem
from src.systems.suspension_system import SuspensionSystem
from src.systems.pose_system import PoseSystem
from src.systems.wheel_system import WheelSystem
from src.systems.tire_system import TireSystem
from src.systems.transmission_system import TransmissionSystem

# Import terrain system
from src.world.terrain_runtime import RuntimeTerrain, TerrainConfig

class RacingGame(ShowBase):
    """Main game class with enhanced terrain and shadows"""
    
    def __init__(self):
        super().__init__()

        # Scale knob: increasing this makes the playable world larger.
        # For racing games, the default 200x200 terrain is too small.
        self.terrain_world_scale = 10.0
        
        # Window setup
        self.setBackgroundColor(0.4, 0.65, 0.85)
        
        # Setup display
        props = WindowProperties()
        props.setSize(1280, 720)
        props.setTitle("Panda3D Racing Game - Enhanced Terrain")
        self.win.requestProperties(props)
        
        # Enable advanced rendering
        self.render.setShaderAuto()

        # Let Panda3D pick a reasonable AA mode when available.
        self.render.setAntialias(AntialiasAttrib.MAuto)
        
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
        
        # Setup scene
        self.setup_lights()
        self.setup_terrain()
        self.setup_environment()
        self.create_vehicle_visuals()
        self.setup_camera()
        self.setup_inputs()
        self.setup_ui()
        
        # Add update task
        self.taskMgr.add(self.update, "UpdateTask")
        
        # Initialize camera to follow vehicle
        self._init_camera_position()
        
        print("Racing Game Initialized!")
        print("Controls: W/S - Throttle/Brake, A/D - Steering, ESC - Exit")
        print("Terrain: Enhanced with grass/dirt/rock/snow blending")
    
    def _create_vehicle_config(self):
        """Create vehicle configuration"""
        return {
            'name': 'Sports Car',
            'position': [0, 0, 12.0],
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
        """Setup lighting with shadows"""
        # Ambient light (sky color)
        self.amblight = AmbientLight("ambient_light")
        # Keep ambient lower so shadows remain visible.
        self.amblight.setColor((0.22, 0.24, 0.27, 1))
        self.ambient_np = self.render.attachNewNode(self.amblight)
        self.render.setLight(self.ambient_np)
        
        # Main directional light (sun) with shadows
        self.sun_light = DirectionalLight("sun")
        self.sun_light.setColor((1.0, 0.96, 0.8, 1.0))  # Warm sun
        self.sun_np = self.render.attachNewNode(self.sun_light)

        # IMPORTANT: for shadow mapping, the light's NodePath transform acts as the
        # shadow camera. Using setDirection() alone does not orient the camera.
        # So we position + orient the NodePath instead.
        self.sun_np.setPos(60, -60, 120)
        self.sun_np.lookAt(0, 0, 0)
        self.render.setLight(self.sun_np)
        
        # Setup shadow mapping
        # Use a higher-res shadow map for crisper vehicle shadows.
        self.sun_light.setShadowCaster(True, 2048, 2048)
        # Cover the whole terrain with the orthographic shadow camera.
        shadow_scale = float(self.terrain_world_scale)
        self.sun_light.getLens().setFilmSize(260 * shadow_scale, 260 * shadow_scale)
        self.sun_light.getLens().setNearFar(10, 400 * shadow_scale)
        
        # Fill light (warmer)
        fill_light = AmbientLight("fill_light")
        fill_light.setColor((0.12, 0.13, 0.15, 1))
        fill_np = self.render.attachNewNode(fill_light)
        self.render.setLight(fill_np)
        
        # Rim light for better definition
        rim_light = DirectionalLight("rim_light")
        rim_light.setColor((0.3, 0.35, 0.4, 0.6))
        rim_light.setDirection((0.3, 0.5, -0.3))
        rim_np = self.render.attachNewNode(rim_light)
        self.render.setLight(rim_np)

        # Re-apply auto shader after lights are configured (ensures shadow variant).
        self.render.setShaderAuto()
        
        print("Lighting: Multi-light setup with shadows enabled")
    
    def setup_terrain(self):
        """Setup enhanced procedural terrain"""
        # Create terrain with enhanced parameters
        scale = float(self.terrain_world_scale)
        terrain_config = TerrainConfig(
           heightmap_path="res/terrain/smoke_flat_hd_regen_cli.npy",
            use_procedural_texture=True,
            # Make the terrain 10x larger without changing the heightmap.
            # This keeps sampling logic stable while enlarging the playable area.
            world_size_x=200.0 * scale,
            world_size_y=200.0 * scale,
            height_scale=20.0,  # More height variation
            mesh_step=1,
            # When scaling the world up, keep macro noise features readable.
            noise_scale=0.08 / scale,
            noise_octaves=5,    # More detail layers
            grass_color=(0.08, 0.38, 0.08),      # Deeper green
            dirt_color=(0.58, 0.42, 0.25),       # More saturated brown
            rock_color=(0.68, 0.62, 0.55),       # Lighter, more contrast
            height_rock_threshold=0.4,           # More rock at lower heights
            slope_rock_threshold=0.3,            # More sensitive to slope

            # Improve perceived sharpness: stable world-space UVs + detail texture.
            uv_mode="world",
            uv_world_scale=0.06,
            enable_detail_texture=True,
            detail_texture_size=256,
            detail_texture_strength=0.22,
            # Finer ground micro-texture.
            detail_uv_scale=18.0,
            detail_lod_bias=-0.7,
            detail_anisotropy=16,
        )
        
        # Create terrain
        self.terrain = RuntimeTerrain(self.loader, terrain_config)
        self.terrain_node = self.terrain.build(self.render)
        self.terrain_node.setPos(0, 0, 0)
        self.terrain_node.setTwoSided(False)
        
        # Enable shadows and shaders on terrain
        self.terrain_node.setShaderAuto()
        
        print(f"Terrain: {self.terrain.map_width}x{self.terrain.map_height} with enhanced colors")
    
    def setup_environment(self):
        """Add environment details"""
        # Add fog for depth
        self.myfog = Fog("linear_fog")
        self.render.setFog(self.myfog)
        fog = self.myfog
        fog.setColor(0.6, 0.72, 0.85)
        # Scale fog with the terrain so the scene doesn't look washed out.
        scale = float(self.terrain_world_scale)
        fog.setLinearRange(100 * scale, 500 * scale)
        
        # Add some decorative elements (trees/rocks)
        self.add_environment_props()
    
    def add_environment_props(self):
        """Add trees and rocks to the scene"""
        self.env_props = []

        scale = float(self.terrain_world_scale)
        
        # Add random rocks
        for i in range(40):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(30 * scale, 90 * scale)
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            
            # Skip center area (track)
            if abs(x) < 15 and abs(y) < 100:
                continue
            
            # Create rock
            rock = self.loader.loadModel("box")
            scale = random.uniform(1.5, 4.0)
            rock.setScale(scale, scale, scale * 0.6)
            rock.setPos(x, y, 0.5)
            
            # Color rocks grey-brown
            rock_color = (random.uniform(0.55, 0.65), 
                         random.uniform(0.52, 0.60), 
                         random.uniform(0.48, 0.55), 1)
            rock.setColor(rock_color)
            rock.setTwoSided(True)
            rock.reparentTo(self.render)
            self.env_props.append(rock)
        
        # Add random trees (simplified as cones)
        for i in range(30):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(40 * scale, 95 * scale)
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            
            # Skip center area
            if abs(x) < 18 and abs(y) < 100:
                continue
            
            # Tree trunk
            trunk = self.loader.loadModel("box")
            trunk.setScale(0.8, 0.8, 3.0)
            trunk.setPos(x, y, 1.5)
            trunk.setColor(0.35, 0.25, 0.15, 1)
            trunk.setTwoSided(True)
            trunk.reparentTo(self.render)
            self.env_props.append(trunk)
            
            # Tree foliage (cone approximation with box)
            foliage = self.loader.loadModel("box")
            foliage.setScale(3.5, 3.5, 4.0)
            foliage.setPos(x, y, 5.0)
            foliage.setColor(0.12, 0.35, 0.15, 1)
            foliage.setTwoSided(True)
            foliage.reparentTo(self.render)
            self.env_props.append(foliage)
        
        print(f"Environment: Added {len(self.env_props)} props (rocks and trees)")

    def _attach_centered_box(self, parent, name: str, size_xyz, pos_xyz, color_rgba, hpr_xyz=None):
        """Attach a unit box centered on the parent node.

        Panda3D's built-in `box` model spans [0..1] on each axis (origin is a corner).
        We offset it by (-0.5, -0.5, -0.5) under a scaled node so the parent's origin
        becomes the geometric center.

        Args:
            parent: NodePath to attach under.
            name: Node name.
            size_xyz: (sx, sy, sz) full size in local units.
            pos_xyz: (x, y, z) local position of the box center.
            color_rgba: (r, g, b, a).
            hpr_xyz: optional (h, p, r) in degrees.
        """
        node = parent.attachNewNode(name)
        node.setPos(float(pos_xyz[0]), float(pos_xyz[1]), float(pos_xyz[2]))
        if hpr_xyz is not None:
            node.setHpr(float(hpr_xyz[0]), float(hpr_xyz[1]), float(hpr_xyz[2]))
        node.setScale(float(size_xyz[0]), float(size_xyz[1]), float(size_xyz[2]))

        geom = self.loader.loadModel("box")
        geom.reparentTo(node)
        geom.setPos(-0.5, -0.5, -0.5)
        geom.setColor(float(color_rgba[0]), float(color_rgba[1]), float(color_rgba[2]), float(color_rgba[3]))
        geom.setTwoSided(True)
        return node

    def _attach_centered_cylinder(
        self,
        parent,
        name: str,
        radius: float,
        length: float,
        pos_xyz,
        color_rgba,
        segments: int = 24,
        cap: bool = True,
        hpr_xyz=None,
    ):
        """Attach a simple cylinder centered on the parent.

        We generate the mesh procedurally because a built-in `cylinder` model is
        not guaranteed to exist on the Panda3D model path.

        The cylinder axis is the X axis. So it works well for wheels where rolling
        is a pitch rotation (P) around X.
        """

        radius = float(radius)
        length = float(length)
        segments = int(max(8, segments))
        if radius <= 0.0 or length <= 0.0:
            return None

        node = parent.attachNewNode(name)
        node.setPos(float(pos_xyz[0]), float(pos_xyz[1]), float(pos_xyz[2]))
        if hpr_xyz is not None:
            node.setHpr(float(hpr_xyz[0]), float(hpr_xyz[1]), float(hpr_xyz[2]))

        fmt = GeomVertexFormat.getV3n3()
        vdata = GeomVertexData(f"{name}_vdata", fmt, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, "vertex")
        normal = GeomVertexWriter(vdata, "normal")
        prim = GeomTriangles(Geom.UHStatic)

        idx = 0

        def add_v(vx, vy, vz, nx, ny, nz):
            nonlocal idx
            vertex.addData3(float(vx), float(vy), float(vz))
            normal.addData3(float(nx), float(ny), float(nz))
            i = idx
            idx += 1
            return i

        half = length * 0.5
        two_pi = math.pi * 2.0

        # Side surface
        for i in range(segments):
            a0 = two_pi * (i / segments)
            a1 = two_pi * ((i + 1) / segments)

            cos0, sin0 = math.cos(a0), math.sin(a0)
            cos1, sin1 = math.cos(a1), math.sin(a1)

            y0, z0 = cos0 * radius, sin0 * radius
            y1, z1 = cos1 * radius, sin1 * radius

            # Quad vertices
            v0 = (-half, y0, z0)
            v1 = (half, y0, z0)
            v2 = (half, y1, z1)
            v3 = (-half, y1, z1)

            # Outward normals (no X component on the side).
            n0 = (0.0, cos0, sin0)
            n1 = (0.0, cos1, sin1)

            # Two triangles: (v0, v2, v1) and (v0, v3, v2)
            i0 = add_v(*v0, *n0)
            i1 = add_v(*v2, *n1)
            i2 = add_v(*v1, *n0)
            prim.addVertices(i0, i1, i2)

            i3 = add_v(*v0, *n0)
            i4 = add_v(*v3, *n1)
            i5 = add_v(*v2, *n1)
            prim.addVertices(i3, i4, i5)

        # Caps
        if cap:
            for i in range(segments):
                a0 = two_pi * (i / segments)
                a1 = two_pi * ((i + 1) / segments)
                cos0, sin0 = math.cos(a0), math.sin(a0)
                cos1, sin1 = math.cos(a1), math.sin(a1)

                y0, z0 = cos0 * radius, sin0 * radius
                y1, z1 = cos1 * radius, sin1 * radius

                # Left cap faces -X: (center, rim1, rim0)
                c0 = add_v(-half, 0.0, 0.0, -1.0, 0.0, 0.0)
                r1 = add_v(-half, y1, z1, -1.0, 0.0, 0.0)
                r0 = add_v(-half, y0, z0, -1.0, 0.0, 0.0)
                prim.addVertices(c0, r1, r0)

                # Right cap faces +X: (center, rim0, rim1)
                c1 = add_v(half, 0.0, 0.0, 1.0, 0.0, 0.0)
                r0b = add_v(half, y0, z0, 1.0, 0.0, 0.0)
                r1b = add_v(half, y1, z1, 1.0, 0.0, 0.0)
                prim.addVertices(c1, r0b, r1b)

        prim.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(prim)
        geom_node = GeomNode(f"{name}_geom")
        geom_node.addGeom(geom)

        geom_np = node.attachNewNode(geom_node)
        geom_np.setColor(
            float(color_rgba[0]),
            float(color_rgba[1]),
            float(color_rgba[2]),
            float(color_rgba[3]),
        )
        geom_np.setTwoSided(True)
        # Guard against any parent non-uniform scaling.
        geom_np.setAttrib(RescaleNormalAttrib.make(RescaleNormalAttrib.MNormalize))
        return node
   
    def create_vehicle_visuals(self):
        """(Re)build the vehicle visual hierarchy.

        The previous implementation suffered from a common Panda3D gotcha:
        the built-in `box` model is not centered (it spans 0..1), so scaling it
        produces meshes that are offset from the expected origin.

        Here we build every part using `_attach_centered_box()` so the vehicle local
        origin matches the wheel config coordinates.
        """
        # If we ever rebuild visuals in a running session, clean up old nodes.
        if hasattr(self, "vehicle_node") and self.vehicle_node is not None:
            try:
                self.vehicle_node.removeNode()
            except Exception:
                pass

        self.vehicle_node = self.render.attachNewNode("vehicle")
        # A separate node lets us change pose without touching world-space placement.
        self.chassis_node = self.vehicle_node.attachNewNode("chassis")
        self.body_node = self.chassis_node.attachNewNode("body")

        # Wheel configs drive both visuals and ground offset.
        wheel_cfgs = list(self.vehicle_config.get("wheels", []))
        if not wheel_cfgs:
            wheel_cfgs = [
                {"position": [-0.9, 1.3, -0.35], "radius": 0.35, "can_steer": True},
                {"position": [0.9, 1.3, -0.35], "radius": 0.35, "can_steer": True},
                {"position": [-0.9, -1.3, -0.35], "radius": 0.35, "can_steer": False},
                {"position": [0.9, -1.3, -0.35], "radius": 0.35, "can_steer": False},
            ]

        # Derive key dimensions.
        pose_cfg = self.vehicle_config.get("pose", {}) if isinstance(self.vehicle_config, dict) else {}
        track_width = float(pose_cfg.get("track_width", 1.8))
        wheelbase = float(pose_cfg.get("wheelbase", 2.6))

        avg_radius = 0.35
        if wheel_cfgs:
            radii = [float(w.get("radius", 0.35)) for w in wheel_cfgs]
            avg_radius = sum(radii) / float(len(radii))
            avg_radius = max(0.1, min(1.0, avg_radius))

        body_width = track_width * 0.9
        body_length = wheelbase * 1.35
        body_height = max(0.35, avg_radius * 1.2)

        # Ground offset: align the lowest wheel bottom to z=0 in vehicle-local space.
        min_bottom = None
        for w in wheel_cfgs:
            pos = w.get("position", [0.0, 0.0, 0.0])
            if not isinstance(pos, (list, tuple)) or len(pos) < 3:
                continue
            r = float(w.get("radius", 0.35))
            bottom = float(pos[2]) - r
            if min_bottom is None or bottom < min_bottom:
                min_bottom = bottom
        self.vehicle_ground_offset = -float(min_bottom) if min_bottom is not None else 0.55

        # Body parts (all centered boxes).
        self._attach_centered_box(
            self.body_node,
            "chassis",
            (body_width, body_length, body_height),
            (0.0, 0.0, body_height * 0.5),
            (0.85, 0.12, 0.12, 1.0),
        )

        cabin_h = body_height * 0.75
        self._attach_centered_box(
            self.body_node,
            "cabin",
            (body_width * 0.72, body_length * 0.38, cabin_h),
            (0.0, -body_length * 0.12, body_height + cabin_h * 0.5),
            (0.15, 0.18, 0.22, 1.0),
        )

        self._attach_centered_box(
            self.body_node,
            "hood",
            (body_width * 0.85, body_length * 0.28, body_height * 0.25),
            (0.0, body_length * 0.32, body_height + body_height * 0.12),
            (0.85, 0.12, 0.12, 1.0),
        )

        self._attach_centered_box(
            self.body_node,
            "trunk",
            (body_width * 0.85, body_length * 0.22, body_height * 0.25),
            (0.0, -body_length * 0.34, body_height + body_height * 0.12),
            (0.85, 0.12, 0.12, 1.0),
        )

        self._attach_centered_box(
            self.body_node,
            "spoiler",
            (body_width * 0.9, body_length * 0.06, body_height * 0.12),
            (0.0, -body_length * 0.48, body_height + body_height * 0.55),
            (0.1, 0.1, 0.12, 1.0),
        )

        # Wheels (centered boxes under a steering + spin rig).
        self.wheel_visuals = []
        for i, w in enumerate(wheel_cfgs):
            pos = w.get("position", [0.0, 0.0, 0.0])
            if not isinstance(pos, (list, tuple)) or len(pos) < 3:
                pos = [0.0, 0.0, 0.0]

            radius = float(w.get("radius", 0.35))
            radius = max(0.1, min(1.0, radius))
            wheel_width = max(0.18, radius * 0.55)
            diameter = radius * 2.0

            pivot = self.chassis_node.attachNewNode(f"wheel_pivot_{i}")
            pivot.setPos(float(pos[0]), float(pos[1]), 0.0)
            spin = pivot.attachNewNode(f"wheel_spin_{i}")

            # Tire (cylinder)
            self._attach_centered_cylinder(
                spin,
                f"wheel_tire_{i}",
                radius=radius,
                length=wheel_width,
                pos_xyz=(0.0, 0.0, 0.0),
                color_rgba=(0.1, 0.1, 0.12, 1.0),
                segments=28,
                cap=True,
            )

            # Hub (keep as a box so rotation is visible)
            self._attach_centered_box(
                spin,
                f"wheel_hub_{i}",
                (wheel_width * 0.6, diameter * 0.55, diameter * 0.55),
                (0.0, 0.0, 0.0),
                (0.75, 0.75, 0.78, 1.0),
            )

            self.wheel_visuals.append(
                {
                    "pivot": pivot,
                    "spin": spin,
                    "radius": radius,
                    "base_z": float(pos[2]),
                }
            )

        # Shading + lighting.
        self.vehicle_node.setShaderAuto()
        self.vehicle_node.setLightOff()
        self.vehicle_node.setLight(self.sun_np)
        self.vehicle_node.setLight(self.ambient_np)

    def setup_camera(self):
        """Setup camera"""
        self.camera_distance = 15.0
        self.camera_height = 8.0
        self.camera_smooth = 0.06
        self.camera_smooth_catchup = 0.22
        self._camera_catchup_frames = 0

        # Camera control mode: True = manual debug camera, False = auto-follow
        self.camera_manual = False

        # Always disable Panda3D's built-in mouse->camera control. We implement
        # manual camera controls ourselves so toggling does not snap/jump.
        self.disableMouse()

        # Manual debug camera state (orbit around a target point).
        self._debug_cam_target = Vec3(0.0, 0.0, 0.0)
        self._debug_cam_distance = float(self.camera_distance)
        self._debug_cam_yaw = 0.0
        self._debug_cam_pitch = 0.0
        self._debug_cam_orbiting = False
        self._debug_cam_panning = False
        self._debug_cam_last_mouse = None
        # Mouse coordinates are in [-1..1]. These are tuned for trackpad use.
        self._debug_cam_rotate_speed = 1.6  # radians per normalized unit
        self._debug_cam_pan_speed = 0.75    # scaled by distance
        self._debug_cam_zoom_factor = 0.9

    def _get_mouse_xy(self):
        if self.mouseWatcherNode and self.mouseWatcherNode.hasMouse():
            m = self.mouseWatcherNode.getMouse()
            return (float(m.getX()), float(m.getY()))
        return None

    def _sync_debug_camera_from_view(self):
        """Derive orbit camera params from the current follow camera view.

        This avoids any camera movement when switching into manual mode.
        """

        state = self.player_vehicle.get_state()
        target = Vec3(state.position.x, state.position.y, state.position.z + 2.0)

        cam_pos = self.camera.getPos(self.render)
        offset = cam_pos - target
        dist = offset.length()
        if dist < 1e-3:
            dist = float(self.camera_distance)
            offset = Vec3(0.0, -dist, 0.0)

        horiz = math.sqrt(float(offset.x * offset.x + offset.y * offset.y))
        yaw = math.atan2(float(-offset.x), float(-offset.y))
        pitch = math.atan2(float(offset.z), float(horiz))

        self._debug_cam_target = target
        self._debug_cam_distance = float(dist)
        self._debug_cam_yaw = float(yaw)
        self._debug_cam_pitch = float(pitch)

    def _apply_debug_camera(self):
        dist = max(2.0, float(self._debug_cam_distance))
        pitch = max(-1.4, min(1.4, float(self._debug_cam_pitch)))
        self._debug_cam_distance = dist
        self._debug_cam_pitch = pitch

        cos_pitch = math.cos(pitch)
        sin_pitch = math.sin(pitch)
        sin_yaw = math.sin(self._debug_cam_yaw)
        cos_yaw = math.cos(self._debug_cam_yaw)

        offset = Vec3(
            -sin_yaw * cos_pitch * dist,
            -cos_yaw * cos_pitch * dist,
            sin_pitch * dist,
        )
        cam_pos = self._debug_cam_target + offset
        self.camera.setPos(cam_pos)
        self.camera.lookAt(self._debug_cam_target)

    def _debug_cam_begin_orbit(self):
        if not self.camera_manual:
            return
        self._debug_cam_orbiting = True
        self._debug_cam_panning = False
        self._debug_cam_last_mouse = self._get_mouse_xy()

    def _debug_cam_end_orbit(self):
        self._debug_cam_orbiting = False
        self._debug_cam_last_mouse = None

    def _debug_cam_begin_pan(self):
        if not self.camera_manual:
            return
        self._debug_cam_panning = True
        self._debug_cam_orbiting = False
        self._debug_cam_last_mouse = self._get_mouse_xy()

    def _debug_cam_end_pan(self):
        self._debug_cam_panning = False
        self._debug_cam_last_mouse = None

    def _debug_cam_zoom(self, direction: int):
        if not self.camera_manual:
            return
        if direction > 0:
            self._debug_cam_distance *= float(self._debug_cam_zoom_factor)
        else:
            self._debug_cam_distance /= float(self._debug_cam_zoom_factor)
        self._apply_debug_camera()

    def _update_debug_camera(self):
        if not (self._debug_cam_orbiting or self._debug_cam_panning):
            return

        xy = self._get_mouse_xy()
        if xy is None:
            self._debug_cam_last_mouse = None
            return

        if self._debug_cam_last_mouse is None:
            self._debug_cam_last_mouse = xy
            return

        last_x, last_y = self._debug_cam_last_mouse
        mx, my = xy
        dx = mx - last_x
        dy = my - last_y
        self._debug_cam_last_mouse = xy

        if self._debug_cam_orbiting:
            self._debug_cam_yaw -= dx * float(self._debug_cam_rotate_speed)
            self._debug_cam_pitch += dy * float(self._debug_cam_rotate_speed)
            self._apply_debug_camera()
            return

        # Pan target in the camera view plane.
        quat = self.camera.getQuat(self.render)
        right = quat.getRight()
        up = quat.getUp()
        scale = float(self._debug_cam_distance) * float(self._debug_cam_pan_speed)
        self._debug_cam_target -= right * (dx * scale)
        self._debug_cam_target += up * (dy * scale)
        self._apply_debug_camera()
    
    def _init_camera_position(self):
        """Initialize camera position to follow vehicle at start"""
        state = self.player_vehicle.get_state()
        heading_rad = math.radians(state.heading)
        cam_x = state.position.x - math.sin(heading_rad) * self.camera_distance
        cam_y = state.position.y - math.cos(heading_rad) * self.camera_distance
        cam_z = state.position.z + self.camera_height
        self.camera.setPos(cam_x, cam_y, cam_z)
        target_z = state.position.z + 2.0
        self.camera.lookAt(state.position.x, state.position.y, target_z)
    
    def setup_inputs(self):
        """Setup keyboard inputs"""
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
        
        # Camera mode toggle
        self.accept("c", self.toggle_camera_mode)
        self.accept("C", self.toggle_camera_mode)

        # Manual camera controls (only active in manual mode)
        self.accept("mouse1", self._debug_cam_begin_orbit)
        self.accept("mouse1-up", self._debug_cam_end_orbit)
        self.accept("mouse3", self._debug_cam_begin_pan)
        self.accept("mouse3-up", self._debug_cam_end_pan)
        self.accept("wheel_up", self._debug_cam_zoom, [1])
        self.accept("wheel_down", self._debug_cam_zoom, [-1])
    
    def set_key(self, key, value):
        """Handle key input"""
        self.keys[key] = value
    
    def toggle_camera_mode(self):
        """Toggle between manual camera control and auto-follow mode"""
        self.camera_manual = not self.camera_manual
        
        if self.camera_manual:
            # Switch to manual mode: do not touch camera transform here.
            # We sync internal orbit params from the current view so the first
            # manual interaction is smooth and there is no snap on toggle.
            self._sync_debug_camera_from_view()
            self._debug_cam_orbiting = False
            self._debug_cam_panning = False
            self._debug_cam_last_mouse = None
            print("Camera: MANUAL mode")
        else:
            # Switch to auto-follow mode: keep current view at the toggle moment.
            # Auto-follow update will smoothly converge to follow position.
            self._debug_cam_orbiting = False
            self._debug_cam_panning = False
            self._debug_cam_last_mouse = None
            self._camera_catchup_frames = 30
            print("Camera: AUTO-FOLLOW mode")
    
    def setup_ui(self):
        """Setup UI"""
        # Speed display
        self.speed_text = OnscreenText(
            text="Speed: 0 km/h",
            pos=(-0.9, 0.9),
            scale=0.075,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            shadow=(0, 0, 0, 0.8)
        )
        
        # RPM display
        self.rpm_text = OnscreenText(
            text="RPM: 0",
            pos=(-0.9, 0.8),
            scale=0.065,
            fg=(1, 0.88, 0.25, 1),
            align=TextNode.ALeft,
            shadow=(0, 0, 0, 0.8)
        )
        
        # Gear display
        self.gear_text = OnscreenText(
            text="Gear: N",
            pos=(-0.9, 0.7),
            scale=0.065,
            fg=(0.55, 0.88, 1, 1),
            align=TextNode.ALeft,
            shadow=(0, 0, 0, 0.8)
        )
        
        # Terrain info
        self.terrain_text = OnscreenText(
            text="Terrain: Enhanced Procedural",
            pos=(0.9, 0.9),
            scale=0.05,
            fg=(0.65, 0.65, 0.65, 1),
            align=TextNode.ARight,
            shadow=(0, 0, 0, 0.8)
        )
        
        # Instructions
        self.instructions = OnscreenText(
            text="W/S - Throttle/Brake | A/D - Steer | Space - Handbrake | ESC - Exit",
            pos=(0, -0.92),
            scale=0.045,
            fg=(0.92, 0.92, 0.92, 1),
            align=TextNode.ACenter,
            shadow=(0, 0, 0, 0.8)
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
        
        # Sample terrain height at vehicle position
        terrain_height = self.terrain.sample_height(state.position.x, state.position.y)
        terrain_normal = self.terrain.sample_normal(state.position.x, state.position.y)
        
        # Update visual position
        self._update_visuals(state, pose, wheels, terrain_height, terrain_normal)
        
        # Update camera
        self._update_camera(state, terrain_height)

        # Manual debug camera updates (orbit/pan while dragging).
        if self.camera_manual:
            self._update_debug_camera()
        
        # Update UI
        self._update_ui(state, trans)
        
        return Task.cont
    
    def _update_visuals(self, state, pose, wheels, terrain_height, terrain_normal):
        """更新车辆可视化
        
        坐标系统：
        - vehicle_node 的位置 = 车辆质心在地形上的位置
        - wheel_pivot 的位置 = 轮子相对车身的局部坐标（X: 左右, Y: 前后）
        - wheel_spin 的 Z = 悬挂压缩偏移
        """
        pos = state.position
        # Place the vehicle so wheel bottoms do not penetrate the terrain.
        #
        # We start from a baseline offset (based on wheel config) and then compute
        # an additional required lift from per-wheel terrain samples + suspension
        # offsets. This keeps the visuals from clipping into the ground even though
        # the simulation currently does not solve vertical contact.
        ground_offset = float(getattr(self, "vehicle_ground_offset", 0.55))
        z_base = float(terrain_height) + ground_offset

        z_required = z_base
        try:
            req = None
            for i, vis in enumerate(getattr(self, "wheel_visuals", [])):
                if i >= len(wheels.wheels):
                    continue
                wheel_state = wheels.wheels[i]

                base_z = float(vis.get("base_z", 0.0))
                radius = float(vis.get("radius", 0.35))

                suspension = self.player_vehicle.get_wheel_suspension_state(i)
                z_offset = float(suspension.wheel_offset.z) if suspension else 0.0

                # Sample terrain height under each wheel (XY only).
                wx = float(wheel_state.position.x)
                wy = float(wheel_state.position.y)
                th = float(terrain_height)
                if hasattr(self, "terrain") and self.terrain is not None:
                    try:
                        th = float(self.terrain.sample_height(wx, wy))
                    except Exception:
                        th = float(terrain_height)

                bottom_local = base_z + z_offset - radius
                required_i = th - bottom_local
                req = required_i if req is None else max(req, required_i)

            if req is not None:
                z_required = max(z_required, float(req))
        except Exception:
            z_required = z_base

        # Small clearance avoids visible z-fighting/near-zero penetration.
        z_required += 0.02

        # Apply bounce, but never allow it to push the wheels into the terrain.
        z = z_required + float(pose.bounce)
        if z < z_required:
            z = z_required
        self.vehicle_node.setPos(pos.x, pos.y, z)

        # The simulation uses a math-style heading where +angle turns toward +X.
        # Panda3D's +H turns toward -X, so we negate to keep visuals aligned.
        self.vehicle_node.setH(-state.heading)

        # Pitch/roll on the chassis node so wheel local coordinates remain stable.
        if hasattr(self, "chassis_node") and self.chassis_node is not None:
            self.chassis_node.setHpr(0.0, pose.pitch * 0.5, pose.roll * 0.5)
        
        # 更新车轮
        for i, vis in enumerate(getattr(self, "wheel_visuals", [])):
            if i >= len(wheels.wheels):
                continue
            
            wheel_state = wheels.wheels[i]
            pivot = vis.get("pivot")
            spin = vis.get("spin")
            base_z = vis.get("base_z", -0.35)
            
            if pivot is None or spin is None:
                continue
            
            # Steering angle (yaw around Z) on the pivot.
            pivot.setH(-wheel_state.steering_angle)
            
            # 悬挂压缩（轮子相对车身的上下移动）
            suspension = self.player_vehicle.get_wheel_suspension_state(i)
            z_offset = suspension.wheel_offset.z if suspension else 0.0
            spin.setZ(base_z + z_offset)
            
            # 轮子滚动（绕X轴的pitch旋转）
            spin.setP(wheel_state.rotation_angle)

    def _update_camera(self, state, terrain_height):
        """Update camera"""
        # Only update camera in auto-follow mode
        if self.camera_manual:
            return

        # After leaving manual mode, converge faster for a short period so it
        # feels responsive without snapping.
        smooth = self.camera_smooth
        if self._camera_catchup_frames > 0:
            smooth = self.camera_smooth_catchup
            self._camera_catchup_frames -= 1
            
        heading_rad = math.radians(state.heading)
        # Panda3D coordinate system: X right, Y forward (into screen), Z up
        # Camera should be behind vehicle (negative Y offset in vehicle local space)
        cam_x = state.position.x - math.sin(heading_rad) * self.camera_distance
        cam_y = state.position.y - math.cos(heading_rad) * self.camera_distance
        cam_z = state.position.z + self.camera_height
        
        current_pos = self.camera.getPos()
        new_x = current_pos[0] + (cam_x - current_pos[0]) * smooth
        new_y = current_pos[1] + (cam_y - current_pos[1]) * smooth
        new_z = current_pos[2] + (cam_z - current_pos[2]) * smooth
        
        self.camera.setPos(new_x, new_y, new_z)
        # Look at a point slightly above vehicle center
        target_z = state.position.z + 2.0
        self.camera.lookAt(state.position.x, state.position.y, target_z)
    
    def _update_ui(self, state, trans):
        """Update UI"""
        speed_kmh = state.speed * 3.6
        self.speed_text.setText(f"Speed: {int(speed_kmh)} km/h")
        self.rpm_text.setText(f"RPM: {int(state.engine_rpm)}")
        
        gear = trans.current_gear
        gear_str = "N" if gear == 0 else ("R" if gear < 0 else str(gear))
        self.gear_text.setText(f"Gear: {gear_str}")
    
    def exit_game(self):
        """Exit game"""
        print("Exiting game...")
        for name, system in self.player_vehicle._systems.items():
            system.shutdown()
        sys.exit()

if __name__ == "__main__":
    game = RacingGame()
    game.run()
