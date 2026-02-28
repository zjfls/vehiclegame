"""
Panda3D Racing Game - Main Entry Point
With enhanced procedural terrain and shadows
"""
import argparse
import json
from pathlib import Path

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
from src.systems.terrain_query import TerrainQueryAdapter

# Import terrain system
from src.world.terrain_runtime import RuntimeTerrain, TerrainConfig
from src.world.track_runtime import RuntimeTrack, TrackConfig

PROJECT_ROOT = Path(__file__).resolve().parent

class RacingGame(ShowBase):
    """Main game class with enhanced terrain and shadows"""
    
    def __init__(
        self,
        *,
        vehicle_config_id: str = "",
        map_config_id: str = "",
        resolution: str = "1280x720",
        fullscreen: bool = False,
        enable_shadows: bool = True,
        debug: bool = False,
    ):
        super().__init__()

        # Scale knob: increasing this makes the playable world larger.
        # For racing games, the default 200x200 terrain is too small.
        self.terrain_world_scale = 10.0

        # CLI selections / flags
        self.vehicle_config_id = (vehicle_config_id or "").strip()
        self.map_config_id = (map_config_id or "").strip()
        self.enable_shadows = bool(enable_shadows)
        self.debug_mode = bool(debug)
        self._selected_map = self._load_map_selection(self.map_config_id) if self.map_config_id else None
        
        # Window setup
        self.setBackgroundColor(0.4, 0.65, 0.85)
        
        # Setup display
        props = WindowProperties()
        w, h = self._parse_resolution(resolution, default=(1280, 720))
        props.setSize(int(w), int(h))
        if fullscreen:
            props.setFullscreen(True)
        props.setTitle("Panda3D Racing Game - Enhanced Terrain")
        self.win.requestProperties(props)
        
        # Enable advanced rendering
        self.render.setShaderAuto()

        # Let Panda3D pick a reasonable AA mode when available.
        self.render.setAntialias(AntialiasAttrib.MAuto)
        
        # Initialize game world
        self.world = GameWorld()
        
        # Create vehicle configuration
        self.vehicle_config = self._load_vehicle_config(self.vehicle_config_id) or self._create_vehicle_config()
        
        # Create player vehicle
        self.player_vehicle = VehicleEntity("player", self.vehicle_config)
        
        # Register all systems
        self._register_systems()
        
        # Add to world
        self.world.add_vehicle(self.player_vehicle)
        self.world.set_player_vehicle("player")
        
        # Initialize all systems
        self.player_vehicle.initialize_systems()
        
        # Setup scene
        self.setup_lights()
        self.setup_terrain()
        self.setup_track()
        
        # Connect terrain to vehicle systems
        self.player_vehicle.terrain = TerrainQueryAdapter(self.terrain)
        
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
        if self.map_config_id:
            print(f"Map: {self.map_config_id}")
        if self.vehicle_config_id:
            print(f"Vehicle: {self.vehicle_config_id}")
    
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
        self._sun_shadow_dir = Vec3(-1.0, 1.0, -2.0)
        if self._sun_shadow_dir.length_squared() < 1e-8:
            self._sun_shadow_dir = Vec3(-0.4, 0.4, -0.8)
        self._sun_shadow_dir.normalize()

        shadow_scale = float(self.terrain_world_scale)
        self.shadow_map_resolution = 2048
        self.shadow_focus_size = 22.0 * shadow_scale
        self.shadow_light_distance = 32.0 * shadow_scale
        self.shadow_near = 5.0
        self.shadow_far = self.shadow_light_distance + 40.0 * shadow_scale
        self.shadow_target_height = 2.0
        self.render.setLight(self.sun_np)
        
        # Setup shadow mapping
        # Use a higher-res shadow map for crisper vehicle shadows.
        if bool(getattr(self, "enable_shadows", True)):
            self.sun_light.setShadowCaster(True, int(self.shadow_map_resolution), int(self.shadow_map_resolution))
            self._apply_shadow_focus(Vec3(0.0, 0.0, self.shadow_target_height))
        else:
            self.sun_np.setPos(60, -60, 120)
            self.sun_np.lookAt(0, 0, 0)
        
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
        
        print(f"Lighting: Multi-light setup ({'shadows on' if self.enable_shadows else 'shadows off'})")

    def _apply_shadow_focus(self, target: Vec3) -> None:
        if not bool(getattr(self, "enable_shadows", True)):
            return
        if not hasattr(self, "sun_np") or not hasattr(self, "sun_light"):
            return

        direction = Vec3(getattr(self, "_sun_shadow_dir", Vec3(-1.0, 1.0, -2.0)))
        if direction.length_squared() < 1e-8:
            direction = Vec3(-1.0, 1.0, -2.0)
        direction.normalize()

        focus_size = float(getattr(self, "shadow_focus_size", 220.0))
        shadow_map_resolution = max(1, int(getattr(self, "shadow_map_resolution", 2048)))
        texel_world = focus_size / float(shadow_map_resolution)

        snap_target = Vec3(target)
        if texel_world > 1e-6:
            up_ref = Vec3(0.0, 0.0, 1.0)
            if abs(direction.dot(up_ref)) > 0.98:
                up_ref = Vec3(0.0, 1.0, 0.0)

            right = direction.cross(up_ref)
            if right.length_squared() < 1e-8:
                right = Vec3(1.0, 0.0, 0.0)
            right.normalize()

            up = right.cross(direction)
            if up.length_squared() < 1e-8:
                up = Vec3(0.0, 0.0, 1.0)
            up.normalize()

            right_proj = snap_target.dot(right)
            up_proj = snap_target.dot(up)
            right_snap = round(right_proj / texel_world) * texel_world
            up_snap = round(up_proj / texel_world) * texel_world

            snap_target += right * (right_snap - right_proj)
            snap_target += up * (up_snap - up_proj)

        light_distance = float(getattr(self, "shadow_light_distance", 320.0))
        light_pos = snap_target - direction * light_distance
        self.sun_np.setPos(light_pos)
        self.sun_np.lookAt(snap_target)

        lens = self.sun_light.getLens()
        if lens is not None:
            lens.setFilmSize(focus_size, focus_size)
            near_plane = float(getattr(self, "shadow_near", 5.0))
            far_plane = float(getattr(self, "shadow_far", light_distance + 400.0))
            if far_plane <= near_plane + 1.0:
                far_plane = near_plane + 1.0
            lens.setNearFar(near_plane, far_plane)

    def _update_shadow_focus(self, state) -> None:
        if not bool(getattr(self, "enable_shadows", True)):
            return
        anchor, _ = self._get_camera_follow_anchor(state)
        target = Vec3(float(anchor.x), float(anchor.y), float(anchor.z) + float(getattr(self, "shadow_target_height", 2.0)))
        self._apply_shadow_focus(target)
    
    def setup_terrain(self):
        """Setup enhanced procedural terrain"""
        # Create terrain with enhanced parameters
        scale = float(self.terrain_world_scale)
        heightmap_path = "res/terrain/smoke_flat_hd_regen_cli.npy"
        colors = None
        selected = getattr(self, "_selected_map", None)
        terrain_runtime = selected.get("terrain_runtime") if isinstance(selected, dict) else None
        if isinstance(selected, dict):
            heightmap_path = str(selected.get("heightmap_path") or heightmap_path)
            colors = selected.get("colors")
        mesh_tile_quads = 256
        if isinstance(terrain_runtime, dict):
            try:
                runtime_tile_quads = terrain_runtime.get("mesh_tile_quads")
                if runtime_tile_quads is not None:
                    mesh_tile_quads = max(1, int(runtime_tile_quads))
            except Exception:
                mesh_tile_quads = 256
        terrain_config = TerrainConfig(
            heightmap_path=heightmap_path,
            use_procedural_texture=True,
            # Make the terrain 10x larger without changing the heightmap.
            # This keeps sampling logic stable while enlarging the playable area.
            world_size_x=200.0 * scale,
            world_size_y=200.0 * scale,
            height_scale=20.0,  # More height variation
            mesh_step=1,
            mesh_tile_quads=mesh_tile_quads,
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

        # Apply map color overrides if available.
        try:
            if colors and isinstance(colors, dict):
                proc = colors.get("procedural") if colors.get("mode") == "procedural" else None
                if isinstance(proc, dict):
                    if isinstance(proc.get("grass_color"), (list, tuple)) and len(proc["grass_color"]) >= 3:
                        terrain_config.grass_color = tuple(proc["grass_color"][:3])
                    if isinstance(proc.get("dirt_color"), (list, tuple)) and len(proc["dirt_color"]) >= 3:
                        terrain_config.dirt_color = tuple(proc["dirt_color"][:3])
                    if isinstance(proc.get("rock_color"), (list, tuple)) and len(proc["rock_color"]) >= 3:
                        terrain_config.rock_color = tuple(proc["rock_color"][:3])
                    if proc.get("height_rock_threshold") is not None:
                        terrain_config.height_rock_threshold = float(proc.get("height_rock_threshold", terrain_config.height_rock_threshold))
                    if proc.get("slope_rock_threshold") is not None:
                        terrain_config.slope_rock_threshold = float(proc.get("slope_rock_threshold", terrain_config.slope_rock_threshold))
        except Exception:
            pass
        
        # Always keep RuntimeTerrain for sampling (track projection, props placement),
        # but prefer loading pre-baked mesh/color assets when available.
        self.terrain = RuntimeTerrain(self.loader, terrain_config)
        terrain_node = None
        baked_mesh_rel = terrain_runtime.get("mesh_bam") if isinstance(terrain_runtime, dict) else None

        if baked_mesh_rel:
            try:
                baked_mesh_path = PROJECT_ROOT / str(baked_mesh_rel)
                if baked_mesh_path.exists():
                    terrain_node = self.loader.loadModel(str(baked_mesh_path))
                    terrain_node.reparentTo(self.render)
                    print(f"Terrain: loaded baked mesh {baked_mesh_rel}")
            except Exception as e:
                print(f"Terrain: failed to load baked mesh ({e}), fallback to runtime build")
                terrain_node = None

        if terrain_node is None:
            terrain_node = self.terrain.build(self.render)

        self.terrain_node = terrain_node
        self.terrain_node.setPos(0, 0, 0)
        self.terrain_node.setTwoSided(False)
        self.terrain_node.setShaderAuto()
        
        print(f"Terrain: {self.terrain.map_width}x{self.terrain.map_height} with enhanced colors")

    def setup_track(self):
        """Setup track runtime geometry if a map config is selected."""
        selected = getattr(self, "_selected_map", None)
        if not isinstance(selected, dict):
            return

        track_data = selected.get("track")
        if not isinstance(track_data, dict):
            return

        try:
            track_csv = str(track_data.get("csv_path") or track_data.get("track_csv_path") or "scripts/track_example.csv")
            coord_space = str(track_data.get("coord_space") or "normalized")

            geom = track_data.get("geometry", {}) if isinstance(track_data.get("geometry"), dict) else {}
            visuals = track_data.get("visuals", {}) if isinstance(track_data.get("visuals"), dict) else {}

            def to_rgba(value, default):
                if isinstance(value, (list, tuple)) and len(value) >= 4:
                    return (float(value[0]), float(value[1]), float(value[2]), float(value[3]))
                return default

            track_cfg = TrackConfig(
                track_csv_path=track_csv,
                coord_space=coord_space,
                elevation_offset=float(geom.get("elevation_offset", 0.05)),
                track_width=float(geom.get("track_width", 9.0)),
                border_width=float(geom.get("border_width", 0.8)),
                samples_per_segment=int(geom.get("samples_per_segment", 8)),
                show_centerline=bool(visuals.get("show_centerline", True)),
                track_color=to_rgba(visuals.get("track_color"), TrackConfig.track_color),
                border_color=to_rgba(visuals.get("border_color"), TrackConfig.border_color),
                centerline_color=to_rgba(visuals.get("centerline_color"), TrackConfig.centerline_color),
            )

            self.runtime_track = RuntimeTrack(track_cfg, self.terrain)
            self.track_node = self.runtime_track.build(self.render)

            start_pos, start_heading = self.runtime_track.get_start_pose()
            self._spawn_player_at(start_pos, start_heading)
            print(f"Track: loaded from {track_csv}")
        except Exception as e:
            print(f"Track: failed to load ({e})")

    def _spawn_player_at(self, pos: "Vec3", heading: float) -> None:
        """Place the player vehicle at a given world pose."""
        try:
            state = self.player_vehicle.get_state()
            state.position.x = float(pos.x)
            state.position.y = float(pos.y)
            state.position.z = float(pos.z)
            state.heading = float(heading)
            state.speed = 0.0
        except Exception:
            pass
    
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

        scenery = {}
        selected = getattr(self, "_selected_map", None)
        if isinstance(selected, dict) and isinstance(selected.get("scenery"), dict):
            scenery = selected.get("scenery") or {}

        trees_cfg = scenery.get("trees", {}) if isinstance(scenery.get("trees"), dict) else {}
        rocks_cfg = scenery.get("rocks", {}) if isinstance(scenery.get("rocks"), dict) else {}

        trees_count = int(trees_cfg.get("count", 30))
        rocks_count = int(rocks_cfg.get("count", 40))

        rocks_min_r = float(rocks_cfg.get("min_radius", 30))
        rocks_max_r = float(rocks_cfg.get("max_radius", 90))
        trees_min_r = float(trees_cfg.get("min_radius", 40))
        trees_max_r = float(trees_cfg.get("max_radius", 95))

        rocks_excl = rocks_cfg.get("exclude_center", {})
        trees_excl = trees_cfg.get("exclude_center", {})
        if not isinstance(rocks_excl, dict):
            rocks_excl = {}
        if not isinstance(trees_excl, dict):
            trees_excl = {}

        rocks_excl_w = float(rocks_excl.get("width", 15))
        rocks_excl_l = float(rocks_excl.get("length", 100))
        trees_excl_w = float(trees_excl.get("width", 18))
        trees_excl_l = float(trees_excl.get("length", 100))

        rocks_size = rocks_cfg.get("size_range", [1.5, 4.0])
        if not isinstance(rocks_size, (list, tuple)) or len(rocks_size) < 2:
            rocks_size = [1.5, 4.0]
        rock_size_min = float(rocks_size[0])
        rock_size_max = float(rocks_size[1])
        
        # Add random rocks
        for i in range(max(0, rocks_count)):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(rocks_min_r * scale, rocks_max_r * scale)
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            
            # Skip center area (track)
            if abs(x) < rocks_excl_w and abs(y) < rocks_excl_l:
                continue
            
            # Create rock
            rock = self.loader.loadModel("box")
            rscale = random.uniform(rock_size_min, rock_size_max)
            rock.setScale(rscale, rscale, rscale * 0.6)
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
        for i in range(max(0, trees_count)):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(trees_min_r * scale, trees_max_r * scale)
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            
            # Skip center area
            if abs(x) < trees_excl_w and abs(y) < trees_excl_l:
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

    def _parse_resolution(self, text: str, *, default: tuple[int, int]) -> tuple[int, int]:
        s = (text or "").strip().lower()
        if "x" in s:
            try:
                w_s, h_s = s.split("x", 1)
                w = int(w_s.strip())
                h = int(h_s.strip())
                if w > 0 and h > 0:
                    return w, h
            except Exception:
                pass
        return int(default[0]), int(default[1])

    def _load_vehicle_config(self, vehicle_id: str) -> dict | None:
        vehicle_id = (vehicle_id or "").strip()
        if not vehicle_id:
            return None
        try:
            # Vehicle configs are migrated to v2. We still return the legacy-shaped
            # dict until the simulation core is upgraded.
            from core.vehicle_config_loader import load_vehicle_legacy

            return load_vehicle_legacy(vehicle_id)
        except Exception as e:
            print(f"[config] Failed to load vehicle '{vehicle_id}': {e}")
            return None

    def _load_map_selection(self, map_id: str) -> dict | None:
        map_id = (map_id or "").strip()
        if not map_id:
            return None

        try:
            from core.map_config_manager import MapConfigManager

            mgr = MapConfigManager()
            cfg = mgr.load_config(map_id)
        except Exception as e:
            print(f"[config] Failed to load map '{map_id}': {e}")
            return None

        terrain_mod = cfg.modules.get("1_terrain")
        terrain_data = terrain_mod.data if terrain_mod else {}
        terrain_output = str(terrain_data.get("output") or "race_base")
        terrain_generated_files = list(terrain_mod.generated_files or []) if terrain_mod else []

        heightmap_candidates = [
            Path("res/terrain") / f"{terrain_output}.npy",
            Path("res/terrain") / f"{terrain_output}.pgm",
        ]
        heightmap_path = None
        for cand in heightmap_candidates:
            if (PROJECT_ROOT / cand).exists():
                heightmap_path = str(cand)
                break
        if heightmap_path is None:
            heightmap_path = "res/terrain/smoke_flat_hd_regen_cli.npy"

        colors = None
        colors_path = PROJECT_ROOT / "res" / "terrain" / f"{terrain_output}_colors.json"
        if colors_path.exists():
            try:
                with open(colors_path, "r", encoding="utf-8") as f:
                    colors = json.load(f)
            except Exception:
                colors = None

        terrain_runtime = None
        terrain_runtime_candidates = [
            Path(p)
            for p in terrain_generated_files
            if str(p).endswith("_terrain_runtime.json")
        ]

        colors_mod = cfg.modules.get("2_colors")
        if colors_mod and colors_mod.generated_files:
            terrain_runtime_candidates.extend(
                Path(p)
                for p in colors_mod.generated_files
                if str(p).endswith("_terrain_runtime.json")
            )

        terrain_runtime_candidates.append(Path("res/terrain") / f"{terrain_output}_terrain_runtime.json")

        for runtime_candidate in terrain_runtime_candidates:
            runtime_abs = PROJECT_ROOT / runtime_candidate
            if not runtime_abs.exists():
                continue
            try:
                with open(runtime_abs, "r", encoding="utf-8") as f:
                    terrain_runtime = json.load(f)
                break
            except Exception:
                terrain_runtime = None

        if terrain_runtime is None:
            baked_mesh = Path("res/terrain") / f"{terrain_output}_terrain_mesh.bam"
            if (PROJECT_ROOT / baked_mesh).exists():
                terrain_runtime = {
                    "version": "1.0",
                    "terrain_base": terrain_output,
                    "mesh_bam": str(baked_mesh),
                    "heightmap_path": heightmap_path,
                }

        track = None
        track_mod = cfg.modules.get("3_track")
        if track_mod and track_mod.generated_files:
            runtime_json = next((p for p in track_mod.generated_files if str(p).endswith("_runtime.json")), None)
            if runtime_json and (PROJECT_ROOT / runtime_json).exists():
                try:
                    with open(PROJECT_ROOT / runtime_json, "r", encoding="utf-8") as f:
                        track = json.load(f)
                except Exception:
                    track = None
        if track is None and track_mod:
            track = dict(track_mod.data or {})

        scenery = None
        scenery_mod = cfg.modules.get("4_scenery")
        if scenery_mod and scenery_mod.generated_files:
            scen_json = next((p for p in scenery_mod.generated_files if str(p).endswith(".json")), None)
            if scen_json and (PROJECT_ROOT / scen_json).exists():
                try:
                    with open(PROJECT_ROOT / scen_json, "r", encoding="utf-8") as f:
                        scenery = json.load(f)
                except Exception:
                    scenery = None
        if scenery is None and scenery_mod:
            scenery = dict(scenery_mod.data or {})

        return {
            "id": map_id,
            "terrain_output": terrain_output,
            "heightmap_path": heightmap_path,
            "colors": colors,
            "terrain_runtime": terrain_runtime,
            "track": track,
            "scenery": scenery,
        }

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
        self._vehicle_visual_ready = False
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

    def setup_camera(self):
        """Setup camera"""
        self.camera_distance = 15.0
        self.camera_height = 8.0
        self.camera_target_height = 2.0
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

    def _get_camera_follow_anchor(self, state):
        """Return follow anchor position + forward direction in world space.

        Use visual transform once available so camera stays locked to what the
        player actually sees, not a potentially different simulation Z.
        """
        visual_ready = bool(getattr(self, "_vehicle_visual_ready", False))
        vehicle_node = getattr(self, "vehicle_node", None)
        if visual_ready and vehicle_node is not None:
            anchor = vehicle_node.getPos(self.render)
            quat = vehicle_node.getQuat(self.render)
            forward = quat.getForward()
            if forward.length_squared() > 1e-8:
                forward.normalize()
            else:
                forward = Vec3(0.0, 1.0, 0.0)
            return anchor, forward

        heading_rad = math.radians(state.heading)
        anchor = Vec3(float(state.position.x), float(state.position.y), float(state.position.z))
        forward = Vec3(math.sin(heading_rad), math.cos(heading_rad), 0.0)
        if forward.length_squared() > 1e-8:
            forward.normalize()
        return anchor, forward

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
        anchor, _ = self._get_camera_follow_anchor(state)
        target = Vec3(anchor.x, anchor.y, anchor.z + float(self.camera_target_height))

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
        anchor, forward = self._get_camera_follow_anchor(state)
        cam_pos = anchor - forward * float(self.camera_distance) + Vec3(0.0, 0.0, float(self.camera_height))
        self.camera.setPos(cam_pos)
        target = Vec3(anchor.x, anchor.y, anchor.z + float(self.camera_target_height))
        self.camera.lookAt(target)
    
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

        # Keep the directional-light shadow camera centered around the vehicle.
        self._update_shadow_focus(state)
        
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
        self._vehicle_visual_ready = True

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
            
        anchor, forward = self._get_camera_follow_anchor(state)
        desired_pos = anchor - forward * float(self.camera_distance) + Vec3(0.0, 0.0, float(self.camera_height))
        
        current_pos = self.camera.getPos()
        new_x = current_pos[0] + (desired_pos[0] - current_pos[0]) * smooth
        new_y = current_pos[1] + (desired_pos[1] - current_pos[1]) * smooth
        new_z = current_pos[2] + (desired_pos[2] - current_pos[2]) * smooth
        
        self.camera.setPos(new_x, new_y, new_z)
        target = Vec3(anchor.x, anchor.y, anchor.z + float(self.camera_target_height))
        self.camera.lookAt(target)
    
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
        self.player_vehicle.shutdown_systems()
        sys.exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--vehicle", default="", help="Vehicle config id (configs/vehicles/*.json stem)")
    parser.add_argument("--map", dest="map_config", default="", help="Map config id (configs/maps/*.json stem)")
    parser.add_argument("--resolution", default="1280x720", help="Window size, e.g. 1280x720")
    parser.add_argument("--fullscreen", action="store_true", help="Fullscreen window")
    parser.add_argument("--no-shadows", action="store_true", help="Disable shadow casting")
    parser.add_argument("--debug", action="store_true", help="Enable extra debug output")

    args = parser.parse_args()

    # Prevent Panda3D from seeing our custom CLI flags.
    sys.argv = [sys.argv[0]]

    game = RacingGame(
        vehicle_config_id=args.vehicle,
        map_config_id=args.map_config,
        resolution=args.resolution,
        fullscreen=bool(args.fullscreen),
        enable_shadows=not bool(args.no_shadows),
        debug=bool(args.debug),
    )
    game.run()
