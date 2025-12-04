from dataclasses import dataclass, field
from typing import List, Tuple
import random

Position = Tuple[int, int]


@dataclass
class Snake:
    body: List[Position] = field(default_factory=list)
    direction: Position = (1, 0)  # moving right by default (dx, dy)

    def move(self, grow: bool = False) -> None:
        head_x, head_y = self.body[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        self.body.insert(0, new_head)
        if not grow:
            self.body.pop()

    def change_direction(self, new_direction: Position) -> None:
        # Prevent the snake from reversing
        opposite = (-self.direction[0], -self.direction[1])
        if new_direction != opposite:
            self.direction = new_direction

    def collides_with_self(self) -> bool:
        return self.body[0] in self.body[1:]

    def occupies_position(self, pos: Position) -> bool:
        return pos in self.body


@dataclass
class Food:
    position: Position


@dataclass
class GameBoard:
    width: int
    height: int
    snake: Snake
    food: Food
    score: int = 0

    def is_position_inside(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def is_collision(self) -> bool:
        head = self.snake.body[0]
        # Check wall collision
        if not self.is_position_inside(head):
            return True
        # Check self collision
        if self.snake.collides_with_self():
            return True
        return False

    def is_food_eaten(self) -> bool:
        return self.snake.body[0] == self.food.position

    def place_food(self) -> None:
        """Place food at a random position not occupied by the snake."""
        empty_positions = [
            (x, y)
            for x in range(self.width)
            for y in range(self.height)
            if not self.snake.occupies_position((x, y))
        ]
        if not empty_positions:
            # No space left for food, game could be considered won or over
            self.food.position = (-1, -1)  # Invalid position
        else:
            self.food.position = random.choice(empty_positions)

    def update(self) -> None:
        """Advance the game state by one step."""
        # NOTE: to stay zgodny z artefaktem – najpierw sprawdza, potem move
        grow = self.is_food_eaten()
        self.snake.move(grow=grow)

        if grow:
            self.score += 1
            self.place_food()