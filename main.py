import pygame
from game.game_engine import GameEngine

# Initialize audio before pygame
pygame.mixer.pre_init(
    frequency=44100,
    size=-16,
    channels=2,
    buffer=512
)

# Initialize pygame
pygame.init()

# Make sure the mixer is available
if not pygame.mixer.get_init():
    pygame.mixer.init()

# Screen dimensions
WIDTH, HEIGHT = 600, 500
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Marble Tilt Maze - Pygame Version")

# Clock
clock = pygame.time.Clock()
FPS = 60

# Game engine
engine = GameEngine(WIDTH, HEIGHT)


def main():
    running = True

    while running:
        for event in pygame.event.get():
            engine.handle_event(event)

        engine.handle_input()
        engine.update()
        engine.render(SCREEN)

        pygame.display.flip()
        clock.tick(FPS)

        if engine.exit_requested:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()