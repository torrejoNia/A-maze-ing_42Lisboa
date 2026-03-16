# ASCII Renderer
import os, sys, signal, tty, termios
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

def _getch() -> str:
    """
    Read a single character from standard input without
    echoing it to the terminal.

    This function uses the termios and tty modules to set the terminal
    to raw mode, allowing it to read a single character without waiting
    for a newline. It restores the original terminal settings afterward.

    Returns:
        str: The character read from standard input.
    """
    fd: int = sys.stdin.fileno()
    old_settings: list = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch: str = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def _on_resize(signum: int, frame: object) -> None:
    """
    Signal handler for terminal resize events (SIGWINCH).
    """
    global _resize_flag
    _resize_flag = True

signal.signal(signal.SIGWINCH, _on_resize)

def _directions_to_cells(
    start: tuple[int, int],
    directions: str
) -> list[tuple[int, int]]:
    """
    Convert a string of directions (e.g., "NENW") into a list 
    of cell coordinates starting from the given start coordinate.

    Returns:
    list[tuple[int, int]]: A list of cell coordinates 
    corresponding to the path.
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
    """
    Parse the maze data from a hex file.
    Return:
        MazeData: A structured dictionary containing the grid, entry,
        exit, and path.
    """
    content: str = open(filepath).read()

    sections: list[str] = content.split("\n\n", 1)

    if len(sections) > 1:
        part1: str = sections[0]
        part2: str = sections[1]
    else:
        part1: str = content
        part2: str = ""

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

    if part2:
        all_meta: list[str] = part2.splitlines()
        meta_lines: list[str] = []
        for ln in all_meta:
            if ln.strip():
                meta_lines.append(ln.strip())
    if len (meta_lines) >= 1:
        parts: list[str] = meta_lines[0].split(",")
        col_str: str = parts[0]
        row_str: str = parts[1]
        entry = (int(row_str), int(col_str))
    
    if len(meta_lines) >= 2:
        parts: list[str] = meta_lines[1].split(",")
        col_str: str = parts[0]
        row_str: str = parts[1]
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
    """
    Renderer class responsible
    for rendering the maze and handling user input.
    """
    def __init__(
        self,
        grid: list[list[int]],
        entry: tuple[int, int],
        exit_: tuple[int, int],
        path: list[tuple[int, int]],
        on_regenerate: Callable[[], None],
    ) -> None:
        self._grid: list[list[int]] = grid
        self._entry: tuple[int, int] = entry
        self._exit: tuple[int, int] = exit_
        self.path: list[tuple[int, int]] = path
        self._on_regenerate: Callable[[], None] = on_regenerate
        self._rows: int = len(grid)
        self._cols: int = len(grid[0])
        self._char_rows: int = 2 * self._rows + 1
        self._char_cols: int = 2 * self._cols + 1
        self._show_path: bool = False
        self._color_index: int = 0
        self._path_set: frozenset[tuple[int, int]] = frozenset(path)
    
    @classmethod
    def from_cell_grid(
        cls,
        cells: list[list[int]],
        entry: tuple[int, int],
        exit_: tuple[int, int],
        on_regenerate: Callable[[], None],
    ) -> "Renderer":
        grid: list[list[int]] = []

        for row in cells:
            new_row: list[int] = []
            for cell in row:
                new_row.append(cell.walls)
            grid.append(new_row)

        return Renderer(
            grid,
            entry,
            exit_,
            path,
            on_regenerate
        )
    
    def _current_wall_color(self) -> str:
        return WALL_COLORS[self._color_index]

    def _cycle_color(self) -> None:
        self._color_index = (self._color_index + 1) % len(WALL_COLORS)

    def _build_char_grid(self) -> list[list[str]]:
        buf: list[list[str]] = []

        for _ in range(self._char_rows):
            row: list[str] = [" "] * self._char_cols
            buf.append(row)

        for r in range(self._rows + 1):
            for c in range(self._cols + 1):
                buf[2*r][2*c] = "┼"

        for r in range(self._rows):
            for c in range(self._cols):
                walls: int = self._grid[r][c]

                if walls & N_WALL:
                    buf[2*r][2*c + 1] = "─"
                else:
                    buf[2*r][2*c + 1] = " "
                if walls & W_WALL:
                    buf[2*r + 1][2*c] = "│"
                else:
                    buf[2*r + 1][2*c] = " "

            walls: int = self._grid[r][self._cols - 1]
            if walls & E_WALL:
                buf[2*r + 1][2*self._cols] = "│"
            else:
                buf[2*r + 1][2*self._cols] = " "
        
        for c in range(self._cols):
            walls: int = self._grid[self._rows - 1][c]
            if walls & S_WALL:
                buf[2*self._rows][2*c + 1] = "─"
            else:
                buf[2*self._rows][2*c + 1] = " "

        return buf

    def _apply_overlays(self, buf: list[list[str]]) -> None:
        for r in range(self._rows):
            for c in range(self._cols):
                if self._grid[r][c] == 0xF:
                    buf[2*r + 1][2*c + 1] = "█"

        if self._show_path:
            for (r, c) in self.path:
                buf[2*r + 1][2*c + 1] = "*"
        
        er: int = self._entry[0]
        ec: int = self._entry[1]
        buf[2*er + 1][2*ec + 1] = "E"

        xr: int = self._exit[0]
        xc: int = self._exit[1]
        buf[2*xr + 1][2*xc + 1] = "X"

    def _render(self) -> None:
        term_cols: int = os.get_terminal_size().columns
        term_rows: int = os.get_terminal_size().lines

        if term_rows < self._char_rows or term_cols < self._char_cols:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(f"Terminal too small: need\
        {self._char_cols}x{self._char_rows}\n")
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
            sys.stdout.write(line + "\n")
        
        sys.stdout.write(" [p] Toggle Path  [c] Color  [r] Regen  [q] Quit\n")
        sys.stdout.flush()

    def run(self) -> None:
        global _resize_flag
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        signal.signal(signal.SIGWINCH, _on_resize)

        self._render()

        try:
            while True:
                if _resize_flag:
                    _resize_flag = False
                    self._render()
                
                key: str = _getch()

                if key == "q":
                    break
                
                elif key == "p":
                    self._show_path = not self._show_path
                    self._render()
                
                elif key == "c":
                    self._cycle_color()
                    self._render()
                
                elif key == "r":
                    self._on_regenerate()
                    self._render()
                    break
                
        finally:
            sys.stdout.write("\033[?25h")
            sys.stdout.write(f"\033[{self._char_rows + 3};1H")
            sys.stdout.flush()

def launch(
    grid: list[list[int]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> None:
    renderer: Renderer = Renderer(
        grid,
        entry,
        exit_,
        path,
        on_regenerate
    )
    renderer.run()

