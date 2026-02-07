import math
import random
from typing import List

import pygame

from .constants import (
    PARTICLE_LIFETIME,
    PARTICLE_SPEED,
    PARTICLE_COUNT_PER_FRAME,
    PARTICLE_LANDING_BURST,
    PARTICLE_COLOR,
    PARTICLE_MAX_RADIUS,
    ROCK_COLOR,
)


class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = PARTICLE_LIFETIME
        self.max_life = PARTICLE_LIFETIME

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    @property
    def alpha(self) -> int:
        return max(0, min(255, int(255 * (self.life / self.max_life))))

    @property
    def radius(self) -> float:
        return max(0.5, PARTICLE_MAX_RADIUS * (self.life / self.max_life))


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: List[Particle] = []

    def emit_trail(self, x: float, y: float, player_vx: float) -> None:
        for _ in range(PARTICLE_COUNT_PER_FRAME):
            vx = -player_vx * 0.1 + random.uniform(-15, 15)
            vy = random.uniform(-PARTICLE_SPEED, -PARTICLE_SPEED * 0.3)
            px = x + random.uniform(-8, -2)
            py = y + random.uniform(-2, 2)
            self.particles.append(Particle(px, py, vx, vy))

    def emit_landing_burst(self, x: float, y: float) -> None:
        for _ in range(PARTICLE_LANDING_BURST):
            vx = random.uniform(-PARTICLE_SPEED * 2, PARTICLE_SPEED * 2)
            vy = random.uniform(-PARTICLE_SPEED * 2, -PARTICLE_SPEED * 0.5)
            self.particles.append(Particle(x, y, vx, vy))

    def emit_rock_smash(self, x: float, y: float) -> None:
        count = 18
        for _ in range(count):
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(PARTICLE_SPEED * 1.5, PARTICLE_SPEED * 4)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle) - PARTICLE_SPEED
            p = Particle(x + random.uniform(-6, 6), y + random.uniform(-6, 6), vx, vy)
            p.life = PARTICLE_LIFETIME * 1.6
            p.max_life = p.life
            p._color = ROCK_COLOR
            self.particles.append(p)

    def update(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        for p in self.particles:
            sx = int(p.x - camera_x)
            sy = int(p.y - camera_y)
            r = max(1, int(p.radius))
            alpha = p.alpha
            if alpha > 20:
                base = getattr(p, '_color', PARTICLE_COLOR)
                color = (
                    min(255, base[0]),
                    min(255, base[1]),
                    min(255, base[2]),
                )
                # For performance, draw without alpha for most particles
                if alpha > 180:
                    pygame.draw.circle(screen, color, (sx, sy), r)
                else:
                    # Use a small surface for alpha blending
                    surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (*color, alpha), (r, r), r)
                    screen.blit(surf, (sx - r, sy - r))

    def reset(self) -> None:
        self.particles.clear()
