# Main dispatcher
import sys

from config import parse_config, ConfigData
from mazegen import Maze
from solver import solve_maze
from writer import write_maze
from render import launch, _directions_to_cells


def _build_int_grid(maze: Maze) -> list[list[int]]:
    """Extract wall bitmasks from a Maze's Cell grid.

    Maze.grid is a 2D list of Cell objects indexed as grid[y][x].
    Returns a 2D list of integers in the same row-major order.

    Args:
        maze (Maze): A fully generated Maze instance.

    Returns:
        list[list[int]]: 2D list of wall bitmask integers.
    """
    return [
        [cell.walls for cell in row]
        for row in maze.grid
    ]


def _dispatch(filepath: str) -> None:
    """Run one full pass of the pipeline.

    Re-reads the config on every call so that pressing 'r' in the
    renderer picks up any changes made to the config file since the
    last run.

    Args:
        filepath (str): Path to the configuration file.
    """
    config: ConfigData = parse_config(filepath)

    # Config stores coordinates as (row, col).
    # Maze constructor expects (x, y) = (col, row) — swap here.
    entry_rc: tuple[int, int] = config['entry']
    exit_rc: tuple[int, int] = config['exit_']
    maze_entry: tuple[int, int] = (entry_rc[1], entry_rc[0])
    maze_exit: tuple[int, int] = (exit_rc[1], exit_rc[0])

    maze: Maze = Maze(
        width=config['width'],
        height=config['height'],
        entry=maze_entry,
        exit=maze_exit,
        perfect=config['perfect'],
        seed=config['seed'] if config['seed'] is not None else 0,
        algorithm=config['algorithm'],
        logo_pattern=config['logo'],
    )

    path_str: str = solve_maze(maze)

    # Convert Maze (x, y) back to (row, col) for writer and renderer.
    entry: tuple[int, int] = (maze.entry[1], maze.entry[0])
    exit_: tuple[int, int] = (maze.exit[1], maze.exit[0])

    grid: list[list[int]] = _build_int_grid(maze)
    path_cells: list[tuple[int, int]] = _directions_to_cells(
        entry, path_str
    )

    write_maze(config['output_file'], grid, entry, exit_, path_str)

    launch(
        grid=grid,
        entry=entry,
        exit_=exit_,
        path=path_cells,
        on_regenerate=lambda: _dispatch(filepath),
    )


def main() -> None:
    """Validate arguments and start the dispatcher.

    Expects exactly one argument: the path to the config file.
    All ValueError exceptions from any module are caught here
    and printed as a clean error message before exiting.
    """
    if len(sys.argv) != 2:
        print(
            "Usage: python3 a_maze_ing.py config.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    filepath: str = sys.argv[1]

    try:
        _dispatch(filepath)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
