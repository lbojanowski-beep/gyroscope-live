import pygame

from domain import Snake, Food, GameBoard
from usecases import GameService
from interface_adapters import GameInputAdapter, GameOutputAdapter, GameController
from infrastructure_adapters import PygameInputHandler, PygameOutputRenderer


def create_initial_game_board(width: int, height: int) -> GameBoard:
    # Initialize snake in the center moving right
    init_x = width // 2
    init_y = height // 2
    snake = Snake(
        body=[(init_x, init_y), (init_x - 1, init_y), (init_x - 2, init_y)],
        direction=(1, 0),
    )
    food = Food(position=(-1, -1))  # temporary invalid position
    game_board = GameBoard(width=width, height=height, snake=snake, food=food, score=0)
    game_board.place_food()
    return game_board


def main() -> None:
    BOARD_WIDTH = 20
    BOARD_HEIGHT = 20

    # Domain
    game_board = create_initial_game_board(BOARD_WIDTH, BOARD_HEIGHT)

    # Use case
    game_service = GameService(game_board)

    # Interface adapters
    input_adapter = GameInputAdapter(game_service)
    output_adapter = GameOutputAdapter()
    controller = GameController(input_adapter, output_adapter)

    # Infrastructure
    input_handler = PygameInputHandler()
    output_renderer = PygameOutputRenderer(BOARD_WIDTH, BOARD_HEIGHT)

    # Game loop
    running = True
    while running:
        if input_handler.has_quit():
            break

        direction_input = input_handler.get_direction_input()
        if direction_input is not None:
            controller.change_direction(direction_input)

        controller.tick()

        if output_adapter.game_over_score is not None:
            output_renderer.render_game_over(output_adapter.game_over_score)
            running = False
        elif output_adapter.latest_game_board is not None:
            gb = output_adapter.latest_game_board
            output_renderer.render_game_state(
                gb.width,
                gb.height,
                gb.snake.body,
                gb.food.position,
                gb.score,
            )

        input_handler.wait_for_tick()

    pygame.quit()


if __name__ == "__main__":
    main()