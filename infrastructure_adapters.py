import pygame
from typing import Optional, List

from domain import Position
from infrastructure_interfaces import InputHandler, OutputRenderer


# Constants for directions
DIRECTION_MAP = {
    pygame.K_UP: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_RIGHT: (1, 0),
}

CELL_SIZE = 20
MARGIN = 2
FONT_SIZE = 24
BACKGROUND_COLOR = (0, 0, 0)
SNAKE_COLOR = (0, 255, 0)
FOOD_COLOR = (255, 0, 0)
TEXT_COLOR = (255, 255, 255)


class PygameInputHandler(InputHandler):
    def __init__(self):
        pygame.init()
        # Małe okno tylko do eventów – i tak rysujemy w drugim
        self._screen = pygame.display.set_mode((100, 100))
        pygame.display.set_caption("Snake Input Capture")
        self._clock = pygame.time.Clock()
        self._quit = False

    def get_direction_input(self) -> Optional[Position]:
        """
        Poll pygame events to capture arrow key presses.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit = True
                return None
            if event.type == pygame.KEYDOWN:
                if event.key in DIRECTION_MAP:
                    return DIRECTION_MAP[event.key]
        return None

    def wait_for_tick(self) -> None:
        self._clock.tick(10)  # 10 logic FPS

    def has_quit(self) -> bool:
        return self._quit


class PygameOutputRenderer(OutputRenderer):
    def __init__(self, board_width: int, board_height: int):
        pygame.init()
        self._width = board_width
        self._height = board_height
        window_width = board_width * (CELL_SIZE + MARGIN) + MARGIN
        window_height = board_height * (CELL_SIZE + MARGIN) + MARGIN + FONT_SIZE + 10
        self._screen = pygame.display.set_mode((window_width, window_height))
        pygame.display.set_caption("Snake Game")
        self._font = pygame.font.SysFont("Arial", FONT_SIZE)
        self._clock = pygame.time.Clock()

    def render_game_state(
        self,
        width: int,
        height: int,
        snake_body: List[Position],
        food_position: Position,
        score: int,
    ) -> None:
        self._screen.fill(BACKGROUND_COLOR)

        # Grid background
        for x in range(width):
            for y in range(height):
                rect = pygame.Rect(
                    x * (CELL_SIZE + MARGIN) + MARGIN,
                    y * (CELL_SIZE + MARGIN) + MARGIN,
                    CELL_SIZE,
                    CELL_SIZE,
                )
                pygame.draw.rect(self._screen, (40, 40, 40), rect)

        # Food
        if food_position != (-1, -1):
            food_rect = pygame.Rect(
                food_position[0] * (CELL_SIZE + MARGIN) + MARGIN,
                food_position[1] * (CELL_SIZE + MARGIN) + MARGIN,
                CELL_SIZE,
                CELL_SIZE,
            )
            pygame.draw.rect(self._screen, FOOD_COLOR, food_rect)

        # Snake
        for segment in snake_body:
            segment_rect = pygame.Rect(
                segment[0] * (CELL_SIZE + MARGIN) + MARGIN,
                segment[1] * (CELL_SIZE + MARGIN) + MARGIN,
                CELL_SIZE,
                CELL_SIZE,
            )
            pygame.draw.rect(self._screen, SNAKE_COLOR, segment_rect)

        # Score
        score_text = self._font.render(f"Score: {score}", True, TEXT_COLOR)
        self._screen.blit(
            score_text,
            (MARGIN, height * (CELL_SIZE + MARGIN) + MARGIN),
        )

        pygame.display.flip()
        self._clock.tick(60)  # render FPS

    def render_game_over(self, score: int) -> None:
        self._screen.fill(BACKGROUND_COLOR)
        game_over_text = self._font.render("Game Over", True, TEXT_COLOR)
        score_text = self._font.render(f"Final Score: {score}", True, TEXT_COLOR)

        game_over_rect = game_over_text.get_rect(
            center=(self._screen.get_width() // 2,
                    self._screen.get_height() // 2 - FONT_SIZE)
        )
        score_rect = score_text.get_rect(
            center=(self._screen.get_width() // 2,
                    self._screen.get_height() // 2 + FONT_SIZE)
        )

        self._screen.blit(game_over_text, game_over_rect)
        self._screen.blit(score_text, score_rect)

        pygame.display.flip()
        pygame.time.wait(3000)