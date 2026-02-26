"""Simple test to verify procedural terrain colors"""
import os
import sys
from direct.showbase.ShowBase import ShowBase
from panda3d.core import *

# Ensure project root is on sys.path when running from tests/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.world.terrain_runtime import RuntimeTerrain, TerrainConfig

class TerrainTest(ShowBase):
    def __init__(self):
        super().__init__()
        self.setBackgroundColor(0.5, 0.7, 0.85)
        
        # Setup lighting
        ambient = AmbientLight("ambient")
        ambient.setColor((0.6, 0.6, 0.65, 1))
        self.render.setLight(self.render.attachNewNode(ambient))
        
        sun = DirectionalLight("sun")
        sun.setColor((1.0, 0.98, 0.9, 1))
        sun.setDirection((-0.3, -0.6, -0.7))
        sun_np = self.render.attachNewNode(sun)
        self.render.setLight(sun_np)
        self.render.setShaderAuto()
        
        # Create terrain
        config = TerrainConfig(
            heightmap_path="res/terrain/smoke_flat_cli.npy",
            use_procedural_texture=True,
            world_size_x=120.0,
            world_size_y=120.0,
            height_scale=8.0,
            mesh_step=1,
            noise_scale=0.04,
            noise_octaves=4,
            grass_color=(0.15, 0.38, 0.14),
            dirt_color=(0.48, 0.38, 0.26),
            rock_color=(0.58, 0.55, 0.52),
        )
        
        self.terrain = RuntimeTerrain(self.loader, config)
        self.terrain_node = self.terrain.build(self.render)
        
        # Position camera to see terrain
        self.camera.setPos(0, -80, 60)
        self.camera.lookAt(0, 0, 0)
        
        print("Terrain Test Loaded!")
        print("Mouse: Rotate view | Scroll: Zoom | ESC: Exit")
        
        # Enable mouse camera control
        self.disableMouse()
        self.camera_ctrl = None

if __name__ == "__main__":
    game = TerrainTest()
    game.run()
