import math
import random
from typing import List

import pygame

from .constants import (
    WINDOW_WIDTH,
    COIN_RADIUS,
    COIN_COLOR,
    COIN_OUTLINE_COLOR,
    COIN_SCORE,
    COIN_GROUP_MIN_SPACING,
    COIN_GROUP_MAX_SPACING,
    COIN_ARC_HEIGHT,
    COIN_ARC_COUNT_MIN,
    COIN_ARC_COUNT_MAX,
    PLAYER_RADIUS,
)


class Coin:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.collected = False
        self.bob_offset = random.random() * math.pi * 2

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float,
             time: float) -> None:
        if self.collected:
            return
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y + math.sin(time * 3 + self.bob_offset) * 3)
        pygame.draw.circle(screen, COIN_COLOR, (sx, sy), COIN_RADIUS)
        pygame.draw.circle(screen, COIN_OUTLINE_COLOR, (sx, sy), COIN_RADIUS, 2)


class CoinManager:
    def __init__(self, terrain_sample, seed: int = 7777) -> None:
        self.terrain_sample = terrain_sample
        self.rng = random.Random(seed)
        self.coins: List[Coin] = []
        self.next_group_x = 500.0
        self.coins_collected = 0
        self.time = 0.0

    def update(self, dt: float, camera_x: float, player_x: float,
               player_y: float) -> int:
        self.time += dt
        score_gained = 0

        # Spawn coin groups ahead of camera
        spawn_edge = camera_x + WINDOW_WIDTH * 2
        while self.next_group_x < spawn_edge:
            count = self.rng.randint(COIN_ARC_COUNT_MIN, COIN_ARC_COUNT_MAX)
            ground_y = self.terrain_sample(self.next_group_x)
            spread = count * 30
            for i in range(count):
                cx = self.next_group_x + (i - count / 2) * 30
                # Arc shape
                t = (i / max(1, count - 1)) * math.pi
                arc_y = ground_y - 40 - COIN_ARC_HEIGHT * math.sin(t)
                self.coins.append(Coin(cx, arc_y))
            spacing = self.rng.randint(COIN_GROUP_MIN_SPACING, COIN_GROUP_MAX_SPACING)
            self.next_group_x += spacing + spread

        # Check collection
        collect_dist = PLAYER_RADIUS + COIN_RADIUS + 4
        for coin in self.coins:
            if coin.collected:
                continue
            dx = player_x - coin.x
            dy = player_y - coin.y
            if dx * dx + dy * dy < collect_dist * collect_dist:
                coin.collected = True
                self.coins_collected += 1
                score_gained += COIN_SCORE

        # Remove coins far behind
        self.coins = [c for c in self.coins
                      if not c.collected and c.x > camera_x - WINDOW_WIDTH]

        return score_gained

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        for coin in self.coins:
            coin.draw(screen, camera_x, camera_y, self.time)

    def reset(self) -> None:
        self.coins.clear()
        self.next_group_x = 500.0
        self.coins_collected = 0
        self.time = 0.0
