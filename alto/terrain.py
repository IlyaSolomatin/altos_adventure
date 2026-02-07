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
    RAMP_MIN_SPACING,
    RAMP_MAX_SPACING,
    RAMP_WIDTH,
    RAMP_HEIGHT,
)


class Ramp:
    def __init__(self, x: float, width: float, height: float) -> None:
        self.x = x
        self.width = width
        self.height = height

    def offset_at(self, world_x: float) -> float:
        """Return the height offset added by this ramp at world_x."""
        dx = world_x - self.x
        if dx < 0 or dx > self.width:
            return 0.0
        t = dx / self.width
        # Long gentle upslope (80%), short steep backside (20%)
        peak_t = 0.8
        if t <= peak_t:
            s = t / peak_t
            smooth = s * s * (3.0 - 2.0 * s)
            return -self.height * smooth
        else:
            s = (t - peak_t) / (1.0 - peak_t)
            smooth = s * s * (3.0 - 2.0 * s)
            return -self.height * (1.0 - smooth)

    def slope_at(self, world_x: float) -> float:
        """Return the slope contribution of this ramp."""
        dx = world_x - self.x
        if dx < 0 or dx > self.width:
            return 0.0
        t = dx / self.width
        peak_t = 0.8
        if t <= peak_t:
            s = t / peak_t
            return -self.height * 6.0 * s * (1.0 - s) / (peak_t * self.width)
        else:
            s = (t - peak_t) / (1.0 - peak_t)
            return self.height * 6.0 * s * (1.0 - s) / ((1.0 - peak_t) * self.width)


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

        # Ramps
        self.ramp_rng = random.Random(seed + 100)
        self.ramps: List[Ramp] = []
        self.next_ramp_x = 1500.0

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

    def update_ramps(self, camera_x: float) -> None:
        """Spawn ramps ahead of camera and remove those behind."""
        spawn_edge = camera_x + WINDOW_WIDTH * 3
        while self.next_ramp_x < spawn_edge:
            width = RAMP_WIDTH + self.ramp_rng.uniform(-80, 120)
            height = RAMP_HEIGHT + self.ramp_rng.uniform(-15, 20)
            self.ramps.append(Ramp(self.next_ramp_x, width, height))
            spacing = self.ramp_rng.uniform(RAMP_MIN_SPACING, RAMP_MAX_SPACING)
            self.next_ramp_x += spacing
        self.ramps = [r for r in self.ramps
                      if r.x + r.width > camera_x - WINDOW_WIDTH]

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
            y = self.sample_height(x)
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
        self._ensure_points_cover(int(world_x) - WINDOW_WIDTH, int(world_x) + WINDOW_WIDTH)
        h = self._height_at(world_x)
        # Add ramp offsets
        for ramp in self.ramps:
            h += ramp.offset_at(world_x)
        return h

    def sample_slope(self, world_x: float) -> float:
        if not self.points:
            return 0.0
        self._ensure_points_cover(int(world_x) - WINDOW_WIDTH, int(world_x) + WINDOW_WIDTH)
        s = self._slope_at(world_x)
        for ramp in self.ramps:
            s += ramp.slope_at(world_x)
        return s

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

    def reset(self) -> None:
        self.points.clear()
        self.ramps.clear()
        self.next_ramp_x = 1500.0
        self._ensure_points_cover(0, WINDOW_WIDTH * 3)
