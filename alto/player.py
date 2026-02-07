import math
from collections import deque
from typing import List, Tuple

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
    AUTO_LEVEL_FACTOR,
    CRASH_ANGLE_TOLERANCE,
    BACKFLIP_SCORE_BONUS,
    COMBO_MULTIPLIER_BONUS,
    POPUP_DURATION,
    INVINCIBILITY_DURATION,
    INVINCIBILITY_BLINK_START,
    INVINCIBILITY_GLOW_COLOR,
)


class ScorePopup:
    def __init__(self, text: str, x: float, y: float) -> None:
        self.text = text
        self.x = x
        self.y = y
        self.timer = POPUP_DURATION

    def update(self, dt: float) -> bool:
        self.timer -= dt
        self.y -= 30 * dt
        return self.timer > 0

    @property
    def alpha(self) -> int:
        return max(0, min(255, int(255 * (self.timer / POPUP_DURATION))))


def _crossed_ccw(prev: float, curr: float, target: float) -> bool:
    """Return True if *target* was crossed going counter-clockwise from *prev* to *curr*."""
    delta = (curr - prev) % 360.0
    if delta == 0 or delta >= 180.0:
        return False          # no movement or moved clockwise
    return 0 < (target - prev) % 360.0 <= delta


class Player:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.was_on_ground = False
        self.angle_deg = 0.0
        self.crashed = False

        # Backflip tracking
        self.flip_count = 0
        self.prev_head_ref_angle: float | None = None
        self.flip_waiting_for_vertical = False
        self.pending_tricks: List[str] = []
        self.combo = 0
        self.did_trick_this_air = False
        self.popups: List[ScorePopup] = []
        self.flip_score = 0

        # Scarf trail positions
        self.trail: deque = deque(maxlen=8)

        # Landing detection
        self.just_landed = False

        # Post-trick invincibility
        self.invincible_timer = 0.0

    def reset(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.was_on_ground = False
        self.angle_deg = 0.0
        self.crashed = False
        self.flip_count = 0
        self.prev_head_ref_angle = None
        self.flip_waiting_for_vertical = False
        self.pending_tricks.clear()
        self.combo = 0
        self.did_trick_this_air = False
        self.popups.clear()
        self.flip_score = 0
        self.trail.clear()
        self.just_landed = False
        self.invincible_timer = 0.0

    def update(self, dt: float, button_down: bool, button_pressed: bool,
               terrain_sample, terrain_slope) -> None:
        if self.crashed:
            return

        self.just_landed = False

        slope = terrain_slope(self.x)
        self.vx += (SLOPE_ACCEL * slope) * dt
        if abs(self.vx) > MAX_SPEED:
            self.vx = MAX_SPEED if self.vx > 0 else -MAX_SPEED
        if self.vx < MIN_FORWARD_SPEED:
            self.vx = MIN_FORWARD_SPEED

        if self.on_ground:
            # --- Grounded: follow terrain directly, no gravity ---
            if button_pressed:
                self.jump()
            else:
                self.x += self.vx * dt
                ground_y = terrain_sample(self.x) - PLAYER_RADIUS
                # If terrain drops away significantly, become airborne
                if ground_y > self.y + 4:
                    self.on_ground = False
                    # Launch with slope-following velocity
                    self.vy = slope * self.vx
                    self.y += self.vy * dt
                else:
                    self.y = ground_y
                    self.vy = 0.0
        else:
            # --- Airborne: apply gravity ---
            self.vy += GRAVITY * dt
            self.x += self.vx * dt
            self.y += self.vy * dt

            ground_y = terrain_sample(self.x) - PLAYER_RADIUS
            if self.y >= ground_y:
                self.y = ground_y
                self.vy = 0.0
                self.on_ground = True
                self.just_landed = True

                # Check crash on bad landing
                landing_slope = terrain_slope(self.x)
                terrain_angle = math.degrees(math.atan2(landing_slope, 1.0))
                angle_diff = (self.angle_deg - terrain_angle) % 360.0
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                if angle_diff > CRASH_ANGLE_TOLERANCE:
                    self.crashed = True
                    self.pending_tricks.clear()
                    return

                # Award backflip score on landing
                if self.flip_count > 0:
                    self.combo += self.flip_count
                    bonus = self.flip_count * BACKFLIP_SCORE_BONUS
                    if self.combo > 1:
                        bonus += (self.combo - 1) * COMBO_MULTIPLIER_BONUS
                    self.flip_score += bonus
                    label = f"+{bonus}"
                    if self.combo > 1:
                        label = f"x{self.combo} Combo  {label}"
                    self.popups.append(ScorePopup(label, self.x, self.y - 40))
                    self.invincible_timer = INVINCIBILITY_DURATION
                elif not self.did_trick_this_air:
                    self.combo = 0

                self.pending_tricks.clear()
                self.flip_count = 0
                self.prev_head_ref_angle = None
                self.flip_waiting_for_vertical = False
                self.did_trick_this_air = False

        if not self.on_ground and button_down:
            rotation_this_frame = ROTATE_SPEED_DEG * dt
            self.angle_deg = (self.angle_deg - rotation_this_frame) % 360.0
        elif not self.on_ground:
            # Auto-level: if tilted backward, slowly rotate clockwise toward vertical
            normalized = self.angle_deg % 360.0
            if normalized > 180.0:
                backward_tilt = 360.0 - normalized
                correction = AUTO_LEVEL_FACTOR * backward_tilt * dt
                self.angle_deg = (self.angle_deg + correction) % 360.0
                # Clamp to not overshoot past vertical
                new_norm = self.angle_deg % 360.0
                if new_norm <= 180.0:
                    self.angle_deg = 0.0

        # --- Backflip detection via head angle thresholds ---
        if not self.on_ground:
            head_ref = (90.0 - self.angle_deg) % 360.0
            if self.prev_head_ref_angle is not None:
                if not self.flip_waiting_for_vertical:
                    if _crossed_ccw(self.prev_head_ref_angle, head_ref, 300.0):
                        self.flip_count += 1
                        self.flip_waiting_for_vertical = True
                        self.did_trick_this_air = True
                        trick = f"Backflip x{self.flip_count}" if self.flip_count > 1 else "Backflip"
                        self.pending_tricks.append(trick)
                else:
                    if _crossed_ccw(self.prev_head_ref_angle, head_ref, 90.0):
                        self.flip_waiting_for_vertical = False
            self.prev_head_ref_angle = head_ref

        if self.on_ground:
            ground_slope = terrain_slope(self.x)
            self.angle_deg = math.degrees(math.atan2(ground_slope, 1.0))

        # Decrement invincibility timer
        if self.invincible_timer > 0:
            self.invincible_timer = max(0.0, self.invincible_timer - dt)

        # Update scarf trail
        self.trail.appendleft((self.x, self.y))

        # Update popups
        self.popups = [p for p in self.popups if p.update(dt)]

    @property
    def is_invincible(self) -> bool:
        return self.invincible_timer > 0

    @property
    def invincible_blinking(self) -> bool:
        return 0 < self.invincible_timer <= INVINCIBILITY_BLINK_START

    def jump(self) -> None:
        if self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - PLAYER_RADIUS),
            int(self.y - PLAYER_RADIUS),
            PLAYER_RADIUS * 2,
            PLAYER_RADIUS * 2,
        )

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        cx = int(self.x - camera_x)
        cy = int(self.y - camera_y)
        rad = math.radians(self.angle_deg)

        # --- Scarf ---
        if len(self.trail) > 1:
            scarf_anchor_dx = -6 * math.cos(rad) - (-4) * math.sin(rad)
            scarf_anchor_dy = -6 * math.sin(rad) + (-4) * math.cos(rad)
            prev_x = cx + scarf_anchor_dx
            prev_y = cy + scarf_anchor_dy
            scarf_colors = [(200, 50, 50), (180, 40, 40), (160, 30, 30), (140, 25, 25),
                            (120, 20, 20), (100, 15, 15), (80, 10, 10)]
            for i, (tx, ty) in enumerate(list(self.trail)[1:]):
                if i >= len(scarf_colors):
                    break
                sx = tx - camera_x + scarf_anchor_dx * 0.3
                sy = ty - camera_y + scarf_anchor_dy * 0.3
                width = max(1, 4 - i // 2)
                pygame.draw.line(screen, scarf_colors[i],
                                 (int(prev_x), int(prev_y)),
                                 (int(sx), int(sy)), width)
                prev_x, prev_y = sx, sy

        # --- Invincibility glow ---
        if self.is_invincible:
            show_glow = True
            if self.invincible_blinking:
                # Fast blink at ~8Hz using sin wave
                show_glow = math.sin(self.invincible_timer * 16 * math.pi) > 0
            if show_glow:
                # Pulsing alpha via sin wave breathing effect
                pulse = (math.sin(self.invincible_timer * 4 * math.pi) + 1) / 2
                alpha = int(60 + 60 * pulse)
                glow_radius = 20
                glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    glow_surf,
                    (*INVINCIBILITY_GLOW_COLOR, alpha),
                    (glow_radius, glow_radius),
                    glow_radius,
                )
                screen.blit(glow_surf, (cx - glow_radius, cy - glow_radius))

        # --- Snowboarder silhouette ---
        # Body points (relative to center, pre-rotation)
        body_points = [
            (0, -12),   # head top
            (4, -8),    # head right
            (5, -4),    # shoulder right
            (3, 2),     # torso right
            (6, 4),     # hip right
            (4, 8),     # knee right
            (-4, 8),    # knee left
            (-6, 4),    # hip left
            (-3, 2),    # torso left
            (-5, -4),   # shoulder left
            (-4, -8),   # head left
        ]

        # Board points
        board_points = [
            (-10, 10),
            (10, 10),
            (12, 8),
            (-12, 8),
        ]

        def rotate_point(px: float, py: float) -> Tuple[int, int]:
            rx = px * math.cos(rad) - py * math.sin(rad)
            ry = px * math.sin(rad) + py * math.cos(rad)
            return (int(cx + rx), int(cy + ry))

        # Draw board
        rotated_board = [rotate_point(px, py) for px, py in board_points]
        pygame.draw.polygon(screen, (60, 55, 50), rotated_board)

        # Draw body
        rotated_body = [rotate_point(px, py) for px, py in body_points]
        pygame.draw.polygon(screen, PLAYER_COLOR, rotated_body)

        # Draw head circle
        head_center = rotate_point(0, -10)
        pygame.draw.circle(screen, PLAYER_COLOR, head_center, 5)

    def draw_popups(self, screen: pygame.Surface, camera_x: float, camera_y: float,
                    font: pygame.font.Font) -> None:
        for popup in self.popups:
            alpha = popup.alpha
            text_surf = font.render(popup.text, True, (255, 255, 255))
            text_surf.set_alpha(alpha)
            sx = int(popup.x - camera_x) - text_surf.get_width() // 2
            sy = int(popup.y - camera_y)
            screen.blit(text_surf, (sx, sy))
