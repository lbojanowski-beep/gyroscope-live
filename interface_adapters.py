# interface_adapters.py

from typing import Optional

from domain import GameBoard, Position
from usecases import (
    GameService,
    GameStateChangedEvent,
    GameOverEvent,
)


class GameInputAdapter:
    """
    Adapter wejściowy – zamienia wołania kontrolera na metody GameService.
    """

    def __init__(self, game_service: GameService):
        self._game_service = game_service

    def change_direction(self, new_direction: Position) -> None:
        self._game_service.change_direction(new_direction)

    def tick(self) -> None:
        self._game_service.tick()

    @property
    def service(self) -> GameService:
        return self._game_service


class GameOutputAdapter:
    """
    Adapter wyjściowy – trzyma ostatni stan gry / wynik game over
    w formie prostych pól, które UI może sobie czytać.
    """

    def __init__(self):
        self.latest_game_board: Optional[GameBoard] = None
        self.game_over_score: Optional[int] = None

    def present_game_state(self, game_board: GameBoard) -> None:
        self.latest_game_board = game_board
        self.game_over_score = None

    def present_game_over(self, score: int) -> None:
        self.game_over_score = score
        self.latest_game_board = None


class GameController:
    """
    Koordynuje input → use case → output.
    """

    def __init__(self, input_adapter: GameInputAdapter, output_adapter: GameOutputAdapter):
        self._input_adapter = input_adapter
        self._output_adapter = output_adapter

    def change_direction(self, new_direction: Position) -> None:
        self._input_adapter.change_direction(new_direction)
        self._process_events()

    def tick(self) -> None:
        self._input_adapter.tick()
        self._process_events()

    def _process_events(self) -> None:
        event = self._input_adapter.service.get_last_event()
        if event is None:
            return

        if isinstance(event, GameStateChangedEvent):
            self._output_adapter.present_game_state(event.game_board)
        elif isinstance(event, GameOverEvent):
            self._output_adapter.present_game_over(event.score)