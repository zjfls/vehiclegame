"""Terrain query interface for decoupling systems from world module.

This module defines an abstract interface that terrain implementations must
provide. Vehicle systems can query terrain properties through this interface
without directly depending on the world/terrain_runtime module.

Design goals:
- Decouple vehicle systems from world module
- Allow different terrain implementations (procedural, heightmap, physics engine)
- Enable testing with mock terrain
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from ..data.vehicle_state import Vector3


@dataclass
class TerrainSample:
    """Result of sampling terrain at a world position."""

    height: float
    normal: Vector3
    # Optional properties for advanced physics
    friction: float = 1.0
    surface_type: str = "default"  # e.g., "grass", "dirt", "rock", "asphalt"


@runtime_checkable
class ITerrainQuery(Protocol):
    """Protocol interface for terrain queries.

    Vehicle systems should use this interface instead of directly accessing
    RuntimeTerrain or RuntimeMapBuilder. This allows:
    - Swapping terrain implementations
    - Mocking terrain for tests
    - Decoupling systems from world module

    Using Protocol instead of ABC for flexibility - any object with these
    methods will work, no inheritance required.
    """

    def sample_height(self, x: float, y: float) -> float:
        """Get terrain height at world position (x, y).

        Args:
            x: World X coordinate
            y: World Y coordinate

        Returns:
            Terrain height at the given position
        """
        ...

    def sample_normal(self, x: float, y: float) -> Vector3:
        """Get terrain surface normal at world position (x, y).

        Args:
            x: World X coordinate
            y: World Y coordinate

        Returns:
            Unit normal vector pointing up from terrain surface
        """
        ...

    def sample(self, x: float, y: float) -> TerrainSample:
        """Get full terrain sample at world position (x, y).

        This is the preferred method for systems that need multiple
        terrain properties, as implementations can optimize batch queries.

        Args:
            x: World X coordinate
            y: World Y coordinate

        Returns:
            TerrainSample with height, normal, friction, and surface type
        """
        ...

    def get_world_bounds(self) -> tuple[float, float, float, float]:
        """Get terrain world bounds as (min_x, min_y, max_x, max_y).

        Returns:
            Tuple of (min_x, min_y, max_x, max_y) in world coordinates
        """
        ...


class NullTerrainQuery:
    """Null implementation that returns flat ground.

    Useful for testing or when terrain is not available.
    """

    def sample_height(self, x: float, y: float) -> float:
        return 0.0

    def sample_normal(self, x: float, y: float) -> Vector3:
        return Vector3(0.0, 0.0, 1.0)

    def sample(self, x: float, y: float) -> TerrainSample:
        return TerrainSample(
            height=0.0,
            normal=Vector3(0.0, 0.0, 1.0),
            friction=1.0,
            surface_type="default",
        )

    def get_world_bounds(self) -> tuple[float, float, float, float]:
        return (-10000.0, -10000.0, 10000.0, 10000.0)


class TerrainQueryAdapter:
    """Adapter that wraps RuntimeTerrain/RuntimeMapBuilder.

    This bridges the world module's terrain implementation to the
    ITerrainQuery interface used by vehicle systems.
    """

    def __init__(self, terrain):
        """Initialize adapter with a terrain instance.

        Args:
            terrain: RuntimeTerrain or RuntimeMapBuilder instance
        """
        self._terrain = terrain

    def sample_height(self, x: float, y: float) -> float:
        return float(self._terrain.sample_height(x, y))

    def sample_normal(self, x: float, y: float) -> Vector3:
        # RuntimeTerrain returns Vec3 from Panda3D
        n = self._terrain.sample_normal(x, y)
        return Vector3(float(n.x), float(n.y), float(n.z))

    def sample(self, x: float, y: float) -> TerrainSample:
        height = self.sample_height(x, y)
        normal = self.sample_normal(x, y)

        # Future: could query surface type from texture/material
        # For now, return default values
        return TerrainSample(
            height=height,
            normal=normal,
            friction=1.0,
            surface_type="default",
        )

    def get_world_bounds(self) -> tuple[float, float, float, float]:
        # Try to get bounds from terrain config
        if hasattr(self._terrain, 'config'):
            config = self._terrain.config
            half_x = config.world_size_x / 2.0
            half_y = config.world_size_y / 2.0
            return (-half_x, -half_y, half_x, half_y)

        # Fallback to large bounds
        return (-10000.0, -10000.0, 10000.0, 10000.0)
