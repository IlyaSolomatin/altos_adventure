import math
import random
from typing import List, Tuple

import pygame

from .constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    TERRAIN_COLOR,
    TERRAIN_BASELINE_RATIO,
    TERRAIN_AMPLITUDE,
    TERRAIN_SEGMENT_WIDTH,
    TERRAIN_ROUGHNESS,
    DOWNHILL_SLOPE_PER_PX,
    HILL_FREQ1,
    HILL_FREQ2,
    HILL_WEIGHT2,
    MICRO_SINE_AMPL,
    MICRO_SINE_FREQ,
)


class Terrain:
    def __init__(self, seed: int = 4242) -> None:
        self.seed = seed
        self.random = random.Random(seed)
        self.segment_width = TERRAIN_SEGMENT_WIDTH
        self.baseline_y = int(WINDOW_HEIGHT * TERRAIN_BASELINE_RATIO)
        self.amplitude = TERRAIN_AMPLITUDE
        self.roughness = TERRAIN_ROUGHNESS
        self.points: List[Tuple[int, int]] = []
        self._drift_origin_x = 0
        self._ensure_points_cover(0, WINDOW_WIDTH * 3)

    def _ensure_points_cover(self, start_x: int, end_x: int) -> None:
        if not self.points:
            self.points = self._generate_ridge(start_x, end_x)
            return
        current_end_x = self.points[-1][0]
        if current_end_x < end_x:
            extra = self._generate_ridge(current_end_x + self.segment_width, end_x)
            self.points.extend(extra)

    def _generate_ridge(self, start_x: int, end_x: int) -> List[Tuple[int, int]]:
        if end_x <= start_x:
            return []
        xs = list(range(start_x, end_x + 1, self.segment_width))
        if not self.points:
            self._drift_origin_x = xs[0]
        return [(x, int(self._height_at(x))) for x in xs]

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        screen_w = screen.get_width()
        start_x = int(camera_x) - screen_w
        end_x = int(camera_x) + screen_w * 2
        self._ensure_points_cover(start_x, end_x)
        if not self.points:
            return
        step_px = 4
        x = start_x
        poly = []
        while x <= end_x:
            y = self._height_at(x)
            poly.append((int(x - camera_x), int(y - camera_y)))
            x += step_px
        if not poly:
            return
        poly = [(poly[0][0], WINDOW_HEIGHT),] + poly + [(poly[-1][0], WINDOW_HEIGHT)]
        pygame.draw.polygon(screen, TERRAIN_COLOR, poly)

    def _hash01(self, i: int) -> float:
        i = (i ^ (i >> 16)) & 0xFFFFFFFF
        i = (i * 2246822519 + 1013904223 + self.seed * 374761393) & 0xFFFFFFFF
        i ^= (i >> 13)
        i = (i * 3266489917) & 0xFFFFFFFF
        i ^= (i >> 16)
        return i / 0xFFFFFFFF

    def _value_noise(self, x: float) -> float:
        xi = math.floor(x)
        xf = x - xi
        a = self._hash01(xi) * 2.0 - 1.0
        b = self._hash01(xi + 1) * 2.0 - 1.0
        t = xf * xf * (3 - 2 * xf)
        return a + (b - a) * t

    def _fbm(self, x: float, octaves: int = 4) -> float:
        total = 0.0
        amp = 1.0
        freq = 1.0
        max_amp = 0.0
        for _ in range(octaves):
            total += self._value_noise(x * freq) * amp
            max_amp += amp
            amp *= 0.5
            freq *= 2.0
        return total / max_amp if max_amp > 0 else 0.0

    def sample_height(self, world_x: float) -> float:
        if not self.points:
            return self.baseline_y
        # Ensure coverage around the query point
        self._ensure_points_cover(int(world_x) - WINDOW_WIDTH, int(world_x) + WINDOW_WIDTH)
        # Find segment indices
        idx = 0
        while idx + 1 < len(self.points) and self.points[idx + 1][0] < world_x:
            idx += 1
        idx = max(0, min(len(self.points) - 2, idx))
        return self._height_at(world_x)

    def sample_slope(self, world_x: float) -> float:
        if not self.points:
            return 0.0
        self._ensure_points_cover(int(world_x) - WINDOW_WIDTH, int(world_x) + WINDOW_WIDTH)
        idx = 0
        while idx + 1 < len(self.points) and self.points[idx + 1][0] < world_x:
            idx += 1
        idx = max(0, min(len(self.points) - 2, idx))
        return self._slope_at(world_x)

    def _height_at(self, x: float) -> float:
        drift = (x - self._drift_origin_x) * DOWNHILL_SLOPE_PER_PX
        s1 = math.sin(x * HILL_FREQ1)
        s2 = math.sin(x * HILL_FREQ2)
        base = s1 + HILL_WEIGHT2 * s2
        micro = math.sin(x * MICRO_SINE_FREQ)
        return self.baseline_y + drift + TERRAIN_AMPLITUDE * base + MICRO_SINE_AMPL * micro

    def _slope_at(self, x: float) -> float:
        ds1 = math.cos(x * HILL_FREQ1) * HILL_FREQ1
        ds2 = math.cos(x * HILL_FREQ2) * HILL_FREQ2 * HILL_WEIGHT2
        dbase_dx = TERRAIN_AMPLITUDE * (ds1 + ds2)
        dmicro_dx = math.cos(x * MICRO_SINE_FREQ) * MICRO_SINE_FREQ * MICRO_SINE_AMPL
        return dbase_dx + dmicro_dx + DOWNHILL_SLOPE_PER_PX


