"""Runtime track data loading and rendering."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    LineSegs,
    NodePath,
    Vec3,
    VBase4,
)

from .terrain_runtime import PROJECT_ROOT, RuntimeTerrain


@dataclass
class TrackConfig:
    """Runtime track configuration."""

    track_csv_path: str = "scripts/track_example.csv"
    coord_space: str = "normalized"  # normalized | pixel | world
    elevation_offset: float = 0.05
    track_width: float = 9.0
    border_width: float = 0.8
    samples_per_segment: int = 8
    centerline_thickness: float = 2.0
    show_centerline: bool = True
    track_color: tuple[float, float, float, float] = (0.18, 0.18, 0.20, 1.0)
    border_color: tuple[float, float, float, float] = (0.85, 0.14, 0.14, 1.0)
    centerline_color: tuple[float, float, float, float] = (0.95, 0.95, 0.95, 1.0)


@dataclass
class TrackPoint:
    x: float
    y: float
    z: float
    distance: float


class RuntimeTrack:
    """Loads track path data and builds a runtime track mesh."""

    def __init__(self, config: TrackConfig, terrain: RuntimeTerrain):
        self.config = config
        self.terrain = terrain

        base_points = self._load_track_points(self.config.track_csv_path)
        world_points = self._to_world_points(base_points)
        dense_points = self._densify(world_points)
        self.path_points = self._to_track_points(dense_points)

    def build(self, parent: NodePath) -> NodePath:
        """Build track geometry and attach it to parent."""

        if len(self.path_points) < 2:
            return parent.attachNewNode("track_empty")

        root = parent.attachNewNode("track")
        positions = [Vec3(p.x, p.y, p.z) for p in self.path_points]

        track_mesh = self._build_ribbon(
            positions,
            width=self.config.track_width,
            color=self.config.track_color,
            name="track_surface",
        )
        track_mesh.reparentTo(root)

        left_border, right_border = self._build_borders(positions)
        left_border.reparentTo(root)
        right_border.reparentTo(root)

        if self.config.show_centerline:
            line = self._build_centerline(positions)
            line.reparentTo(root)

        return root

    def get_path_points(self) -> List[TrackPoint]:
        """Get track path points in world coordinates."""

        return list(self.path_points)

    def get_start_pose(self) -> tuple[Vec3, float]:
        """Get start position and heading from track path."""

        if len(self.path_points) < 2:
            return Vec3(0.0, 0.0, self.terrain.sample_height(0.0, 0.0)), 0.0

        p0 = self.path_points[0]
        p1 = self.path_points[1]
        dx = p1.x - p0.x
        dy = p1.y - p0.y
        heading = math.degrees(math.atan2(dx, dy))
        return Vec3(p0.x, p0.y, p0.z), float(heading)

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return PROJECT_ROOT / candidate

    def _load_track_points(self, path: str) -> List[Tuple[float, float]]:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Track csv not found: {resolved}")

        points: List[Tuple[float, float]] = []
        with open(resolved, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                if row[0].strip().startswith("#"):
                    continue
                if len(row) < 2:
                    continue
                points.append((float(row[0]), float(row[1])))

        if len(points) < 2:
            raise ValueError("Track CSV requires at least two points")
        return points

    def _to_world_points(self, points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        for px, py in points:
            if self.config.coord_space == "normalized":
                x, y = self.terrain.normalized_to_world(px, py)
            elif self.config.coord_space == "pixel":
                x, y = self.terrain.pixel_to_world(px, py)
            elif self.config.coord_space == "world":
                x = px
                y = py
            else:
                raise ValueError(f"Unsupported coord space: {self.config.coord_space}")
            out.append((x, y))
        return out

    def _densify(self, points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(points) < 2:
            return list(points)

        n = max(1, int(self.config.samples_per_segment))
        dense: List[Tuple[float, float]] = []
        for i in range(len(points) - 1):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            for s in range(n):
                t = s / float(n)
                dense.append((x0 * (1.0 - t) + x1 * t, y0 * (1.0 - t) + y1 * t))
        dense.append(points[-1])
        return dense

    def _to_track_points(self, points: Sequence[Tuple[float, float]]) -> List[TrackPoint]:
        out: List[TrackPoint] = []
        dist = 0.0
        prev_x = None
        prev_y = None
        for x, y in points:
            z = self.terrain.sample_height(x, y) + self.config.elevation_offset
            if prev_x is not None and prev_y is not None:
                dx = x - prev_x
                dy = y - prev_y
                dist += (dx * dx + dy * dy) ** 0.5
            out.append(TrackPoint(x=x, y=y, z=z, distance=dist))
            prev_x, prev_y = x, y
        return out

    def _build_centerline(self, positions: Sequence[Vec3]) -> NodePath:
        lines = LineSegs("track_centerline")
        lines.setThickness(max(1.0, self.config.centerline_thickness))
        lines.setColor(VBase4(*self.config.centerline_color))

        lines.moveTo(positions[0])
        for p in positions[1:]:
            lines.drawTo(p)

        return NodePath(lines.create())

    def _build_borders(self, positions: Sequence[Vec3]) -> tuple[NodePath, NodePath]:
        left = self._build_offset_ribbon(
            positions,
            center_offset=0.5 * self.config.track_width + 0.5 * self.config.border_width,
            width=self.config.border_width,
            color=self.config.border_color,
            name="track_border_left",
        )
        right = self._build_offset_ribbon(
            positions,
            center_offset=-(0.5 * self.config.track_width + 0.5 * self.config.border_width),
            width=self.config.border_width,
            color=self.config.border_color,
            name="track_border_right",
        )
        return left, right

    def _build_offset_ribbon(
        self,
        positions: Sequence[Vec3],
        center_offset: float,
        width: float,
        color: tuple[float, float, float, float],
        name: str,
    ) -> NodePath:
        shifted: List[Vec3] = []
        tangents = self._compute_tangents(positions)
        for i, p in enumerate(positions):
            t = tangents[i]
            normal = Vec3(-t.y, t.x, 0.0)
            if normal.length_squared() < 1e-8:
                normal = Vec3(1.0, 0.0, 0.0)
            normal.normalize()
            shifted.append(Vec3(p.x + normal.x * center_offset, p.y + normal.y * center_offset, p.z))

        return self._build_ribbon(shifted, width=width, color=color, name=name)

    def _build_ribbon(
        self,
        positions: Sequence[Vec3],
        width: float,
        color: tuple[float, float, float, float],
        name: str,
    ) -> NodePath:
        fmt = GeomVertexFormat.getV3n3c4t2()
        vdata = GeomVertexData(name, fmt, Geom.UHStatic)

        vtx = GeomVertexWriter(vdata, "vertex")
        normal = GeomVertexWriter(vdata, "normal")
        clr = GeomVertexWriter(vdata, "color")
        uv = GeomVertexWriter(vdata, "texcoord")

        half_w = max(0.1, width * 0.5)
        tangents = self._compute_tangents(positions)
        total_len = max(0.001, self.path_points[-1].distance)

        for i, p in enumerate(positions):
            tangent = tangents[i]
            side = Vec3(-tangent.y, tangent.x, 0.0)
            if side.length_squared() < 1e-8:
                side = Vec3(1.0, 0.0, 0.0)
            side.normalize()

            left = Vec3(p.x + side.x * half_w, p.y + side.y * half_w, p.z)
            right = Vec3(p.x - side.x * half_w, p.y - side.y * half_w, p.z)

            v = self.path_points[i].distance / total_len

            vtx.addData3(left)
            normal.addData3(0.0, 0.0, 1.0)
            clr.addData4(*color)
            uv.addData2(0.0, v)

            vtx.addData3(right)
            normal.addData3(0.0, 0.0, 1.0)
            clr.addData4(*color)
            uv.addData2(1.0, v)

        tris = GeomTriangles(Geom.UHStatic)
        for i in range(len(positions) - 1):
            i0 = i * 2
            i1 = i0 + 1
            i2 = i0 + 2
            i3 = i0 + 3

            # CCW winding when viewed from +Z so the surface is visible from above.
            tris.addVertices(i0, i1, i2)
            tris.addVertices(i1, i3, i2)
        tris.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(tris)

        node = GeomNode(name)
        node.addGeom(geom)
        return NodePath(node)

    def _compute_tangents(self, positions: Sequence[Vec3]) -> List[Vec3]:
        tangents: List[Vec3] = []
        for i in range(len(positions)):
            if i == 0:
                vec = positions[1] - positions[0]
            elif i == len(positions) - 1:
                vec = positions[-1] - positions[-2]
            else:
                vec = positions[i + 1] - positions[i - 1]

            tangent = Vec3(vec.x, vec.y, 0.0)
            if tangent.length_squared() < 1e-8:
                tangent = Vec3(0.0, 1.0, 0.0)
            tangent.normalize()
            tangents.append(tangent)
        return tangents
