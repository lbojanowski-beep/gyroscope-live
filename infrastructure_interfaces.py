from abc import ABC, abstractmethod
from typing import Optional, List

from domain import Position


class InputHandler(ABC):
    """Abstrakcyjny handler wejścia (klawiatura, pad itd.)."""

    @abstractmethod
    def get_direction_input(self) -> Optional[Position]:
        """
        Zwraca nowy kierunek (dx, dy) albo None, jeśli brak nowego inputu.
        """
        pass

    @abstractmethod
    def wait_for_tick(self) -> None:
        """
        Czeka do następnego „tiku” logiki (np. ogranicza FPS).
        """
        pass

    @abstractmethod
    def has_quit(self) -> bool:
        """
        Czy użytkownik poprosił o zamknięcie gry?
        """
        pass


class OutputRenderer(ABC):
    """Abstrakcyjny renderer wyjścia (pygame, terminal, webcanvas...)."""

    @abstractmethod
    def render_game_state(
        self,
        width: int,
        height: int,
        snake_body: List[Position],
        food_position: Position,
        score: int,
    ) -> None:
        pass

    @abstractmethod
    def render_game_over(self, score: int) -> None:
        pass