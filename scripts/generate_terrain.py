#!/usr/bin/env python3
"""
Procedural terrain generator for racing base maps.

Stack baseline:
- numpy/scipy for numeric processing and smoothing
- opensimplex/noise for terrain detail synthesis

Outputs:
- 16-bit PGM heightmap (engine-friendly, no extra image dependencies)
- .npy raw height array
- JSON report with generation stats and parameters
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np


@dataclass
class Timer:
    label: str
    start: float


def start_timer(label: str) -> Timer:
    now = time.perf_counter()
    print(f"[terrain] START {label}")
    return Timer(label=label, start=now)


def end_timer(timer: Timer) -> None:
    elapsed = time.perf_counter() - timer.start
    print(f"[terrain] DONE  {timer.label} ({elapsed:.3f}s)")


def _gaussian_filter_fallback(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Small, dependency-free Gaussian blur fallback.

    SciPy's ndimage gaussian_filter is preferred, but this implementation is
    good enough for generating smooth race heightmaps.
    """

    sigma = float(sigma)
    if sigma <= 0.0:
        return arr

    # Build a 1D Gaussian kernel and apply separably (X then Y).
    radius = int(max(1.0, math.ceil(3.0 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    k = np.exp(-(x * x) / (2.0 * sigma * sigma))
    k /= float(k.sum())

    def convolve1d_reflect(a: np.ndarray, kernel: np.ndarray, axis: int) -> np.ndarray:
        pad = kernel.size // 2
        pads = [(0, 0)] * a.ndim
        pads[axis] = (pad, pad)
        ap = np.pad(a, pads, mode="reflect")

        # Move the convolving axis to the end for simpler slicing.
        ap = np.moveaxis(ap, axis, -1)
        out = np.empty(ap.shape[:-1] + (ap.shape[-1] - 2 * pad,), dtype=np.float64)
        # Sliding window dot product; kernel sizes here are small (sigma is small).
        for i in range(out.shape[-1]):
            out[..., i] = np.tensordot(ap[..., i : i + kernel.size], kernel, axes=([-1], [0]))
        out = np.moveaxis(out, -1, axis)
        return out

    a64 = arr.astype(np.float64, copy=False)
    blurred = convolve1d_reflect(a64, k, axis=1)
    blurred = convolve1d_reflect(blurred, k, axis=0)
    return blurred.astype(arr.dtype, copy=False)


def _require_scipy():
    """Return (gaussian_filter, distance_transform_edt or None).

    - If SciPy is available, return the real functions.
    - Otherwise, return a local Gaussian fallback and None for distance transform.
      Track flattening requires SciPy and will be skipped/blocked accordingly.
    """

    try:
        from scipy.ndimage import distance_transform_edt, gaussian_filter  # type: ignore

        return gaussian_filter, distance_transform_edt
    except ImportError:
        return _gaussian_filter_fallback, None


def _import_generator(name: str):
    if name == "opensimplex":
        try:
            from opensimplex import OpenSimplex
        except ImportError as exc:
            raise RuntimeError(
                "opensimplex is not installed. "
                "Install with: python3 -m pip install opensimplex"
            ) from exc
        return OpenSimplex

    if name == "noise":
        try:
            from noise import pnoise2
        except ImportError as exc:
            raise RuntimeError(
                "noise is not installed. Install with: python3 -m pip install noise"
            ) from exc
        return pnoise2

    raise ValueError(f"Unsupported generator: {name}")


def _normalize01(arr: np.ndarray) -> np.ndarray:
    low = float(arr.min())
    high = float(arr.max())
    if math.isclose(low, high):
        return np.zeros_like(arr)
    return (arr - low) / (high - low)


def _build_fbm(
    width: int,
    height: int,
    seed: int,
    generator_name: str,
    octaves: int,
    base_frequency: float,
    persistence: float,
    lacunarity: float,
) -> np.ndarray:
    terrain = np.zeros((height, width), dtype=np.float64)
    amplitude = 1.0
    frequency = base_frequency
    amp_total = 0.0

    if generator_name == "opensimplex":
        OpenSimplex = _import_generator("opensimplex")
        simplex = OpenSimplex(seed=seed)

        ys = np.arange(height, dtype=np.float64)
        xs = np.arange(width, dtype=np.float64)

        for _ in range(octaves):
            sample_x = xs * frequency
            sample_y = ys * frequency

            if hasattr(simplex, "noise2array"):
                layer = simplex.noise2array(sample_x, sample_y)
            else:
                xx, yy = np.meshgrid(sample_x, sample_y)
                layer = np.vectorize(simplex.noise2)(xx, yy)

            terrain += layer * amplitude
            amp_total += amplitude
            amplitude *= persistence
            frequency *= lacunarity

    elif generator_name == "noise":
        pnoise2 = _import_generator("noise")

        for octave in range(octaves):
            layer = np.zeros_like(terrain)
            freq = base_frequency * (lacunarity ** octave)
            amp = persistence ** octave

            for y in range(height):
                fy = y * freq
                for x in range(width):
                    fx = x * freq
                    layer[y, x] = pnoise2(fx, fy, repeatx=width, repeaty=height, base=seed)

            terrain += layer * amp
            amp_total += amp

    else:
        raise ValueError(f"Unknown generator: {generator_name}")

    if amp_total > 0:
        terrain /= amp_total
    return _normalize01(terrain)


def _compress_relief(heightmap: np.ndarray, relief_strength: float) -> np.ndarray:
    center = float(heightmap.mean())
    compressed = center + (heightmap - center) * relief_strength
    return _normalize01(compressed)


def _read_track_points(path: str) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if row[0].strip().startswith("#"):
                continue
            if len(row) < 2:
                raise ValueError(f"Invalid track row: {row}")
            points.append((float(row[0]), float(row[1])))
    if len(points) < 2:
        raise ValueError("Track CSV requires at least 2 points.")
    return points


def _to_pixel_points(
    points: Sequence[Tuple[float, float]],
    width: int,
    height: int,
    coord_space: str,
) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for x, y in points:
        if coord_space == "normalized":
            px = int(round(x * (width - 1)))
            py = int(round(y * (height - 1)))
        else:
            px = int(round(x))
            py = int(round(y))
        px = max(0, min(width - 1, px))
        py = max(0, min(height - 1, py))
        out.append((px, py))
    return out


def _draw_polyline(mask: np.ndarray, points: Sequence[Tuple[int, int]]) -> None:
    def draw_line(x0: int, y0: int, x1: int, y1: int) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        x, y = x0, y0
        while True:
            mask[y, x] = True
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        draw_line(x0, y0, x1, y1)


def _apply_track_flatten(
    heightmap: np.ndarray,
    track_pixels: Sequence[Tuple[int, int]],
    corridor_width_px: float,
    edge_falloff_px: float,
    flatten_strength: float,
) -> np.ndarray:
    gaussian_filter, distance_transform_edt = _require_scipy()
    if distance_transform_edt is None:
        raise RuntimeError(
            "scipy is required for track flattening (distance_transform_edt). "
            "Install with: python3 -m pip install scipy"
        )

    centerline = np.zeros(heightmap.shape, dtype=bool)
    _draw_polyline(centerline, track_pixels)
    if not centerline.any():
        return heightmap

    # Distance field gives smooth control from centerline to edge.
    dist = distance_transform_edt(~centerline)
    half_corridor = max(1.0, corridor_width_px * 0.5)
    fade = max(1.0, edge_falloff_px)

    target = gaussian_filter(heightmap, sigma=max(1.0, corridor_width_px * 0.25))

    inner = dist <= half_corridor
    feather = (dist > half_corridor) & (dist < half_corridor + fade)

    strength = np.zeros_like(heightmap, dtype=np.float64)
    strength[inner] = flatten_strength
    strength[feather] = flatten_strength * (
        1.0 - (dist[feather] - half_corridor) / fade
    )

    out = heightmap * (1.0 - strength) + target * strength
    return _normalize01(out)


def _write_pgm16(path: str, data_01: np.ndarray) -> None:
    data_u16 = np.clip(data_01 * 65535.0, 0, 65535).astype(np.uint16)
    be = data_u16.byteswap()  # PGM binary stores big-endian for 16-bit
    with open(path, "wb") as f:
        f.write(f"P5\n{data_u16.shape[1]} {data_u16.shape[0]}\n65535\n".encode("ascii"))
        f.write(be.tobytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a mostly-flat race terrain heightmap with optional track flattening."
    )
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--generator", choices=["opensimplex", "noise"], default="opensimplex")
    parser.add_argument("--octaves", type=int, default=5)
    parser.add_argument("--base-frequency", type=float, default=0.003)
    parser.add_argument("--persistence", type=float, default=0.5)
    parser.add_argument("--lacunarity", type=float, default=2.0)
    parser.add_argument(
        "--relief-strength",
        type=float,
        default=0.25,
        help="0..1, lower means flatter global terrain",
    )
    parser.add_argument(
        "--smooth-sigma",
        type=float,
        default=2.5,
        help="Gaussian smoothing strength",
    )

    parser.add_argument("--track-csv", type=str, default="")
    parser.add_argument(
        "--track-coord-space",
        choices=["normalized", "pixel"],
        default="normalized",
        help="Track CSV point space",
    )
    parser.add_argument("--corridor-width-px", type=float, default=90.0)
    parser.add_argument("--edge-falloff-px", type=float, default=40.0)
    parser.add_argument("--track-flatten-strength", type=float, default=0.9)

    parser.add_argument("--out-dir", type=str, default="res/terrain")
    parser.add_argument("--name", type=str, default="race_base")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.width <= 1 or args.height <= 1:
        raise ValueError("width/height must be > 1")
    if not (0.0 <= args.relief_strength <= 1.0):
        raise ValueError("relief-strength must be in [0, 1]")
    if not (0.0 <= args.track_flatten_strength <= 1.0):
        raise ValueError("track-flatten-strength must be in [0, 1]")

    os.makedirs(args.out_dir, exist_ok=True)

    t = start_timer("terrain base generation")
    terrain = _build_fbm(
        width=args.width,
        height=args.height,
        seed=args.seed,
        generator_name=args.generator,
        octaves=args.octaves,
        base_frequency=args.base_frequency,
        persistence=args.persistence,
        lacunarity=args.lacunarity,
    )
    end_timer(t)

    gaussian_filter, _ = _require_scipy()

    t = start_timer("global smoothing and flatten")
    terrain = gaussian_filter(terrain, sigma=max(0.01, args.smooth_sigma))
    terrain = _compress_relief(terrain, relief_strength=args.relief_strength)
    end_timer(t)

    track_used = False
    if args.track_csv:
        t = start_timer("track corridor flatten")
        points = _read_track_points(args.track_csv)
        pixels = _to_pixel_points(
            points, args.width, args.height, coord_space=args.track_coord_space
        )
        try:
            terrain = _apply_track_flatten(
                terrain,
                track_pixels=pixels,
                corridor_width_px=args.corridor_width_px,
                edge_falloff_px=args.edge_falloff_px,
                flatten_strength=args.track_flatten_strength,
            )
            track_used = True
            end_timer(t)
        except RuntimeError as exc:
            # Keep generation usable on minimal Python installs; flattening is optional.
            print(f"[terrain] WARN: {exc}")
            print("[terrain] WARN: skipping track flatten (install scipy to enable)")
            end_timer(t)

    t = start_timer("write artifacts")
    base = os.path.join(args.out_dir, args.name)
    npy_path = f"{base}.npy"
    pgm_path = f"{base}.pgm"
    report_path = f"{base}.json"

    np.save(npy_path, terrain.astype(np.float32))
    _write_pgm16(pgm_path, terrain)

    report = {
        "name": args.name,
        "shape": [args.height, args.width],
        "seed": args.seed,
        "generator": args.generator,
        "params": {
            "octaves": args.octaves,
            "base_frequency": args.base_frequency,
            "persistence": args.persistence,
            "lacunarity": args.lacunarity,
            "smooth_sigma": args.smooth_sigma,
            "relief_strength": args.relief_strength,
        },
        "track_flatten": {
            "enabled": track_used,
            "track_csv": args.track_csv,
            "coord_space": args.track_coord_space,
            "corridor_width_px": args.corridor_width_px,
            "edge_falloff_px": args.edge_falloff_px,
            "strength": args.track_flatten_strength,
        },
        "stats": {
            "min": float(terrain.min()),
            "max": float(terrain.max()),
            "mean": float(terrain.mean()),
            "std": float(terrain.std()),
        },
        "artifacts": {
            "npy": npy_path,
            "pgm16": pgm_path,
            "report": report_path,
        },
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=True, indent=2)
    end_timer(t)

    print("[terrain] SUCCESS")
    print(f"[terrain] npy   -> {npy_path}")
    print(f"[terrain] pgm16 -> {pgm_path}")
    print(f"[terrain] json  -> {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[terrain] ERROR: {exc}", file=sys.stderr)
        raise
