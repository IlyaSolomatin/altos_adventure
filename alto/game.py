import pygame

from .constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    FPS,
    BACKGROUND_COLOR,
    BASE_SCROLL_SPEED,
    CAMERA_LERP,
)
from .camera import Camera
from .background import ParallaxBackground
from .terrain import Terrain
from .player import Player


def run_game() -> None:
    pygame.init()
    try:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        clock = pygame.time.Clock()
        running = True
        font = pygame.font.SysFont(None, 28)
        camera = Camera(BASE_SCROLL_SPEED)
        background = ParallaxBackground(WINDOW_WIDTH, WINDOW_HEIGHT)
        terrain = Terrain()
        player = Player(100.0, WINDOW_HEIGHT * 0.4)
        distance = 0.0
        airtime = 0.0
        score = 0
        button_down = False
        button_pressed = False

        while running:
            dt = clock.tick(FPS) / 1000.0

            button_pressed = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    button_down = True
                    button_pressed = True
                elif event.type == pygame.KEYUP and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    button_down = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    button_down = True
                    button_pressed = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    button_down = False

            screen.fill(BACKGROUND_COLOR)
            player.update(dt, button_down, button_pressed, terrain.sample_height, terrain.sample_slope)
            camera_target_x = max(camera.x + BASE_SCROLL_SPEED * dt, player.x - WINDOW_WIDTH * 0.3)
            target_y = player.y - WINDOW_HEIGHT * 0.6
            camera.update(dt, camera_target_x, CAMERA_LERP, target_y, CAMERA_LERP)
            distance += max(0.0, player.vx) * dt
            airtime = airtime + dt if not player.on_ground else 0.0
            if not player.on_ground and airtime > 1.0:
                score += int(10 * dt)
            background.draw(screen, camera.x)
            terrain.draw(screen, camera.x, camera.y)
            player.draw(screen, camera.x, camera.y)
            fps_text = font.render(f"FPS {clock.get_fps():.0f}", True, (200, 210, 220))
            hud_text = font.render(f"Spd {player.vx:4.0f}  Dist {distance/10:.0f}m  Air {airtime:0.1f}s  Score {score}", True, (230, 235, 240))
            screen.blit(fps_text, (12, 10))
            screen.blit(hud_text, (12, 36))
            pygame.display.flip()
    finally:
        pygame.quit()


