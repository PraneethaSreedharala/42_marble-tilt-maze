import pygame
from .marble import Marble
from .wall import Wall

# Game colors
WHITE = (255, 255, 255)
DARK = (40, 40, 50)
WALL_COLOR = (90, 90, 110)
GOAL_COLOR = (60, 200, 120)
TIMEOUT_COLOR = (220, 80, 80)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        # Difficulty settings
        self.difficulties = {
            "Easy": {
                "tilt_strength": 0.4,
                "friction": 0.05,
                "time_limit_ms": 60000
            },
            "Medium": {
                "tilt_strength": 0.6,
                "friction": 0.02,
                "time_limit_ms": 45000
            },
            "Hard": {
                "tilt_strength": 0.9,
                "friction": 0.01,
                "time_limit_ms": 30000
            }
        }

        self.current_difficulty = "Medium"

        # Maze
        self.walls = self._build_maze()

        # Goal
        self.goal_x = width - 60
        self.goal_y = height - 60
        self.goal_radius = 22

        # Fonts
        self.font = pygame.font.SysFont("Arial", 26)
        self.end_font = pygame.font.SysFont("Arial", 48)
        self.small_font = pygame.font.SysFont("Arial", 24)
        self.menu_font = pygame.font.SysFont("Arial", 32)

        # Game state
        self.game_over = False
        self.result = None
        self.finish_time_ms = None

        # Replay/menu state
        self.show_difficulty_menu = False
        self.exit_requested = False

        # Sound setup
        pygame.mixer.set_num_channels(8)

        self.bounce_sound = self._load_sound(
            "sounds/bounce.wav"
        )

        self.goal_sound = self._load_sound(
            "sounds/goal.wav"
        )

        self.timeout_sound = self._load_sound(
            "sounds/timeout.wav"
        )

        # Dedicated channels prevent sounds from interfering
        self.bounce_channel = pygame.mixer.Channel(0)
        self.goal_channel = pygame.mixer.Channel(1)
        self.timeout_channel = pygame.mixer.Channel(2)

        # Initialize game
        self.reset_game("Medium")

    def _load_sound(self, filename):
        """Load a sound effect safely."""

        try:
            sound = pygame.mixer.Sound(filename)
            sound.set_volume(1.0)
            return sound

        except (pygame.error, FileNotFoundError):
            print(f"Warning: Could not load sound: {filename}")
            return None

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

    def reset_game(self, difficulty):
        """Reset the game using the selected difficulty."""

        self.current_difficulty = difficulty

        settings = self.difficulties[difficulty]

        self.tilt_strength = settings["tilt_strength"]
        self.friction = settings["friction"]
        self.time_limit_ms = settings["time_limit_ms"]

        # Reset marble
        self.marble = Marble(50, 50)
        self.max_speed = 9

        # Reset game state
        self.game_over = False
        self.result = None
        self.finish_time_ms = None

        # Hide difficulty menu
        self.show_difficulty_menu = False

        # Reset timer
        self.start_ticks = pygame.time.get_ticks()

    def handle_event(self, event):
        # Close window
        if event.type == pygame.QUIT:
            self.exit_requested = True
            return

        if event.type != pygame.KEYDOWN:
            return

        # Game-over screen
        if self.game_over and not self.show_difficulty_menu:

            # Replay
            if event.key in (pygame.K_r, pygame.K_RETURN):
                self.show_difficulty_menu = True

            # Exit
            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.exit_requested = True

            return

        # Difficulty selection
        if self.show_difficulty_menu:

            if event.key == pygame.K_1:
                self.reset_game("Easy")

            elif event.key == pygame.K_2:
                self.reset_game("Medium")

            elif event.key == pygame.K_3:
                self.reset_game("Hard")

            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.exit_requested = True

    def handle_input(self):
        if self.game_over or self.show_difficulty_menu:
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
        if self.game_over or self.show_difficulty_menu:
            return

        # Check timer
        elapsed = pygame.time.get_ticks() - self.start_ticks

        if elapsed >= self.time_limit_ms:
            self.game_over = True
            self.result = "timeout"
            self.finish_time_ms = self.time_limit_ms

            # Play timeout sound
            if self.timeout_sound:
                self.timeout_channel.play(self.timeout_sound)

            return

        # Apply friction
        self.marble.vx *= (1 - self.friction)
        self.marble.vy *= (1 - self.friction)

        # Limit maximum speed
        speed = (
            self.marble.vx ** 2
            + self.marble.vy ** 2
        ) ** 0.5

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

            # Play goal sound
            if self.goal_sound:
                self.goal_channel.play(self.goal_sound)

    def _resolve_wall_collisions(self):
        """
        True circle-vs-rectangle collision detection.
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

            # Collision only when the actual circular marble
            # touches or overlaps the wall.
            if distance_squared <= self.marble.radius ** 2:

                distance = distance_squared ** 0.5

                if distance > 0:

                    # Push marble outside the wall
                    overlap = self.marble.radius - distance

                    nx = dx / distance
                    ny = dy / distance

                    self.marble.x += nx * overlap
                    self.marble.y += ny * overlap

                    # Determine whether marble is moving
                    # toward the wall.
                    velocity_toward_wall = (
                        self.marble.vx * nx
                        + self.marble.vy * ny
                    )

                    # Bounce only if moving into the wall
                    if velocity_toward_wall < 0:

                        self.marble.vx -= (
                            1.3 * velocity_toward_wall * nx
                        )

                        self.marble.vy -= (
                            1.3 * velocity_toward_wall * ny
                        )

                        # Play bounce sound
                        if self.bounce_sound:
                            self.bounce_channel.play(
                                self.bounce_sound
                            )

                else:
                    # Safety fallback
                    if abs(self.marble.vx) > abs(self.marble.vy):
                        self.marble.vx *= -0.3
                    else:
                        self.marble.vy *= -0.3

    def render(self, screen):
        screen.fill(DARK)

        # Difficulty selection menu
        if self.show_difficulty_menu:
            self._render_difficulty_menu(screen)
            return

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

        # Timer
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

        # Difficulty indicator
        difficulty_text = self.font.render(
            f"Difficulty: {self.current_difficulty}",
            True,
            WHITE
        )

        screen.blit(
            difficulty_text,
            (10, 42)
        )

        # Game-over screen
        if self.game_over:
            self._render_game_over(screen)

    def _render_game_over(self, screen):
        # Dark overlay
        overlay = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA
        )

        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))

        if self.result == "solved":
            title = "MAZE SOLVED!"
            title_color = GOAL_COLOR

            finish_seconds = self.finish_time_ms / 1000

            message = (
                f"Finished in {finish_seconds:.1f} seconds"
            )

        else:
            title = "TIME'S UP!"
            title_color = TIMEOUT_COLOR

            message = (
                "The maze was not solved in time."
            )

        # Title
        title_surface = self.end_font.render(
            title,
            True,
            title_color
        )

        title_rect = title_surface.get_rect(
            center=(self.width // 2, 170)
        )

        screen.blit(
            title_surface,
            title_rect
        )

        # Result message
        message_surface = self.small_font.render(
            message,
            True,
            WHITE
        )

        message_rect = message_surface.get_rect(
            center=(self.width // 2, 230)
        )

        screen.blit(
            message_surface,
            message_rect
        )

        # Replay instruction
        replay_text = self.small_font.render(
            "Press R to replay",
            True,
            WHITE
        )

        replay_rect = replay_text.get_rect(
            center=(self.width // 2, 290)
        )

        screen.blit(
            replay_text,
            replay_rect
        )

        # Exit instruction
        exit_text = self.small_font.render(
            "Press ESC to exit",
            True,
            WHITE
        )

        exit_rect = exit_text.get_rect(
            center=(self.width // 2, 330)
        )

        screen.blit(
            exit_text,
            exit_rect
        )

    def _render_difficulty_menu(self, screen):
        # Title
        title_surface = self.end_font.render(
            "CHOOSE DIFFICULTY",
            True,
            WHITE
        )

        title_rect = title_surface.get_rect(
            center=(self.width // 2, 100)
        )

        screen.blit(
            title_surface,
            title_rect
        )

        # Easy
        easy = self.menu_font.render(
            "1 - Easy",
            True,
            WHITE
        )

        easy_rect = easy.get_rect(
            center=(self.width // 2, 190)
        )

        screen.blit(easy, easy_rect)

        # Medium
        medium = self.menu_font.render(
            "2 - Medium",
            True,
            WHITE
        )

        medium_rect = medium.get_rect(
            center=(self.width // 2, 250)
        )

        screen.blit(medium, medium_rect)

        # Hard
        hard = self.menu_font.render(
            "3 - Hard",
            True,
            WHITE
        )

        hard_rect = hard.get_rect(
            center=(self.width // 2, 310)
        )

        screen.blit(hard, hard_rect)

        # Difficulty settings
        settings = self.small_font.render(
            "Easy: 60s | Medium: 45s | Hard: 30s",
            True,
            WHITE
        )

        settings_rect = settings.get_rect(
            center=(self.width // 2, 370)
        )

        screen.blit(
            settings,
            settings_rect
        )

        # Exit
        exit_text = self.small_font.render(
            "Press ESC to exit",
            True,
            WHITE
        )

        exit_rect = exit_text.get_rect(
            center=(self.width // 2, 420)
        )

        screen.blit(
            exit_text,
            exit_rect
        )