"""Runtime map composition: terrain and track."""

from __future__ import annotations

from dataclasses import dataclass, field

from panda3d.core import NodePath

from .terrain_runtime import RuntimeTerrain, TerrainConfig
from .track_runtime import RuntimeTrack, TrackConfig


@dataclass
class RuntimeMapConfig:
    """Top-level runtime map config."""

    terrain: TerrainConfig = field(default_factory=TerrainConfig)
    track: TrackConfig = field(default_factory=TrackConfig)


class RuntimeMapBuilder:
    """Build runtime map nodes and expose query helpers."""

    def __init__(self, loader, config: RuntimeMapConfig | None = None):
        self.loader = loader
        self.config = config or RuntimeMapConfig()
        self.terrain = RuntimeTerrain(loader, self.config.terrain)
        self.track = RuntimeTrack(self.config.track, self.terrain)

        self.root: NodePath | None = None
        self.terrain_node: NodePath | None = None
        self.track_node: NodePath | None = None

    def build(self, parent: NodePath) -> NodePath:
        """Build and attach terrain + track nodes."""

        self.root = parent.attachNewNode("runtime_map")
        self.terrain_node = self.terrain.build(self.root)
        self.track_node = self.track.build(self.root)
        return self.root

    def sample_height(self, x: float, y: float) -> float:
        return self.terrain.sample_height(x, y)

    def sample_normal(self, x: float, y: float):
        return self.terrain.sample_normal(x, y)

    def get_track_start(self):
        return self.track.get_start_pose()

    def get_track_points(self):
        return self.track.get_path_points()

