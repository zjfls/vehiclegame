"""Runtime terrain construction from heightmaps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from panda3d.core import (
    Filename,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    PNMImage,
    TextureStage,
    Texture,
    Vec3,
)
from opensimplex import OpenSimplex


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class TerrainConfig:
    """Runtime terrain configuration."""

    heightmap_path: str = "res/terrain/smoke_flat_cli.npy"
    texture_path: str = "res/tex/terrain.png"
    world_size_x: float = 240.0
    world_size_y: float = 240.0
    height_scale: float = 18.0
    mesh_step: int = 2
    # UVs drive texture/detail mapping. Default keeps backward compatibility.
    uv_mode: str = "normalized"  # normalized | world
    uv_tiling: float = 3.0
    uv_world_scale: float = 0.06  # UV units per world unit when uv_mode == "world"
    base_height: float = 0.0

    # High-frequency detail overlay to avoid blurry/flat-looking terrain.
    enable_detail_texture: bool = True
    detail_texture_size: int = 256
    detail_texture_strength: float = 0.25  # 0..1, larger = darker micro-contrast
    # Multiplier applied to existing terrain UVs for the detail stage. Higher values
    # create smaller, finer-looking ground patterns without increasing mesh density.
    detail_uv_scale: float = 12.0
    # Negative bias keeps higher mip levels longer (sharper at grazing angles).
    # Too negative can cause shimmering/aliasing.
    detail_lod_bias: float = -0.6
    # Expands the detail noise distribution around 0.5 to keep micro-variation
    # visible after filtering/mipmapping.
    detail_noise_contrast: float = 1.8
    detail_anisotropy: int = 16
    # Procedural texture settings
    use_procedural_texture: bool = True
    grass_color: tuple = (0.18, 0.35, 0.16)
    dirt_color: tuple = (0.45, 0.36, 0.24)
    rock_color: tuple = (0.56, 0.56, 0.54)
    noise_scale: float = 0.05
    noise_octaves: int = 4
    height_rock_threshold: float = 0.65
    slope_rock_threshold: float = 0.5


class RuntimeTerrain:
    """Builds and samples a runtime terrain mesh."""

    def __init__(self, loader, config: TerrainConfig | None = None):
        self.loader = loader
        self.config = config or TerrainConfig()

        self.heightmap = self._load_heightmap(self.config.heightmap_path)
        self.map_height, self.map_width = self.heightmap.shape
        if self.map_width < 2 or self.map_height < 2:
            raise ValueError("Heightmap must be at least 2x2")
        self._noise = OpenSimplex(seed=42)

    def build(self, parent: NodePath) -> NodePath:
        """Build terrain mesh and attach it to the given parent node."""

        step = max(1, int(self.config.mesh_step))
        sampled = self.heightmap[::step, ::step]
        sample_h, sample_w = sampled.shape
        if sample_w < 2 or sample_h < 2:
            raise ValueError("mesh_step is too large for the selected heightmap")
        dx = self.config.world_size_x / max(1, sample_w - 1)
        dy = self.config.world_size_y / max(1, sample_h - 1)

        # Slope is used for rock placement; compute it in world units so the
        # thresholds remain meaningful when world_size/height_scale changes.
        slope = self._compute_slope(sampled, dx, dy)

        fmt = GeomVertexFormat.getV3n3c4t2()
        vdata = GeomVertexData("terrain", fmt, Geom.UHStatic)
        vtx = GeomVertexWriter(vdata, "vertex")
        normal = GeomVertexWriter(vdata, "normal")
        color = GeomVertexWriter(vdata, "color")
        uv = GeomVertexWriter(vdata, "texcoord")

        for gy in range(sample_h):
            for gx in range(sample_w):
                world_x = -0.5 * self.config.world_size_x + gx * dx
                world_y = -0.5 * self.config.world_size_y + gy * dy
                h_norm = float(sampled[gy, gx])
                world_z = self.config.base_height + h_norm * self.config.height_scale

                vtx.addData3(world_x, world_y, world_z)
                normal.addData3(self._mesh_normal(sampled, gx, gy, dx, dy))
                
                if self.config.use_procedural_texture:
                    color.addData4(
                        *self._procedural_color(
                            h_norm,
                            float(slope[gy, gx]),
                            float(world_x),
                            float(world_y),
                        )
                    )
                else:
                    color.addData4(*self._blend_color(h_norm, float(slope[gy, gx])))

                if str(self.config.uv_mode).lower() == "world":
                    # World-space UVs keep texture scale stable when the terrain is scaled up.
                    u = float(world_x) * float(self.config.uv_world_scale)
                    v = float(world_y) * float(self.config.uv_world_scale)
                else:
                    u = (gx / max(1, sample_w - 1)) * self.config.uv_tiling
                    v = (gy / max(1, sample_h - 1)) * self.config.uv_tiling
                uv.addData2(u, v)

        tris = GeomTriangles(Geom.UHStatic)
        for y in range(sample_h - 1):
            for x in range(sample_w - 1):
                i0 = y * sample_w + x
                i1 = i0 + 1
                i2 = i0 + sample_w
                i3 = i2 + 1

                tris.addVertices(i0, i1, i2)
                tris.addVertices(i1, i3, i2)
        tris.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(tris)

        node = GeomNode("terrain_mesh")
        node.addGeom(geom)

        terrain_np = parent.attachNewNode(node)
        terrain_np.setTwoSided(False)
        if not self.config.use_procedural_texture:
            self._apply_texture(terrain_np)

        # Add a high-frequency detail layer in a separate texture stage.
        # This improves perceived sharpness even when using vertex colors.
        if bool(self.config.enable_detail_texture):
            self._apply_detail_texture(terrain_np)
        return terrain_np

    def _apply_detail_texture(self, terrain_np: NodePath) -> None:
        """Apply a small, tileable detail texture to reduce blurry/flat visuals."""

        size = int(self.config.detail_texture_size)
        if size < 8:
            return

        strength = float(self.config.detail_texture_strength)
        strength = 0.0 if strength < 0.0 else (1.0 if strength > 1.0 else strength)

        contrast = float(self.config.detail_noise_contrast)
        if contrast <= 0.0:
            contrast = 1.0

        tex = Texture("terrain_detail")
        img = PNMImage(size, size, 3)

        # Prefer periodic Perlin noise when available (tileable by construction).
        # Fall back to a deterministic hash noise otherwise.
        try:
            from noise import pnoise2  # type: ignore

            for y in range(size):
                # Use size-1 so the first/last texels match; important for seamless WMRepeat.
                fy = y / float(max(1, size - 1))
                for x in range(size):
                    fx = x / float(max(1, size - 1))
                    n = 0.0
                    amp = 1.0
                    freq = 4.0
                    amp_total = 0.0
                    for _ in range(4):
                        n += amp * pnoise2(
                            fx * freq,
                            fy * freq,
                            repeatx=int(freq),
                            repeaty=int(freq),
                            base=7,
                        )
                        amp_total += amp
                        amp *= 0.5
                        freq *= 2.0
                    n = (n / max(1e-6, amp_total)) * 0.5 + 0.5
                    n = 0.5 + (n - 0.5) * contrast
                    n = 0.0 if n < 0.0 else (1.0 if n > 1.0 else n)

                    # Keep values near 1.0 so modulating doesn't crush the base colors.
                    val = 1.0 - strength * (1.0 - float(n))
                    img.setXel(x, y, val, val, val)
        except Exception:
            import math

            # Fallback: tileable simplex-based noise using a 4D torus mapping.
            # This keeps the texture seamless even without the optional `noise` dependency.
            tau = getattr(math, "tau", 2.0 * math.pi)

            for y in range(size):
                fy = y / float(max(1, size - 1))
                for x in range(size):
                    fx = x / float(max(1, size - 1))

                    n = 0.0
                    amp = 1.0
                    freq = 4.0
                    amp_total = 0.0
                    for _ in range(4):
                        ax = tau * fx * freq
                        ay = tau * fy * freq
                        layer = self._noise.noise4(
                            math.cos(ax),
                            math.sin(ax),
                            math.cos(ay),
                            math.sin(ay),
                        )
                        n += amp * layer
                        amp_total += amp
                        amp *= 0.5
                        freq *= 2.0

                    n = (n / max(1e-6, amp_total)) * 0.5 + 0.5
                    n = 0.5 + (n - 0.5) * contrast
                    n = 0.0 if n < 0.0 else (1.0 if n > 1.0 else n)
                    val = 1.0 - strength * (1.0 - float(n))
                    img.setXel(x, y, val, val, val)

        tex.load(img)
        tex.setWrapU(Texture.WMRepeat)
        tex.setWrapV(Texture.WMRepeat)
        tex.setMinfilter(Texture.FTLinearMipmapLinear)
        tex.setMagfilter(Texture.FTLinear)

        # High anisotropy is important for racing games where the ground is viewed at a low angle.
        try:
            tex.setAnisotropicDegree(int(self.config.detail_anisotropy))
        except Exception:
            pass

        # Ensure mipmaps exist for better minification quality.
        try:
            tex.generateRamMipmapImages()
        except Exception:
            pass

        # Slightly bias towards higher-resolution mips for more visible texture.
        try:
            from panda3d.core import SamplerState

            # getDefaultSampler() returns a const object; copy it before mutating.
            sampler = SamplerState(tex.getDefaultSampler())
            sampler.setLodBias(float(self.config.detail_lod_bias))
            tex.setDefaultSampler(sampler)
        except Exception:
            pass

        stage = TextureStage("detail")
        stage.setMode(TextureStage.MModulate)
        # Keep stage ordering stable if a base texture is ever enabled.
        try:
            stage.setSort(10)
        except Exception:
            pass
        terrain_np.setTexture(stage, tex, 1)

        # Apply extra tiling for the detail stage without changing base UVs.
        uv_scale = float(self.config.detail_uv_scale)
        if uv_scale > 0.0 and abs(uv_scale - 1.0) > 1e-6:
            terrain_np.setTexScale(stage, uv_scale, uv_scale)

    def normalized_to_world(self, u: float, v: float) -> tuple[float, float]:
        """Convert normalized coordinates [0..1] into world X/Y."""
        x = (float(u) - 0.5) * float(self.config.world_size_x)
        y = (float(v) - 0.5) * float(self.config.world_size_y)
        return x, y

    def pixel_to_world(self, px: float, py: float) -> tuple[float, float]:
        """Convert heightmap pixel coordinates into world X/Y."""
        u = float(px) / max(1.0, float(self.map_width - 1))
        v = float(py) / max(1.0, float(self.map_height - 1))
        return self.normalized_to_world(u, v)

    def world_to_normalized(self, world_x: float, world_y: float) -> tuple[float, float]:
        """Convert world X/Y into normalized coordinates [0..1]."""
        u = (float(world_x) / float(self.config.world_size_x)) + 0.5
        v = (float(world_y) / float(self.config.world_size_y)) + 0.5
        return u, v

    def sample_height(self, world_x: float, world_y: float) -> float:
        """Sample terrain height using bilinear interpolation in world coordinates."""
        u, v = self.world_to_normalized(world_x, world_y)
        u = min(1.0, max(0.0, u))
        v = min(1.0, max(0.0, v))

        grid_x = u * (self.map_width - 1)
        grid_y = v * (self.map_height - 1)

        x0 = int(np.floor(grid_x))
        y0 = int(np.floor(grid_y))
        x1 = min(self.map_width - 1, x0 + 1)
        y1 = min(self.map_height - 1, y0 + 1)

        tx = grid_x - x0
        ty = grid_y - y0

        h00 = self.heightmap[y0, x0]
        h10 = self.heightmap[y0, x1]
        h01 = self.heightmap[y1, x0]
        h11 = self.heightmap[y1, x1]

        top = h00 * (1.0 - tx) + h10 * tx
        bottom = h01 * (1.0 - tx) + h11 * tx
        h_norm = top * (1.0 - ty) + bottom * ty

        return self.config.base_height + float(h_norm) * self.config.height_scale

    def sample_normal(self, world_x: float, world_y: float) -> Vec3:
        """Estimate terrain normal in world coordinates."""
        eps_x = self.config.world_size_x / max(64, self.map_width - 1)
        eps_y = self.config.world_size_y / max(64, self.map_height - 1)

        h_left = self.sample_height(world_x - eps_x, world_y)
        h_right = self.sample_height(world_x + eps_x, world_y)
        h_down = self.sample_height(world_x, world_y - eps_y)
        h_up = self.sample_height(world_x, world_y + eps_y)

        normal = Vec3(h_left - h_right, h_down - h_up, 2.0 * max(eps_x, eps_y))
        if normal.length_squared() < 1e-8:
            return Vec3(0.0, 0.0, 1.0)
        normal.normalize()
        return normal

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return PROJECT_ROOT / candidate

    def _load_heightmap(self, path: str) -> np.ndarray:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Heightmap not found: {resolved}")

        suffix = resolved.suffix.lower()
        if suffix == ".npy":
            data = np.load(resolved)
        elif suffix == ".pgm":
            data = self._load_pgm16_as_array(resolved)
        else:
            raise ValueError(f"Unsupported heightmap format: {resolved.suffix}")

        if data.ndim != 2:
            raise ValueError("Heightmap must be a 2D array")

        data = data.astype(np.float32)
        lo = float(np.min(data))
        hi = float(np.max(data))
        if hi > lo:
            data = (data - lo) / (hi - lo)
        else:
            data = np.zeros_like(data, dtype=np.float32)
        return np.clip(data, 0.0, 1.0)

    def _load_pgm16_as_array(self, path: Path) -> np.ndarray:
        image = PNMImage()
        if not image.read(Filename.from_os_specific(str(path))):
            raise RuntimeError(f"Failed to read PGM file: {path}")

        width = image.getXSize()
        height = image.getYSize()
        arr = np.zeros((height, width), dtype=np.float32)
        for y in range(height):
            for x in range(width):
                arr[y, x] = image.getGrayVal(x, y) / 65535.0
        return arr

    def _compute_slope(self, heightmap: np.ndarray, dx: float, dy: float) -> np.ndarray:
        """Estimate normalized slope from a normalized heightmap.

        Returns values in [0..1] where higher means steeper.
        """

        # Convert to world-space height (Z) before differentiating.
        z = heightmap.astype(np.float32) * float(self.config.height_scale)
        # np.gradient expects spacing per axis: (dy, dx) because axis0 is Y.
        gy, gx = np.gradient(z, float(dy), float(dx))
        slope = np.sqrt(gx * gx + gy * gy)
        # Map typical terrain slopes into [0..1]. The factor is tuned for this
        # project's default terrain sizes; callers can adjust thresholds.
        return np.clip(slope * 3.0, 0.0, 1.0)

    def _mesh_normal(
        self, heightmap: np.ndarray, gx: int, gy: int, dx: float, dy: float
    ) -> Vec3:
        x0 = max(0, gx - 1)
        x1 = min(heightmap.shape[1] - 1, gx + 1)
        y0 = max(0, gy - 1)
        y1 = min(heightmap.shape[0] - 1, gy + 1)

        h_left = float(heightmap[gy, x0]) * self.config.height_scale
        h_right = float(heightmap[gy, x1]) * self.config.height_scale
        h_down = float(heightmap[y0, gx]) * self.config.height_scale
        h_up = float(heightmap[y1, gx]) * self.config.height_scale

        nx = -(h_right - h_left) / max(0.001, (x1 - x0) * dx)
        ny = -(h_up - h_down) / max(0.001, (y1 - y0) * dy)

        n = Vec3(nx, ny, 1.0)
        n.normalize()
        return n

    def _fbm_noise(
        self,
        x: float,
        y: float,
        *,
        scale: float | None = None,
        octaves: int | None = None,
    ) -> float:
        """Fractal Brownian Motion noise using OpenSimplex.

        x/y are in world units. Larger scale values yield more frequent variation.
        """

        scale_f = float(self.config.noise_scale if scale is None else scale)
        octaves_i = int(self.config.noise_octaves if octaves is None else octaves)

        value = 0.0
        amplitude = 0.5
        frequency = 1.0
        max_value = 0.0

        for _ in range(max(1, octaves_i)):
            value += amplitude * self._noise.noise2(x * frequency * scale_f, y * frequency * scale_f)
            max_value += amplitude
            amplitude *= 0.5
            frequency *= 2.0

        return (value / max_value) * 0.5 + 0.5

    def _smoothstep(self, edge0: float, edge1: float, x: float) -> float:
        if edge1 == edge0:
            return 0.0
        t = (float(x) - float(edge0)) / (float(edge1) - float(edge0))
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
        return t * t * (3.0 - 2.0 * t)

    def _procedural_color(
        self,
        h_norm: float,
        slope_norm: float,
        world_x: float,
        world_y: float,
    ) -> tuple[float, float, float, float]:
        """Generate procedural terrain color using world-space noise and slope/height rules."""

        grass_r, grass_g, grass_b = self.config.grass_color
        dirt_r, dirt_g, dirt_b = self.config.dirt_color
        rock_r, rock_g, rock_b = self.config.rock_color

        # World-space noise for large patches + small detail. Using world coords
        # avoids the near-constant noise you get when sampling only [0..1].
        macro = self._fbm_noise(world_x, world_y)
        detail = self._fbm_noise(
            world_x,
            world_y,
            scale=float(self.config.noise_scale) * 4.0,
            octaves=max(1, int(self.config.noise_octaves) - 2),
        )
        speckle = self._fbm_noise(world_x, world_y, scale=float(self.config.noise_scale) * 12.0, octaves=1)

        # Rock from height + slope.
        rock_from_height = self._smoothstep(self.config.height_rock_threshold, min(1.0, self.config.height_rock_threshold + 0.22), h_norm)
        rock_from_slope = self._smoothstep(self.config.slope_rock_threshold, min(1.0, self.config.slope_rock_threshold + 0.25), slope_norm)

        # Dirt/grass patches from macro noise (with a little height bias).
        dirt_patch = self._smoothstep(0.35, 0.65, macro)
        dirt_height = 1.0 - self._smoothstep(0.70, 0.92, h_norm)

        rock_w = max(rock_from_height, rock_from_slope)
        dirt_w = (1.0 - rock_w) * dirt_patch * dirt_height
        grass_w = max(0.0, 1.0 - rock_w - dirt_w)

        total = rock_w + grass_w + dirt_w
        if total > 1e-6:
            rock_w /= total
            grass_w /= total
            dirt_w /= total

        r = grass_w * float(grass_r) + dirt_w * float(dirt_r) + rock_w * float(rock_r)
        g = grass_w * float(grass_g) + dirt_w * float(dirt_g) + rock_w * float(rock_g)
        b = grass_w * float(grass_b) + dirt_w * float(dirt_b) + rock_w * float(rock_b)

        # Add subtle value variation and tiny pebble speckles.
        shade = 0.85 + 0.30 * (detail - 0.5)
        pebble = self._smoothstep(0.72, 0.92, speckle)
        r = r * shade * (1.0 - 0.20 * pebble) + float(rock_r) * 0.10 * pebble
        g = g * shade * (1.0 - 0.20 * pebble) + float(rock_g) * 0.10 * pebble
        b = b * shade * (1.0 - 0.20 * pebble) + float(rock_b) * 0.10 * pebble

        return float(r), float(g), float(b), 1.0

    def _blend_color(self, h_norm: float, slope_norm: float) -> tuple[float, float, float, float]:
        """Legacy color blending (without noise)."""
        grass = np.array([0.18, 0.35, 0.16], dtype=np.float32)
        dirt = np.array([0.45, 0.36, 0.24], dtype=np.float32)
        rock = np.array([0.56, 0.56, 0.54], dtype=np.float32)

        rock_w = np.clip(0.75 * slope_norm + max(0.0, h_norm - 0.65) * 1.8, 0.0, 1.0)
        grass_w = np.clip((1.0 - slope_norm) * (1.0 - h_norm * 0.65), 0.0, 1.0)
        dirt_w = max(0.0, 1.0 - rock_w - grass_w)

        total = rock_w + grass_w + dirt_w
        if total > 1e-6:
            rock_w /= total
            grass_w /= total
            dirt_w /= total

        color = grass_w * grass + dirt_w * dirt + rock_w * rock
        return float(color[0]), float(color[1]), float(color[2]), 1.0

    def _apply_texture(self, terrain_np: NodePath) -> None:
        if not self.loader:
            return

        texture_path = self._resolve_path(self.config.texture_path)
        if not texture_path.exists():
            return

        texture = self.loader.loadTexture(str(texture_path))
        if not texture:
            return

        texture.setMinfilter(Texture.FTLinearMipmapLinear)
        texture.setMagfilter(Texture.FTLinear)
        terrain_np.setTexture(texture, 1)
