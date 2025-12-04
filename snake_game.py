#!/usr/bin/env python
import pygame
import sys
import random
from typing import List, Tuple

# -----------------------------
# 1. Setup and Configuration
# -----------------------------

pygame.init()

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
CELL_SIZE = 20
FPS = 10

GRID_WIDTH = SCREEN_WIDTH // CELL_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // CELL_SIZE

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED   = (255,   0,   0)
GRAY  = (40,   40,   40)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Snake – Clean Architecture")
clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 32)


# -----------------------------
# 2. Game Entities
# -----------------------------

GridPos = Tuple[int, int]


class Snake:
    def __init__(self, start: GridPos):
        # body: head is index 0
        self.body: List[GridPos] = [start]
        self.direction: GridPos = (1, 0)  # moving right

    @property
    def head(self) -> GridPos:
        return self.body[0]

    def set_direction(self, new_dir: GridPos):
        """Prevent reversing directly into itself."""
        opposite = (-self.direction[0], -self.direction[1])
        if new_dir != opposite:
            self.direction = new_dir

    def move(self, grow: bool = False):
        hx, hy = self.head
        dx, dy = self.direction
        new_head = (hx + dx, hy + dy)
        self.body.insert(0, new_head)
        if not grow:
            self.body.pop()

    def occupies(self, pos: GridPos) -> bool:
        return pos in self.body

    def collides_with_self(self) -> bool:
        return self.head in self.body[1:]


class Food:
    def __init__(self, position: GridPos):
        self.position = position


# -----------------------------
# 3. Game State Management
# -----------------------------

class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        start_pos = (GRID_WIDTH // 2, GRID_HEIGHT // 2)
        self.snake = Snake(start_pos)
        self.food = self._spawn_food()
        self.score = 0
        self.game_over = False

    def _spawn_food(self) -> Food:
        while True:
            pos = (random.randint(0, GRID_WIDTH - 1),
                   random.randint(0, GRID_HEIGHT - 1))
            if not self.snake.occupies(pos):
                return Food(pos)


# -----------------------------
# 4. Input Handling (Queued)
# -----------------------------

class InputBuffer:
    """
    Collects inputs each frame and turns them into high-level commands.
    We don't modify GameState here – just queue intents.
    """

    def __init__(self):
        self.commands: List[Tuple[str, object]] = []

    def poll(self) -> bool:
        """
        Poll Pygame events.
        Returns False if user requested quit.
        """
        self.commands.clear()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_r:
                    self.commands.append(("RESTART", None))
                if event.key == pygame.K_UP:
                    self.commands.append(("DIR", (0, -1)))
                elif event.key == pygame.K_DOWN:
                    self.commands.append(("DIR", (0, 1)))
                elif event.key == pygame.K_LEFT:
                    self.commands.append(("DIR", (-1, 0)))
                elif event.key == pygame.K_RIGHT:
                    self.commands.append(("DIR", (1, 0)))
        return True

    def drain(self) -> List[Tuple[str, object]]:
        cmds = list(self.commands)
        self.commands.clear()
        return cmds


# -----------------------------
# 5. Game Logic Controller
# -----------------------------

class GameController:
    """
    Applies commands to state and advances simulation.
    """

    def __init__(self, state: GameState):
        self.state = state

    def apply_commands(self, commands: List[Tuple[str, object]]):
        if self.state.game_over:
            # Only allow restart while game over
            for cmd, payload in commands:
                if cmd == "RESTART":
                    self.state.reset()
            return

        for cmd, payload in commands:
            if cmd == "RESTART":
                self.state.reset()
            elif cmd == "DIR":
                self.state.snake.set_direction(payload)

    def update(self):
        """
        One logic tick: move snake, check collisions, handle food.
        """
        if self.state.game_over:
            return

        snake = self.state.snake
        snake.move(grow=False)

        hx, hy = snake.head

        # Wall collision
        if hx < 0 or hx >= GRID_WIDTH or hy < 0 or hy >= GRID_HEIGHT:
            self.state.game_over = True
            return

        # Self collision
        if snake.collides_with_self():
            self.state.game_over = True
            return

        # Food collision
        if snake.head == self.state.food.position:
            # grow by moving again but with grow=True
            snake.move(grow=True)
            self.state.score += 1
            self.state.food = self.state._spawn_food()


# -----------------------------
# 6. Rendering Engine
# -----------------------------

class Renderer:
    def __init__(self, screen, state: GameState):
        self.screen = screen
        self.state = state

    def _draw_cell(self, pos: GridPos, color):
        x, y = pos
        rect = pygame.Rect(
            x * CELL_SIZE,
            y * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )
        pygame.draw.rect(self.screen, color, rect)

    def render(self):
        # Background
        self.screen.fill(BLACK)

        # Optional grid
        for x in range(GRID_WIDTH):
            pygame.draw.line(
                self.screen, GRAY,
                (x * CELL_SIZE, 0),
                (x * CELL_SIZE, SCREEN_HEIGHT),
                1,
            )
        for y in range(GRID_HEIGHT):
            pygame.draw.line(
                self.screen, GRAY,
                (0, y * CELL_SIZE),
                (SCREEN_WIDTH, y * CELL_SIZE),
                1,
            )

        # Snake
        for i, segment in enumerate(self.state.snake.body):
            color = GREEN if i == 0 else (0, 200, 0)
            self._draw_cell(segment, color)

        # Food
        self._draw_cell(self.state.food.position, RED)

        # Score
        score_surf = font.render(f"Score: {self.state.score}", True, WHITE)
        self.screen.blit(score_surf, (10, 10))

        # Game over message
        if self.state.game_over:
            msg = "Game Over – R to restart, ESC to quit"
            text_surf = font.render(msg, True, WHITE)
            rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(text_surf, rect)

        pygame.display.flip()


# -----------------------------
# 7. Main Game Loop
# -----------------------------

def main():
    state = GameState()
    input_buf = InputBuffer()
    controller = GameController(state)
    renderer = Renderer(screen, state)

    running = True
    while running:
        # 1. Input
        if not input_buf.poll():
            running = False
            break
        commands = input_buf.drain()

        # 2. Apply commands & logic update
        controller.apply_commands(commands)
        controller.update()

        # 3. Render
        renderer.render()

        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()