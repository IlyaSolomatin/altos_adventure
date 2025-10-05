import random
import pygame

from .constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    SKY_TOP,
    SKY_BOTTOM,
    LAYER_SPEEDS,
    LAYER_COLORS,
)


class ParallaxBackground:
    def __init__(self, width: int = WINDOW_WIDTH, height: int = WINDOW_HEIGHT) -> None:
        self.width = width
        self.height = height
        self.sky_surface = pygame.Surface((width, height)).convert()
        self._render_vertical_gradient(self.sky_surface, SKY_TOP, SKY_BOTTOM)

        self.layers = []
        total_width = width * 3
        base_y_ratios = [0.70, 0.76, 0.82, 0.88]
        peak_heights = [height * 0.10, height * 0.12, height * 0.14, height * 0.16]
        roughness_values = [0.5, 0.6, 0.7, 0.8]

        for i, speed in enumerate(LAYER_SPEEDS):
            color = LAYER_COLORS[i % len(LAYER_COLORS)]
            base_y = int(height * base_y_ratios[i % len(base_y_ratios)])
            peak_h = int(peak_heights[i % len(peak_heights)])
            roughness = roughness_values[i % len(roughness_values)]
            seed = 1337 + i * 101
            layer_surface = self._generate_ridge_surface(
                total_width, height, base_y, color, peak_h, roughness, seed
            )
            self.layers.append({"surface": layer_surface, "speed": speed})

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        screen.blit(self.sky_surface, (0, 0))
        for layer in self.layers:
            surf = layer["surface"]
            speed = layer["speed"]
            w = surf.get_width()
            offset = -int(camera_x * speed) % w
            screen.blit(surf, (offset, 0))
            if offset > 0:
                screen.blit(surf, (offset - w, 0))
            if offset + w < self.width:
                screen.blit(surf, (offset + w, 0))

    def _render_vertical_gradient(self, target: pygame.Surface, top_color, bottom_color) -> None:
        width, height = target.get_size()
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
            pygame.draw.line(target, (r, g, b), (0, y), (width, y))

    def _generate_ridge_surface(
        self,
        total_width: int,
        total_height: int,
        base_y: int,
        color,
        peak_height: int,
        roughness: float,
        seed: int,
    ) -> pygame.Surface:
        surf = pygame.Surface((total_width, total_height), pygame.SRCALPHA).convert_alpha()
        rng = random.Random(seed)
        step = 24
        points = []
        y = base_y
        for x in range(0, total_width + step, step):
            target = base_y - int(peak_height * (0.3 + 0.7 * rng.random()))
            y += int((target - y) * roughness)
            points.append((x, max(0, min(total_height - 1, y))))
        polygon = [(0, total_height), (0, points[0][1])] + points + [
            (total_width, points[-1][1]),
            (total_width, total_height),
        ]
        pygame.draw.polygon(surf, color, polygon)
        return surf


