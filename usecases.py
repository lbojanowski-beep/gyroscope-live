from dataclasses import dataclass
from typing import Optional

from domain import GameBoard, Position


@dataclass
class GameStateChangedEvent:
    game_board: GameBoard


@dataclass
class GameOverEvent:
    score: int


class GameService:
    """
    Czysta logika „use case” – nie zna pygame, ekranu itd.
    """

    def __init__(self, game_board: GameBoard):
        self._game_board = game_board
        self._game_over = False
        self._last_event: Optional[object] = None

    def change_direction(self, new_direction: Position) -> None:
        if self._game_over:
            return
        self._game_board.snake.change_direction(new_direction)

    def tick(self) -> None:
        if self._game_over:
            return

        # aktualizacja planszy
        self._game_board.update()

        # kolizje → game over
        if self._game_board.is_collision():
            self._game_over = True
            self._last_event = GameOverEvent(score=self._game_board.score)
        else:
            self._last_event = GameStateChangedEvent(game_board=self._game_board)

    def get_last_event(self) -> Optional[object]:
        return self._last_event

    def is_game_over(self) -> bool:
        return self._game_over

    def get_game_board(self) -> GameBoard:
        return self._game_board