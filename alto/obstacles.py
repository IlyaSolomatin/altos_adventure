import random
from typing import List, Optional, Tuple

import pygame

from .constants import (
    WINDOW_WIDTH,
    OBSTACLE_MIN_SPACING,
    OBSTACLE_MAX_SPACING,
    ROCK_WIDTH,
    ROCK_HEIGHT,
    ROCK_COLOR,
)


class Rock:
    def __init__(self, x: float, ground_y: float) -> None:
        self.x = x
        self.y = ground_y - ROCK_HEIGHT
        self.width = ROCK_WIDTH
        self.height = ROCK_HEIGHT

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.width // 2), int(self.y),
                           self.width, self.height)

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        # Draw as a triangular rock silhouette
        points = [
            (sx - self.width // 2, sy + self.height),
            (sx - self.width // 3, sy + 2),
            (sx + 2, sy),
            (sx + self.width // 3, sy + 4),
            (sx + self.width // 2, sy + self.height),
        ]
        pygame.draw.polygon(screen, ROCK_COLOR, points)


class ObstacleManager:
    def __init__(self, terrain_sample, seed: int = 9999) -> None:
        self.terrain_sample = terrain_sample
        self.rng = random.Random(seed)
        self.rocks: List[Rock] = []
        self.next_rock_x = 800.0  # first rock spawns a bit ahead

    def update(self, camera_x: float) -> None:
        # Spawn rocks ahead of camera
        spawn_edge = camera_x + WINDOW_WIDTH * 2
        while self.next_rock_x < spawn_edge:
            ground_y = self.terrain_sample(self.next_rock_x)
            self.rocks.append(Rock(self.next_rock_x, ground_y))
            spacing = self.rng.randint(OBSTACLE_MIN_SPACING, OBSTACLE_MAX_SPACING)
            self.next_rock_x += spacing

        # Remove rocks far behind camera
        self.rocks = [r for r in self.rocks if r.x > camera_x - WINDOW_WIDTH]

    def check_collision(self, player_rect: pygame.Rect,
                        invincible: bool = False
                        ) -> Tuple[Optional[str], Optional[Tuple[float, float]]]:
        for rock in self.rocks:
            if player_rect.colliderect(rock.get_rect()):
                if invincible:
                    pos = (rock.x, rock.y)
                    self.rocks.remove(rock)
                    return ("smashed", pos)
                return ("crashed", None)
        return (None, None)

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        for rock in self.rocks:
            rock.draw(screen, camera_x, camera_y)

    def reset(self) -> None:
        self.rocks.clear()
        self.next_rock_x = 800.0
