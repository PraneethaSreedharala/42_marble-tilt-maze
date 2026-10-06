import pygame
from .marble import Marble
from .wall import Wall

# Game colors
WHITE = (255, 255, 255)
DARK = (40, 40, 50)
WALL_COLOR = (90, 90, 110)
GOAL_COLOR = (60, 200, 120)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        # Marble settings
        self.marble = Marble(50, 50)
        self.tilt_strength = 0.6
        self.friction = 0.02
        self.max_speed = 9

        # Maze
        self.walls = self._build_maze()

        # Goal
        self.goal_x = width - 60
        self.goal_y = height - 60
        self.goal_radius = 22

        # Timer
        self.time_limit_ms = 45000
        self.start_ticks = pygame.time.get_ticks()

        # Fonts
        self.font = pygame.font.SysFont("Arial", 26)

        # Game state
        self.game_over = False
        self.result = None
        self.finish_time_ms = None

    def _build_maze(self):
        walls = []
        t = 16

        # Outer boundary
        walls.append(Wall(0, 0, self.width, t))
        walls.append(Wall(0, self.height - t, self.width, t))
        walls.append(Wall(0, 0, t, self.height))
        walls.append(Wall(self.width - t, 0, t, self.height))

        # Internal walls
        walls.append(Wall(0, 140, self.width - 140, t))
        walls.append(Wall(140, 260, self.width - 140, t))
        walls.append(Wall(0, 380, self.width - 140, t))

        return walls

    def handle_event(self, event):
        # The game is controlled by the mouse position.
        pass

    def handle_input(self):
        if self.game_over:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()

        dx = mouse_x - self.width // 2
        dy = mouse_y - self.height // 2

        dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)

        ax = (dx / dist) * self.tilt_strength
        ay = (dy / dist) * self.tilt_strength

        self.marble.vx += ax
        self.marble.vy += ay

    def update(self):
        if self.game_over:
            return

        # Check timer
        elapsed = pygame.time.get_ticks() - self.start_ticks

        if elapsed >= self.time_limit_ms:
            self.game_over = True
            self.result = "timeout"
            return

        # Apply friction
        self.marble.vx *= (1 - self.friction)
        self.marble.vy *= (1 - self.friction)

        # Limit maximum speed
        speed = (self.marble.vx ** 2 + self.marble.vy ** 2) ** 0.5

        if speed > self.max_speed:
            scale = self.max_speed / speed
            self.marble.vx *= scale
            self.marble.vy *= scale

        # Move marble
        self.marble.x += self.marble.vx
        self.marble.y += self.marble.vy

        # Handle wall collisions
        self._resolve_wall_collisions()

        # Check goal
        gx = self.goal_x - self.marble.x
        gy = self.goal_y - self.marble.y

        if (gx ** 2 + gy ** 2) ** 0.5 <= self.goal_radius:
            self.game_over = True
            self.result = "solved"
            self.finish_time_ms = elapsed

    def _resolve_wall_collisions(self):
        """
        Resolve collisions using true circle-vs-rectangle
        collision detection instead of bounding-box collision.
        """

        for wall in self.walls:
            wall_rect = wall.rect()

            # Find the closest point on the wall rectangle
            # to the center of the marble.
            closest_x = max(
                wall_rect.left,
                min(self.marble.x, wall_rect.right)
            )

            closest_y = max(
                wall_rect.top,
                min(self.marble.y, wall_rect.bottom)
            )

            # Distance between marble center and closest point
            dx = self.marble.x - closest_x
            dy = self.marble.y - closest_y

            distance_squared = dx * dx + dy * dy

            # The marble has touched the wall only when the
            # actual circular edge reaches the rectangle.
            if distance_squared <= self.marble.radius ** 2:

                distance = distance_squared ** 0.5

                if distance > 0:

                    # Push the marble outside the wall.
                    overlap = self.marble.radius - distance

                    nx = dx / distance
                    ny = dy / distance

                    self.marble.x += nx * overlap
                    self.marble.y += ny * overlap

                    # Determine whether the marble is moving
                    # toward the wall.
                    velocity_toward_wall = (
                        self.marble.vx * nx
                        + self.marble.vy * ny
                    )

                    # Bounce only if moving into the wall.
                    if velocity_toward_wall < 0:
                        self.marble.vx -= (
                            1.3 * velocity_toward_wall * nx
                        )

                        self.marble.vy -= (
                            1.3 * velocity_toward_wall * ny
                        )

                else:
                    # Safety fallback if the marble center is
                    # exactly inside the wall.
                    if abs(self.marble.vx) > abs(self.marble.vy):
                        self.marble.vx *= -0.3
                    else:
                        self.marble.vy *= -0.3

    def render(self, screen):
        screen.fill(DARK)

        # Draw walls
        for wall in self.walls:
            pygame.draw.rect(
                screen,
                WALL_COLOR,
                wall.rect()
            )

        # Draw goal
        pygame.draw.circle(
            screen,
            GOAL_COLOR,
            (self.goal_x, self.goal_y),
            self.goal_radius
        )

        # Draw marble
        pygame.draw.circle(
            screen,
            WHITE,
            (
                int(self.marble.x),
                int(self.marble.y)
            ),
            self.marble.radius
        )

        # Draw timer
        elapsed = pygame.time.get_ticks() - self.start_ticks

        seconds_left = max(
            0,
            (self.time_limit_ms - elapsed) // 1000
        )

        timer_text = self.font.render(
            f"Time: {seconds_left}s",
            True,
            WHITE
        )

        screen.blit(timer_text, (10, 10))

        # Existing console-based game-over message
        if self.game_over and not getattr(
            self,
            "_game_over_logged",
            False
        ):
            if self.result == "solved":
                print(
                    f"Solved! Finished in "
                    f"{self.finish_time_ms / 1000:.1f}s"
                )
            else:
                print("Time's up! Maze not solved.")

            self._game_over_logged = True