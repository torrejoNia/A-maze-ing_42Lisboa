# render.py — Implementation Guide

Everything in this file lives in **`render.py`** only. No other files should be
touched at this stage.

No external libraries. Uses only Python built-ins:
- `sys` — writing to stdout
- `os` — getting terminal size
- `tty` + `termios` — raw keyboard input (single keypress, no Enter needed)
- `signal` — catching terminal resize events (`SIGWINCH`)
- `typing` — type hint helpers (`Callable`, `TypedDict`)

---

## Background knowledge you need first

### The Cell bitmask (`mazegen/cell.py`)

Each maze cell stores its walls as a 4-bit integer:

```
Bit 0 (LSB) = North  → 0b0001 = 1
Bit 1       = East   → 0b0010 = 2
Bit 2       = South  → 0b0100 = 4
Bit 3       = West   → 0b1000 = 8
```

A wall is **closed** when its bit is `1`, **open** when `0`.
Example: `0b1010` (hex `A`) → East and West walls are closed, North and South open.

`cell.walls` gives you the raw integer. Test a wall with:
```python
if cell.walls & 0b0001:   # North wall is closed
```

### The hex output file format

```
fcd6        ← row 0: 4 cells, one hex digit each
b5a4        ← row 1
9996        ← row 2

0,0         ← entry: col,row  (so row=0, col=0)
3,2         ← exit:  col,row  (so row=2, col=3)
SESES       ← path as cardinal directions from entry to exit
```

The path string is a sequence of `N`, `E`, `S`, `W` steps. Walking each step
from the entry cell gives you all cells on the solution path.

---

## ANSI escape codes — the only "graphics" you need

These are plain strings written to stdout. No library required.

### Cursor and screen control

```
\033[2J        clear the entire screen
\033[H         move cursor to top-left (row 1, col 1)
\033[R;CH      move cursor to row R, column C  (1-indexed)
\033[?25l      hide cursor
\033[?25h      show cursor (restore on exit!)
```

Combine clear + home into one write for a flicker-free redraw:
```python
sys.stdout.write("\033[2J\033[H")
```

### Colors (SGR sequences)

```
\033[0m         reset all attributes
\033[1m         bold
\033[3Xm        foreground color  (X = 0 black, 1 red, 2 green, 3 yellow,
                                       4 blue, 5 magenta, 6 cyan, 7 white)
\033[4Xm        background color  (same X values)
\033[9Xm        bright foreground (X same as above)
```

Examples:
```python
RED_BOLD  = "\033[1;31m"
CYAN      = "\033[36m"
YELLOW    = "\033[33m"
GREEN     = "\033[32m"
RESET     = "\033[0m"
```

To write a colored character:
```python
sys.stdout.write(f"{COLOR}X{RESET}")
```

### Getting terminal size

```python
cols, rows = os.get_terminal_size()
```

---

## Raw keyboard input (single keypress)

By default the terminal is in "cooked" mode — it buffers input until Enter.
To read one keypress at a time, switch to raw mode temporarily.

```python
import sys, tty, termios

def _getch() -> str:
    fd: int = sys.stdin.fileno()
    old_settings: list = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch: str = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch
```

`tty.setraw` disables line buffering and echo. `termios.tcsetattr` restores the
terminal no matter what (the `finally` block ensures this even on exceptions).

---

## Handling terminal resize (`SIGWINCH`)

When the user resizes the terminal, the OS sends the `SIGWINCH` signal.
You can catch it with the `signal` module:

```python
import signal

_resize_flag: bool = False

def _on_resize(signum: int, frame: object) -> None:
    global _resize_flag
    _resize_flag = True

signal.signal(signal.SIGWINCH, _on_resize)
```

In your event loop, check `_resize_flag` after each keypress and redraw if set.

---

## Step 1 — Imports and constants

At the top of the file, import everything you will need:

```python
import os
import sys
import signal
import tty
import termios
from typing import Callable, TypedDict
```

Then define all constants (module-level, no class):

```python
# Wall bitmasks — match Cell.WALLMAP in mazegen/cell.py
N_WALL: int = 0b0001
E_WALL: int = 0b0010
S_WALL: int = 0b0100
W_WALL: int = 0b1000

# ANSI color strings — applied around each character when printing
RESET:       str = "\033[0m"
COLOR_PATH:  str = ...   # yellow
COLOR_ENTRY: str = ...   # bold green
COLOR_EXIT:  str = ...   # bold red

# Wall color presets — cycled with the "c" key
WALL_COLORS: list[str] = [
    ...,   # white
    ...,   # cyan
    ...,   # green
    ...,   # red
]

# Maps a direction letter to its (row_delta, col_delta)
DIR_DELTA: dict[str, tuple[int, int]] = {
    "N": (-1,  0),
    "E": ( 0, +1),
    "S": (+1,  0),
    "W": ( 0, -1),
}

# Set to True by the SIGWINCH handler; checked in the event loop
_resize_flag: bool = False
```

---

## Step 2 — `_directions_to_cells(start, directions)`

Module-level helper. Converts a direction string into a list of `(row, col)` cells.

**Signature:**
```python
def _directions_to_cells(
    start: tuple[int, int],
    directions: str,
) -> list[tuple[int, int]]:
```

**Input:**
- `start` — `(row, col)` of the first cell (the entry point)
- `directions` — string like `"SESE"`

**Output:** ordered `list[tuple[int, int]]`, starting with `start`, one entry per step.

Walk each character in `directions`, look up its delta in `DIR_DELTA`, accumulate.

---

## Step 3 — `parse_hex_file(filepath)`

Module-level function. Parses the maze output file and returns structured data.

First define a `TypedDict` for the return type so it's self-documenting:

```python
class MazeData(TypedDict):
    grid:  list[list[int]]
    entry: tuple[int, int]
    exit_: tuple[int, int]
    path:  list[tuple[int, int]]
```

**Signature:**
```python
def parse_hex_file(filepath: str) -> MazeData:
```

**How to parse:**

1. Read the file. Split on `"\n\n"` to get two sections.
2. Section 1: each non-empty line is a grid row.
   Each character → `int(ch, 16)`. Build the 2-D list.
3. Section 2 (after the blank line): three non-empty lines.
   - Line 1: `"col,row"` → entry as `(row, col)` (note the order swap — col comes first in the file)
   - Line 2: `"col,row"` → exit as `(row, col)`
   - Line 3: direction string → pass to `_directions_to_cells(entry, ...)`

---

## Step 4 — `Renderer.__init__`

Create a class `Renderer`. Constructor signature:

```python
def __init__(
    self,
    grid: list[list[int]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> None:
```

Store all as `self._...` attributes. Also compute and store:

```python
self._rows:        int                       = len(grid)
self._cols:        int                       = len(grid[0])
self._char_rows:   int                       = 2 * self._rows + 1
self._char_cols:   int                       = 2 * self._cols + 1
self._show_path:   bool                      = False
self._color_index: int                       = 0
self._path_set:    frozenset[tuple[int,int]] = frozenset(path)
```

No `stdscr` parameter — we write directly to `sys.stdout`.

---

## Step 5 — `Renderer.from_cell_grid` (classmethod)

Alternate constructor accepting a 2-D list of `Cell` objects. Convert each
`cell.walls` to an int, then call the normal `__init__`.

```python
@classmethod
def from_cell_grid(
    cls,
    cells: list[list],          # list[list[Cell]] — avoid importing Cell here
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> "Renderer":
```

---

## Step 6 — Color helpers

### `_current_wall_color`

```python
def _current_wall_color(self) -> str:
```

Returns `WALL_COLORS[self._color_index]`.

### `_cycle_color`

```python
def _cycle_color(self) -> None:
```

Increments `self._color_index` by 1, wrapping with `%` against `len(WALL_COLORS)`.

---

## Step 7 — `_build_char_grid`

```python
def _build_char_grid(self) -> list[list[str]]:
```

Returns a 2-D list of single characters with dimensions `(char_rows) × (char_cols)`.

**Character buffer dimensions:** `(2M+1) rows × (2N+1) cols`

### Coordinate mapping

```
Cell (r, c) interior  →  char position (2r+1, 2c+1)
North wall of (r,c)   →  char position (2r,   2c+1)   "-" or " "
West  wall of (r,c)   →  char position (2r+1, 2c  )   "|" or " "
Corner                →  char position (2r,   2c  )   always "+"
```

### Algorithm

1. Create buffer: `[[" "] * char_cols for _ in range(char_rows)]`

2. Place `"+"` at every corner position `(2r, 2c)` for all valid `r`, `c`.

3. For every cell `(r, c)`, read its bitmask from `self._grid[r][c]`:
   - `N_WALL` bit set → `buf[2r][2c+1] = "-"` else `" "`
   - `W_WALL` bit set → `buf[2r+1][2c] = "|"` else `" "`

4. **East border** — for each row `r`, read `self._grid[r][cols-1]`:
   - `E_WALL` bit set → `buf[2r+1][2*cols] = "|"` else `" "`

5. **South border** — for each col `c`, read `self._grid[rows-1][c]`:
   - `S_WALL` bit set → `buf[2*rows][2c+1] = "-"` else `" "`

Return `buf`.

---

## Step 8 — `_apply_overlays`

```python
def _apply_overlays(self, buf: list[list[str]]) -> None:
```

Modifies the buffer in-place. No return value.

1. If `self._show_path`: for each `(r, c)` in `self._path`:
   `buf[2r+1][2c+1] = "*"`

2. Entry marker — always:
   `buf[2*er+1][2*ec+1] = "E"` where `(er, ec) = self._entry`

3. Exit marker — always (drawn last so it overrides `*`):
   `buf[2*xr+1][2*xc+1] = "X"` where `(xr, xc) = self._exit`

---

## Step 9 — `_render`

```python
def _render(self) -> None:
```

Writes the full maze to the terminal using ANSI codes.

### Check terminal size first

```python
term_cols: int
term_rows: int
term_cols, term_rows = os.get_terminal_size()

if term_rows < self._char_rows or term_cols < self._char_cols:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write(f"Terminal too small: need {self._char_cols}x{self._char_rows}\n")
    sys.stdout.flush()
    return
```

### Build and print the buffer

1. Call `_build_char_grid()` and `_apply_overlays(buf)`.
2. Move cursor to top-left: write `"\033[2J\033[H"`.
3. For each row in the buffer, build a single string for that row:
   - For each character, prepend the correct ANSI color based on the character:
     - `"E"` → `COLOR_ENTRY`
     - `"X"` → `COLOR_EXIT`
     - `"*"` → `COLOR_PATH`
     - `"+"`, `"-"`, `"|"` → `self._current_wall_color()`
     - `" "` → no color code needed
   - Always append `RESET` after a colored character.
4. Write each row string followed by `"\n"`.
5. Write the hint bar: `" [p] path  [c] color  [r] regen  [q] quit"`
6. `sys.stdout.flush()` at the end.

---

## Step 10 — `run`

```python
def run(self) -> None:
```

The main event loop. Sets up the terminal, runs until quit or regenerate.

### Setup

```python
sys.stdout.write("\033[?25l")   # hide cursor
sys.stdout.flush()
signal.signal(signal.SIGWINCH, _on_resize)
self._render()
```

### Loop (inside `try/finally`)

```python
global _resize_flag

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
            break
finally:
    sys.stdout.write("\033[?25h")                           # show cursor
    sys.stdout.write(f"\033[{self._char_rows + 3};0H")     # move below maze
    sys.stdout.flush()
```

---

## Step 11 — `launch`

```python
def launch(
    grid: list[list[int]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> None:
```

Module-level function — the **only** thing the main program needs to import.

Creates a `Renderer` and calls `run()`:

```python
def launch(grid, entry, exit_, path, on_regenerate):
    r: Renderer = Renderer(grid, entry, exit_, path, on_regenerate)
    r.run()
```

---

## Testing without the rest of the project

Create a file `test_maze.txt`:

```
fcd6
b5a4
9996

0,0
3,2
SESES
```

Then run:
```bash
python3 -c "
from render import parse_hex_file, launch
d = parse_hex_file('test_maze.txt')
launch(d['grid'], d['entry'], d['exit_'], d['path'], lambda: None)
"
```

Expected result:
- A colored maze grid appears in the terminal
- `E` visible in green at entry, `X` in red at exit
- Press `p` → path cells show as yellow `*`
- Press `c` → wall color changes
- Press `q` → terminal restores cleanly (cursor reappears)
- Resize window → redraws automatically

---

## Checklist

- [ ] Step 1 — Imports + constants (with type annotations)
- [ ] Step 2 — `_directions_to_cells(start: tuple[int,int], directions: str) -> list[tuple[int,int]]`
- [ ] Step 3 — `MazeData` TypedDict + `parse_hex_file(filepath: str) -> MazeData`
- [ ] Step 4 — `Renderer.__init__` (typed parameters + typed attributes)
- [ ] Step 5 — `Renderer.from_cell_grid(...) -> "Renderer"` classmethod
- [ ] Step 6 — `_current_wall_color(self) -> str` / `_cycle_color(self) -> None`
- [ ] Step 7 — `_build_char_grid(self) -> list[list[str]]`
- [ ] Step 8 — `_apply_overlays(self, buf: list[list[str]]) -> None`
- [ ] Step 9 — `_render(self) -> None`
- [ ] Step 10 — `run(self) -> None`
- [ ] Step 11 — `launch(...) -> None`
