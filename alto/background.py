import random
import pygame

from .constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    SKY_PALETTES,
    LAYER_SPEEDS,
    DAY_CYCLE_DURATION,
)


def _lerp_color(c1, c2, t: float):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


class ParallaxBackground:
    def __init__(self, width: int = WINDOW_WIDTH, height: int = WINDOW_HEIGHT) -> None:
        self.width = width
        self.height = height
        self.sky_surface = pygame.Surface((width, height)).convert()

        # Generate ridge shapes once (geometry doesn't change, only color)
        self.layer_ridges = []
        total_width = width * 3
        base_y_ratios = [0.70, 0.76, 0.82, 0.88]
        peak_heights = [height * 0.10, height * 0.12, height * 0.14, height * 0.16]
        roughness_values = [0.5, 0.6, 0.7, 0.8]

        for i, speed in enumerate(LAYER_SPEEDS):
            base_y = int(height * base_y_ratios[i % len(base_y_ratios)])
            peak_h = int(peak_heights[i % len(peak_heights)])
            roughness = roughness_values[i % len(roughness_values)]
            seed = 1337 + i * 101
            ridge_points = self._generate_ridge_points(
                total_width, height, base_y, peak_h, roughness, seed
            )
            self.layer_ridges.append({
                "points": ridge_points,
                "speed": speed,
                "total_width": total_width,
                "total_height": height,
            })

        # Pre-render initial layers
        self.layers = []
        initial_palette = SKY_PALETTES[1]  # Start at "day"
        self._render_sky_gradient(initial_palette["top"], initial_palette["bottom"])
        for i, ridge in enumerate(self.layer_ridges):
            color = initial_palette["layers"][i]
            surf = self._render_ridge_surface(ridge, color)
            self.layers.append({"surface": surf, "speed": ridge["speed"]})

        self.current_palette_colors = {
            "top": initial_palette["top"],
            "bottom": initial_palette["bottom"],
            "layers": list(initial_palette["layers"]),
        }
        self._last_palette_idx = -1

    def update_cycle(self, elapsed_time: float) -> None:
        """Update sky and layer colors based on day/night cycle."""
        n = len(SKY_PALETTES)
        cycle_pos = (elapsed_time % DAY_CYCLE_DURATION) / DAY_CYCLE_DURATION
        total_t = cycle_pos * n
        idx = int(total_t) % n
        frac = total_t - int(total_t)
        next_idx = (idx + 1) % n

        p1 = SKY_PALETTES[idx]
        p2 = SKY_PALETTES[next_idx]

        new_top = _lerp_color(p1["top"], p2["top"], frac)
        new_bottom = _lerp_color(p1["bottom"], p2["bottom"], frac)
        new_layers = [_lerp_color(p1["layers"][i], p2["layers"][i], frac)
                      for i in range(len(LAYER_SPEEDS))]

        # Only re-render if colors changed noticeably (every few frames)
        changed = (new_top != self.current_palette_colors["top"] or
                   new_bottom != self.current_palette_colors["bottom"])
        if changed:
            self.current_palette_colors["top"] = new_top
            self.current_palette_colors["bottom"] = new_bottom
            self.current_palette_colors["layers"] = new_layers
            self._render_sky_gradient(new_top, new_bottom)
            for i, ridge in enumerate(self.layer_ridges):
                self.layers[i]["surface"] = self._render_ridge_surface(ridge, new_layers[i])

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

    def _render_sky_gradient(self, top_color, bottom_color) -> None:
        width, height = self.sky_surface.get_size()
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
            pygame.draw.line(self.sky_surface, (r, g, b), (0, y), (width, y))

    def _generate_ridge_points(self, total_width, total_height, base_y,
                                peak_height, roughness, seed):
        rng = random.Random(seed)
        step = 24
        points = []
        y = base_y
        for x in range(0, total_width + step, step):
            target = base_y - int(peak_height * (0.3 + 0.7 * rng.random()))
            y += int((target - y) * roughness)
            points.append((x, max(0, min(total_height - 1, y))))
        return points

    def _render_ridge_surface(self, ridge, color) -> pygame.Surface:
        total_width = ridge["total_width"]
        total_height = ridge["total_height"]
        points = ridge["points"]
        surf = pygame.Surface((total_width, total_height), pygame.SRCALPHA).convert_alpha()
        polygon = [(0, total_height), (0, points[0][1])] + points + [
            (total_width, points[-1][1]),
            (total_width, total_height),
        ]
        pygame.draw.polygon(surf, color, polygon)
        return surf
