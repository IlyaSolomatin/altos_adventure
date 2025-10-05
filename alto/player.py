import math
import pygame

from .constants import (
    PLAYER_COLOR,
    PLAYER_RADIUS,
    GRAVITY,
    JUMP_SPEED,
    MAX_SPEED,
    MIN_FORWARD_SPEED,
    SLOPE_ACCEL,
    ROTATE_SPEED_DEG,
)


class Player:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.angle_deg = 0.0

    def update(self, dt: float, button_down: bool, button_pressed: bool, terrain_sample, terrain_slope) -> None:
        slope = terrain_slope(self.x)
        self.vx += (SLOPE_ACCEL * slope) * dt
        if abs(self.vx) > MAX_SPEED:
            self.vx = MAX_SPEED if self.vx > 0 else -MAX_SPEED
        if self.vx < MIN_FORWARD_SPEED:
            self.vx = MIN_FORWARD_SPEED

        self.vy += GRAVITY * dt

        self.x += self.vx * dt
        self.y += self.vy * dt

        ground_y = terrain_sample(self.x) - PLAYER_RADIUS
        if self.y >= ground_y:
            self.y = ground_y
            self.vy = 0.0
            self.on_ground = True
        else:
            self.on_ground = False

        if self.on_ground and button_pressed:
            self.jump()
        if not self.on_ground and button_down:
            self.angle_deg = (self.angle_deg + ROTATE_SPEED_DEG * dt) % 360.0
        if self.on_ground:
            self.angle_deg = 0.0

    def jump(self) -> None:
        if self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        center = (int(self.x - camera_x), int(self.y - camera_y))
        pygame.draw.circle(screen, PLAYER_COLOR, center, PLAYER_RADIUS)
        end_len = PLAYER_RADIUS + 8
        rad = math.radians(self.angle_deg - 90)
        end = (int(center[0] + end_len * math.cos(rad)), int(center[1] + end_len * math.sin(rad)))
        pygame.draw.line(screen, PLAYER_COLOR, center, end, 3)


