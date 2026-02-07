import pygame

from .constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    FPS,
    BACKGROUND_COLOR,
    BASE_SCROLL_SPEED,
    CAMERA_LERP,
    HUD_FONT_SIZE,
    COIN_COLOR,
    COIN_OUTLINE_COLOR,
    COIN_ICON_RADIUS,
    COIN_SCORE,
    ROCK_SMASH_SCORE,
)
from .camera import Camera
from .background import ParallaxBackground
from .terrain import Terrain
from .player import Player, ScorePopup
from .obstacles import ObstacleManager
from .collectibles import CoinManager
from .particles import ParticleSystem

STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2


def run_game() -> None:
    pygame.init()
    try:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        clock = pygame.time.Clock()
        running = True

        font = pygame.font.SysFont(None, HUD_FONT_SIZE)
        title_font = pygame.font.SysFont(None, 64)
        subtitle_font = pygame.font.SysFont(None, 32)
        popup_font = pygame.font.SysFont(None, 30)

        # --- Initialize game objects ---
        camera = Camera(BASE_SCROLL_SPEED)
        background = ParallaxBackground(WINDOW_WIDTH, WINDOW_HEIGHT)
        terrain = Terrain()
        player = Player(100.0, WINDOW_HEIGHT * 0.4)
        obstacles = ObstacleManager(terrain.sample_height)
        coins = CoinManager(terrain.sample_height)
        particles = ParticleSystem()

        distance = 0.0
        score = 0
        elapsed_time = 0.0
        state = STATE_START

        # Overlay surface for semi-transparent screens
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)

        def reset_game() -> None:
            nonlocal distance, score, elapsed_time
            camera.x = 0.0
            camera.y = 0.0
            terrain.reset()
            player.reset(100.0, WINDOW_HEIGHT * 0.4)
            obstacles.reset()
            coins.reset()
            particles.reset()
            distance = 0.0
            score = 0
            elapsed_time = 0.0

        while running:
            dt = clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # Cap dt to prevent physics explosion

            button_pressed = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    button_pressed = True
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    button_pressed = True

            # Check held keys for rotation
            keys = pygame.key.get_pressed()
            mouse = pygame.mouse.get_pressed()
            button_down = (keys[pygame.K_SPACE] or keys[pygame.K_UP]
                           or keys[pygame.K_w] or mouse[0])

            # --- State transitions ---
            if state == STATE_START:
                if button_pressed:
                    reset_game()
                    state = STATE_PLAYING

            elif state == STATE_GAME_OVER:
                if button_pressed:
                    reset_game()
                    state = STATE_PLAYING

            # --- Update ---
            if state == STATE_PLAYING:
                elapsed_time += dt

                player.update(dt, button_down, button_pressed,
                              terrain.sample_height, terrain.sample_slope)

                # Check obstacle collision
                if not player.crashed:
                    obstacles.update(camera.x)
                    result, rock_pos = obstacles.check_collision(
                        player.get_rect(), player.is_invincible
                    )
                    if result == "crashed":
                        player.crashed = True
                    elif result == "smashed" and rock_pos is not None:
                        score += ROCK_SMASH_SCORE
                        player.popups.append(
                            ScorePopup(f"Rock Smash! +{ROCK_SMASH_SCORE}",
                                       rock_pos[0], rock_pos[1])
                        )
                        particles.emit_rock_smash(rock_pos[0], rock_pos[1])

                if player.crashed:
                    state = STATE_GAME_OVER

                camera_target_x = max(camera.x + BASE_SCROLL_SPEED * dt,
                                      player.x - WINDOW_WIDTH * 0.3)
                target_y = player.y - WINDOW_HEIGHT * 0.6
                camera.update(dt, camera_target_x, CAMERA_LERP, target_y, CAMERA_LERP)

                distance += max(0.0, player.vx) * dt

                # Coin collection
                coin_score = coins.update(dt, camera.x, player.x, player.y)
                score += coin_score

                # Backflip score
                score += player.flip_score
                player.flip_score = 0

                # Distance score (1 point per meter)
                score = max(score, int(distance / 10))

                # Terrain ramps
                terrain.update_ramps(camera.x)

                # Day/night cycle
                background.update_cycle(elapsed_time)

                # Particles
                if player.on_ground and not player.crashed:
                    particles.emit_trail(player.x, player.y + 8, player.vx)
                if player.just_landed and not player.crashed:
                    particles.emit_landing_burst(player.x, player.y + 8)
                particles.update(dt)

            # --- Draw ---
            screen.fill(BACKGROUND_COLOR)
            background.draw(screen, camera.x)
            terrain.draw(screen, camera.x, camera.y)
            obstacles.draw(screen, camera.x, camera.y)
            coins.draw(screen, camera.x, camera.y)
            particles.draw(screen, camera.x, camera.y)
            player.draw(screen, camera.x, camera.y)
            player.draw_popups(screen, camera.x, camera.y, popup_font)

            # --- HUD ---
            _draw_hud(screen, font, distance, score, coins.coins_collected)
            if player.pending_tricks:
                _draw_trick_list(screen, font, player.pending_tricks)

            # --- Overlays ---
            if state == STATE_START:
                _draw_start_screen(screen, overlay, title_font, subtitle_font)
            elif state == STATE_GAME_OVER:
                _draw_game_over(screen, overlay, title_font, subtitle_font,
                                font, distance, score, coins.coins_collected)

            pygame.display.flip()
    finally:
        pygame.quit()


def _draw_hud(screen: pygame.Surface, font: pygame.font.Font,
              distance: float, score: int, coins_collected: int) -> None:
    # Distance centered at top
    dist_text = font.render(f"{distance / 10:.0f} m", True, (255, 255, 255))
    dist_text.set_alpha(210)
    screen.blit(dist_text, (WINDOW_WIDTH // 2 - dist_text.get_width() // 2, 16))

    # Score top-right
    score_text = font.render(f"{score}", True, (255, 255, 255))
    score_text.set_alpha(210)
    screen.blit(score_text, (WINDOW_WIDTH - score_text.get_width() - 20, 16))

    # Coin count top-left with icon
    coin_x = 20
    coin_y = 18
    pygame.draw.circle(screen, COIN_COLOR, (coin_x + COIN_ICON_RADIUS,
                                             coin_y + COIN_ICON_RADIUS),
                       COIN_ICON_RADIUS)
    pygame.draw.circle(screen, COIN_OUTLINE_COLOR, (coin_x + COIN_ICON_RADIUS,
                                                     coin_y + COIN_ICON_RADIUS),
                       COIN_ICON_RADIUS, 1)
    coin_text = font.render(f" {coins_collected}", True, (255, 255, 255))
    coin_text.set_alpha(210)
    screen.blit(coin_text, (coin_x + COIN_ICON_RADIUS * 2 + 4, coin_y - 2))


def _draw_trick_list(screen: pygame.Surface, font: pygame.font.Font,
                     tricks: list) -> None:
    x = WINDOW_WIDTH - 20
    y = 48
    for trick in tricks:
        text_surf = font.render(trick, True, (255, 255, 255))
        text_surf.set_alpha(230)
        screen.blit(text_surf, (x - text_surf.get_width(), y))
        y += text_surf.get_height() + 4


def _draw_start_screen(screen: pygame.Surface, overlay: pygame.Surface,
                       title_font: pygame.font.Font,
                       subtitle_font: pygame.font.Font) -> None:
    overlay.fill((0, 0, 0, 100))
    screen.blit(overlay, (0, 0))

    title = title_font.render("Alto's Adventure", True, (255, 255, 255))
    screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2,
                        WINDOW_HEIGHT // 2 - 60))

    sub = subtitle_font.render("Press SPACE or click to start", True, (220, 220, 230))
    screen.blit(sub, (WINDOW_WIDTH // 2 - sub.get_width() // 2,
                      WINDOW_HEIGHT // 2 + 10))


def _draw_game_over(screen: pygame.Surface, overlay: pygame.Surface,
                    title_font: pygame.font.Font,
                    subtitle_font: pygame.font.Font,
                    font: pygame.font.Font,
                    distance: float, score: int,
                    coins_collected: int) -> None:
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))

    title = title_font.render("Game Over", True, (255, 255, 255))
    screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2,
                        WINDOW_HEIGHT // 2 - 80))

    dist_text = font.render(f"Distance: {distance / 10:.0f} m", True, (220, 220, 230))
    screen.blit(dist_text, (WINDOW_WIDTH // 2 - dist_text.get_width() // 2,
                            WINDOW_HEIGHT // 2 - 15))

    score_text = font.render(f"Score: {score}", True, (220, 220, 230))
    screen.blit(score_text, (WINDOW_WIDTH // 2 - score_text.get_width() // 2,
                             WINDOW_HEIGHT // 2 + 15))

    coins_text = font.render(f"Coins: {coins_collected}", True, (255, 210, 60))
    screen.blit(coins_text, (WINDOW_WIDTH // 2 - coins_text.get_width() // 2,
                             WINDOW_HEIGHT // 2 + 45))

    restart = subtitle_font.render("Press SPACE or click to restart", True, (200, 200, 210))
    screen.blit(restart, (WINDOW_WIDTH // 2 - restart.get_width() // 2,
                          WINDOW_HEIGHT // 2 + 90))
