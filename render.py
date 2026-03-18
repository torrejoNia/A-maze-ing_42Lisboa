# ASCII Renderer
import os
import sys
import signal
import tty
import termios
import select
from typing import Callable, TypedDict

# Wall bitmasks — match the bit positions in Cell.walls
N_WALL: int = 0b0001
E_WALL: int = 0b0010
S_WALL: int = 0b0100
W_WALL: int = 0b1000

# ANSI escape sequences
# Format: \033[ = escape + [,  then a code,  then m to end
RESET: str = "\033[0m"

# ANSI foreground color reference:
#   30 black  | 31 red     | 32 green  | 33 yellow
#   34 blue   | 35 magenta | 36 cyan   | 37 white
#   90–97     = bright variants of the above
#   1;Xm      = bold + color X
COLOR_PATH: str = "\033[33m"
COLOR_ENTRY: str = "\033[1;32m"
COLOR_EXIT: str = "\033[1;31m"

# List of wall color options cycled with the "c" key
WALL_COLORS: list[str] = [
    "\033[37m",
    "\033[36m",
    "\033[32m",
    "\033[31m"
]

# Direction → (row delta, col delta)
# Frame delays for each animation phase (seconds)
GEN_FRAME_DELAY: float = 0.01    # fast — 50 cells/sec
PATH_FRAME_DELAY: float = 0.05   # slower — ~14 cells/sec

# Direction → (row delta, col delta)
DIR_DELTA: dict[str, tuple[int, int]] = {
    "N": (-1, 0),
    "E": (0, +1),
    "S": (+1, 0),
    "W": (0, -1),
}

# Global boolean flag — set to True by the resize signal handler
_resize_flag: bool = False


# Type definitions for structured data
class MazeData(TypedDict):
    """Structured data for rendering the maze."""

    grid: list[list[int]]
    entry: tuple[int, int]
    exit_: tuple[int, int]
    path: list[tuple[int, int]]


def _on_resize(signum: int, frame: object) -> None:
    """Handle SIGWINCH by setting the global resize flag."""
    global _resize_flag
    _resize_flag = True


signal.signal(signal.SIGWINCH, _on_resize)


def _directions_to_cells(
    start: tuple[int, int],
    directions: str
) -> list[tuple[int, int]]:
    """Convert a direction string into a list of cell coordinates.

    Args:
        start (tuple[int, int]): Starting cell as (row, col).
        directions (str): Sequence of cardinal letters, e.g. "NENW".

    Returns:
        list[tuple[int, int]]: Ordered cell coordinates of the path,
            including the start cell.
    """
    result: list[tuple[int, int]] = [start]
    current_row: int = start[0]
    current_col: int = start[1]

    for dir in directions:
        row_delta: int = DIR_DELTA[dir][0]
        col_delta: int = DIR_DELTA[dir][1]
        current_row += row_delta
        current_col += col_delta
        result.append((current_row, current_col))
    return result


def parse_hex_file(filepath: str) -> MazeData:
    """Parse maze data from a hex file.

    The file contains a grid of hex digits (one per cell) as the
    first section, optionally followed by a blank line and metadata
    lines: entry coordinates, exit coordinates, and a direction
    string encoding the solution path.

    Args:
        filepath (str): Path to the hex maze file.

    Returns:
        MazeData: Structured dict with grid, entry, exit_, and path.
    """
    with open(filepath) as f:
        content: str = f.read()

    sections: list[str] = content.split("\n\n", 1)

    part1: str
    part2: str
    if len(sections) > 1:
        part1 = sections[0]
        part2 = sections[1]
    else:
        part1 = content
        part2 = ""

    all_lines: list[str] = part1.splitlines()
    grid_lines: list[str] = []
    for ln in all_lines:
        if ln.strip():
            grid_lines.append(ln)

    grid: list[list[int]] = []
    for line in grid_lines:
        row: list[int] = []
        clean_line: str = line.strip()

        for ch in clean_line:
            cell_value: int = int(ch, 16)
            row.append(cell_value)
        grid.append(row)

    entry: tuple[int, int] = (0, 0)
    exit_: tuple[int, int] = (0, 0)
    path: list[tuple[int, int]] = []
    meta_lines: list[str] = []

    if part2:
        all_meta: list[str] = part2.splitlines()
        for ln in all_meta:
            if ln.strip():
                meta_lines.append(ln.strip())

    if len(meta_lines) >= 1:
        parts: list[str] = meta_lines[0].split(",")
        col_str: str = parts[0]
        row_str: str = parts[1]
        entry = (int(row_str), int(col_str))

    if len(meta_lines) >= 2:
        parts = meta_lines[1].split(",")
        col_str = parts[0]
        row_str = parts[1]
        exit_ = (int(row_str), int(col_str))

    if len(meta_lines) >= 3:
        directions_str: str = meta_lines[2].strip().upper()
        path = _directions_to_cells(entry, directions_str)

    return MazeData(
        grid=grid,
        entry=entry,
        exit_=exit_,
        path=path
    )


class Renderer:
    """Render a maze in the terminal and handle user input."""

    def __init__(
        self,
        grid: list[list[int]],
        entry: tuple[int, int],
        exit_: tuple[int, int],
        path: list[tuple[int, int]],
        on_regenerate: Callable[[], None],
    ) -> None:
        """Initialise the renderer with maze data and callbacks.

        Args:
            grid (list[list[int]]): 2D wall bitmask grid.
            entry (tuple[int, int]): Entry cell coordinates (row, col).
            exit_ (tuple[int, int]): Exit cell coordinates (row, col).
            path (list[tuple[int, int]]): Solution path as cell coords.
            on_regenerate (Callable[[], None]): Called when the user
                requests maze regeneration.
        """
        self._grid: list[list[int]] = grid
        self._entry: tuple[int, int] = entry
        self._exit: tuple[int, int] = exit_
        self.path: list[tuple[int, int]] = path
        self._on_regenerate: Callable[[], None] = on_regenerate
        self._rows: int = len(grid)
        self._cols: int = len(grid[0])
        self._char_rows: int = 2 * self._rows + 1
        self._char_cols: int = 2 * self._cols + 1
        self._path_step: int = 0
        self._gen_step: int = 0
        self._color_index: int = 0
        self._path_set: frozenset[tuple[int, int]] = frozenset(path)

    def _current_wall_color(self) -> str:
        """Return the ANSI color code for the active wall color.

        Returns:
            str: ANSI escape sequence for the current wall color.
        """
        return WALL_COLORS[self._color_index]

    def _cycle_color(self) -> None:
        """Advance the wall color index to the next available color."""
        self._color_index = (self._color_index + 1) % len(WALL_COLORS)

    def _build_char_grid(self) -> list[list[str]]:
        """Build the character grid from maze wall bitmasks.

        Each maze cell maps to a 2x2 block of characters. Corners
        are always '┼'; horizontal and vertical wall segments are
        drawn based on the N/S/E/W bitmask values.

        Returns:
            list[list[str]]: 2D character buffer of the maze outline.
        """
        buf: list[list[str]] = []

        for _ in range(self._char_rows):
            row: list[str] = [" "] * self._char_cols
            buf.append(row)

        for r in range(self._rows + 1):
            for c in range(self._cols + 1):
                buf[2*r][2*c] = "┼"

        walls: int = 0
        for r in range(self._rows):
            for c in range(self._cols):
                if r * self._cols + c >= self._gen_step:
                    walls = 0xF
                else:
                    walls = self._grid[r][c]

                if walls & N_WALL:
                    buf[2*r][2*c + 1] = "─"
                else:
                    buf[2*r][2*c + 1] = " "
                if walls & W_WALL:
                    buf[2*r + 1][2*c] = "│"
                else:
                    buf[2*r + 1][2*c] = " "

            last_col_idx: int = self._cols - 1
            if r * self._cols + last_col_idx >= self._gen_step:
                walls = 0xF
            else:
                walls = self._grid[r][last_col_idx]
            if walls & E_WALL:
                buf[2*r + 1][2*self._cols] = "│"
            else:
                buf[2*r + 1][2*self._cols] = " "

        for c in range(self._cols):
            last_row_idx: int = self._rows - 1
            if last_row_idx * self._cols + c >= self._gen_step:
                walls = 0xF
            else:
                walls = self._grid[last_row_idx][c]
            if walls & S_WALL:
                buf[2*self._rows][2*c + 1] = "─"
            else:
                buf[2*self._rows][2*c + 1] = " "

        return buf

    def _apply_overlays(self, buf: list[list[str]]) -> None:
        """Overlay path markers, entry, and exit onto the char grid.

        Solid cells (bitmask 0xF) are drawn as '█'. When path display
        is enabled each path cell is marked '*'. Entry and exit cells
        are always drawn as 'E' and 'X' respectively.

        Args:
            buf (list[list[str]]): Character buffer to modify in place.
        """
        for r in range(self._rows):
            for c in range(self._cols):
                if self._grid[r][c] == 0xF:
                    buf[2*r + 1][2*c + 1] = "█"

        if self._path_step > 0:
            for (r, c) in self.path[:self._path_step]:
                buf[2*r + 1][2*c + 1] = "*"

        er: int = self._entry[0]
        ec: int = self._entry[1]
        if 0 <= er < self._rows and 0 <= ec < self._cols:
            buf[2*er + 1][2*ec + 1] = "E"

        xr: int = self._exit[0]
        xc: int = self._exit[1]
        if 0 <= xr < self._rows and 0 <= xc < self._cols:
            buf[2*xr + 1][2*xc + 1] = "X"

        for r in range(self._rows):
            for c in range(self._cols):
                if r * self._cols + c >= self._gen_step:
                    buf[2*r + 1][2*c + 1] = "█"

    def _advance_gen(self) -> bool:
        """Reveal the next cell in the generation animation.

        Returns:
            bool: True if a cell was revealed, False if already done.
        """
        total: int = self._rows * self._cols
        if self._gen_step < total:
            self._gen_step += 1
            return True
        return False

    def _advance_animation(self) -> bool:
        if self._path_step < len(self.path):
            self._path_step += 1
            return True
        return False

    def _render(self) -> None:
        """Draw the current maze state to the terminal.

        Clears the screen, builds the character grid, applies
        overlays, and writes each row with ANSI color codes. If the
        terminal is too small to fit the maze, a warning is shown
        instead.
        """
        term_cols: int = os.get_terminal_size().columns
        term_rows: int = os.get_terminal_size().lines

        if term_rows < self._char_rows or term_cols < self._char_cols:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(
                f"Terminal too small: need"
                f" {self._char_cols}x{self._char_rows}\r\n"
            )
            sys.stdout.flush()
            return

        buf: list[list[str]] = self._build_char_grid()
        self._apply_overlays(buf)

        sys.stdout.write("\033[2J\033[H")

        for row_index in range(self._char_rows):
            line: str = ""

            for ch in buf[row_index]:
                if ch == "E":
                    line += COLOR_ENTRY + ch + RESET
                elif ch == "X":
                    line += COLOR_EXIT + ch + RESET
                elif ch == "*":
                    line += COLOR_PATH + ch + RESET
                elif ch in ("│", "─", "┼", "█"):
                    line += self._current_wall_color() + ch + RESET
                else:
                    line += ch
            sys.stdout.write(line + "\r\n")

        sys.stdout.write(
            " [p] Toggle Path  [c] Color  [r] Regen  [q] Quit\r\n"
        )
        sys.stdout.flush()

    def run(self) -> None:
        """Run the interactive rendering loop.

        Hides the cursor, renders the maze, then blocks on keystrokes:
          p — toggle solution path overlay
          c — cycle wall colour
          r — call on_regenerate and exit the loop
          q — quit without regenerating

        SIGWINCH (terminal resize) triggers an immediate re-render.
        The cursor is restored and repositioned when the loop exits.
        """
        global _resize_flag
        sys.stdout.write("\033[?1049h\033[?25l")
        sys.stdout.flush()
        signal.signal(signal.SIGWINCH, _on_resize)

        fd: int = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)
        termios.tcflush(fd, termios.TCIFLUSH)

        self._render()

        try:
            while True:
                if _resize_flag:
                    _resize_flag = False
                    self._render()

                total: int = self._rows * self._cols
                FRAME_DELAY: float
                if self._gen_step < total:
                    FRAME_DELAY = GEN_FRAME_DELAY
                else:
                    FRAME_DELAY = PATH_FRAME_DELAY

                if select.select([sys.stdin], [], [], FRAME_DELAY)[0]:
                    key: str = os.read(fd, 1).decode('utf-8', errors='replace')

                    if key == "q":
                        break

                    elif key == "p":
                        if self._path_step > 0:
                            self._path_step = 0
                        else:
                            self._path_step = 1
                        self._render()

                    elif key == "c":
                        self._cycle_color()
                        self._render()

                    elif key == "r":
                        self._on_regenerate()
                        break

                else:
                    if self._advance_gen():
                        self._render()
                    elif self._path_step > 0 and self._advance_animation():
                        self._render()

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write("\033[?25h\033[?1049l")
            sys.stdout.flush()


def launch(
    grid: list[list[int]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> None:
    """Create a Renderer and start the interactive loop.

    Args:
        grid (list[list[int]]): 2D wall bitmask grid.
        entry (tuple[int, int]): Entry cell coordinates (row, col).
        exit_ (tuple[int, int]): Exit cell coordinates (row, col).
        path (list[tuple[int, int]]): Solution path as cell coords.
        on_regenerate (Callable[[], None]): Called on maze regeneration.
    """
    renderer: Renderer = Renderer(
        grid,
        entry,
        exit_,
        path,
        on_regenerate
    )
    renderer.run()


if __name__ == "__main__":
    d = parse_hex_file('test_maze.txt')
    launch(d['grid'], d['entry'], d['exit_'], d['path'], lambda: None)
