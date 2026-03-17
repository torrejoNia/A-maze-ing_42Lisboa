# Writes maze data into the output file


def _format_coord(coord: tuple[int, int]) -> str:
    """Convert an internal (row, col) coordinate to 'col,row' string.

    The output file stores coordinates as x,y (col first). This
    function performs the swap from the internal (row, col) convention.

    Args:
        coord (tuple[int, int]): Coordinate as (row, col).

    Returns:
        str: Coordinate formatted as 'col,row'.
    """
    row: int = coord[0]
    col: int = coord[1]
    return f"{col},{row}"


def _format_grid(grid: list[list[int]]) -> str:
    """Convert a 2D wall-bitmask grid to a hex string block.

    Each integer cell value becomes one lowercase hex character.
    Rows are joined by newlines with no trailing newline.

    Args:
        grid (list[list[int]]): 2D list of wall bitmask integers.

    Returns:
        str: Newline-separated rows of hex digits.
    """
    lines: list[str] = []
    for row in grid:
        row_str: str = ""
        for cell_value in row:
            row_str += format(cell_value, 'x')
        lines.append(row_str)
    return "\n".join(lines)


def write_maze(
    filepath: str,
    grid: list[list[int]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: str,
) -> None:
    """Write maze data to the output file.

    Creates or overwrites the file at filepath with the full maze
    representation: hex grid, blank separator line, entry coords,
    exit coords, and the solution path as a direction string.
    Every line ends with a newline character.

    Args:
        filepath (str): Destination file path.
        grid (list[list[int]]): 2D list of wall bitmask integers.
        entry (tuple[int, int]): Entry cell as (row, col).
        exit_ (tuple[int, int]): Exit cell as (row, col).
        path (str): Solution path as a direction string, e.g. 'SENE'.
    """
    grid_str: str = _format_grid(grid)
    entry_str: str = _format_coord(entry)
    exit_str: str = _format_coord(exit_)

    with open(filepath, "w") as f:
        f.write(grid_str + "\n")
        f.write("\n")
        f.write(entry_str + "\n")
        f.write(exit_str + "\n")
        f.write(path + "\n")
