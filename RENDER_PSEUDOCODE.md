# render.py — Pseudocode Guide

Step-by-step pseudocode for every function and class you need to implement.
Follow them in order — each step builds on the previous one.

---

## Overview of the file structure

```
render.py
│
├── IMPORTS
├── CONSTANTS & GLOBALS
│
├── MazeData (TypedDict)          ← return type for parse_hex_file
├── _getch() -> str               ← raw keyboard read
├── _on_resize(int, object)->None ← signal handler for terminal resize
├── _directions_to_cells(         ← convert "SESE" string to cell list
│       tuple[int,int], str
│   ) -> list[tuple[int,int]]
├── parse_hex_file(str)->MazeData ← read and parse the maze output file
│
├── class Renderer
│   ├── __init__(...)  -> None    ← store state, compute dimensions
│   ├── from_cell_grid(...) -> Renderer   ← alternate constructor
│   ├── _current_wall_color() -> str      ← ANSI string for wall color
│   ├── _cycle_color() -> None            ← advance color preset
│   ├── _build_char_grid() -> list[list[str]]  ← ASCII buffer
│   ├── _apply_overlays(list[list[str]]) -> None  ← path/entry/exit
│   ├── _render() -> None         ← full screen redraw
│   └── run() -> None             ← event loop
│
└── launch(...) -> None           ← public entry point
```

---

## Constants and globals

**What they are:**
Named values defined once at the top of the file so that the rest of the code
never uses magic numbers or raw strings.

**What to define:**

```
# Imports needed at the top of render.py
import os, sys, signal, tty, termios
from typing import Callable, TypedDict

# Wall bitmasks — match the bit positions in Cell.walls
N_WALL: int = 1   (binary 0001)
E_WALL: int = 2   (binary 0010)
S_WALL: int = 4   (binary 0100)
W_WALL: int = 8   (binary 1000)

# ANSI escape sequences
# Format: \033[ = escape + [,  then a code,  then m to end the sequence
RESET:       str = "\033[0m"    ← turns off all color and bold
COLOR_PATH:  str = "\033[33m"   ← yellow foreground    (used for "*")
COLOR_ENTRY: str = "\033[1;32m" ← bold + green          (used for "E")
COLOR_EXIT:  str = "\033[1;31m" ← bold + red            (used for "X")

# List of wall color options cycled with the "c" key
WALL_COLORS: list[str] = [
    "\033[37m",   ← white
    "\033[36m",   ← cyan
    "\033[32m",   ← green
    "\033[31m",   ← red
]

# ANSI foreground color reference:
#   30 black  | 31 red     | 32 green  | 33 yellow
#   34 blue   | 35 magenta | 36 cyan   | 37 white
#   90–97     = bright variants of the above
#   1;Xm      = bold + color X

# Direction → (row delta, col delta)
DIR_DELTA: dict[str, tuple[int, int]] = {
    "N": (-1,  0),
    "E": ( 0, +1),
    "S": (+1,  0),
    "W": ( 0, -1),
}

# Global boolean flag — set to True by the resize signal handler
_resize_flag: bool = False
```

---

## `MazeData` (TypedDict)

**What it is:**
A typed dictionary definition that describes the return value of `parse_hex_file`.
Using `TypedDict` lets type checkers (mypy) verify that all callers correctly
handle the parsed data, and makes the structure self-documenting.

**Type signature:**
```python
class MazeData(TypedDict):
    grid:  list[list[int]]
    entry: tuple[int, int]
    exit_: tuple[int, int]
    path:  list[tuple[int, int]]
```

No pseudocode needed — this is just a type declaration, not logic.

---

## `_getch`

**Type signature:**
```python
def _getch() -> str:
```

**What it does:**
Reads exactly one keypress from the keyboard without waiting for Enter and
without echoing the character to the screen.

**Why it's needed:**
By default the terminal buffers everything the user types until they press Enter
(called "cooked" mode). For a TUI we need to react instantly to each key.
`tty.setraw` switches the terminal to raw mode temporarily, and `termios`
saves and restores the original settings.

**Pseudocode:**
```
function _getch() -> str:
    fd: int = file descriptor of standard input
    old_settings: list = save current terminal settings for fd

    try:
        switch fd to raw mode (no buffering, no echo)
        ch: str = read exactly 1 character from standard input
    finally:
        restore old_settings on fd   ← always do this, even on error

    return ch
```

---

## `_on_resize`

**Type signature:**
```python
def _on_resize(signum: int, frame: object) -> None:
```

**What it does:**
A signal handler called automatically by the operating system whenever the
user resizes the terminal window. It sets a global flag so the event loop
knows a redraw is needed.

**Why it's needed:**
You can't check terminal size in the middle of a blocking `_getch()` call.
The OS sends `SIGWINCH` to the process on resize. By catching it with a
signal handler and setting a flag, the event loop can check after each
keypress and redraw when needed.

**Pseudocode:**
```
function _on_resize(signum: int, frame: object) -> None:
    set global _resize_flag to True
```

Note: `signum` and `frame` are passed by the OS. You don't use them — but the
signature must accept them because that is what `signal.signal` requires.

---

## `_directions_to_cells`

**Type signature:**
```python
def _directions_to_cells(
    start: tuple[int, int],
    directions: str,
) -> list[tuple[int, int]]:
```

**What it does:**
Converts a direction string (like `"SESE"`) into an ordered list of
`(row, col)` positions — one per step including the starting cell.

**Why it's needed:**
The maze file stores the solution path as a compact direction string, not as
a list of coordinates. To highlight the path visually, you need the actual
grid coordinates of every cell on the path.

**Pseudocode:**
```
function _directions_to_cells(
    start: tuple[int, int],
    directions: str,
) -> list[tuple[int, int]]:

    result: list[tuple[int, int]] = [start]
    current_row: int, current_col: int = start

    for each character ch in directions (uppercase):
        row_delta: int, col_delta: int = DIR_DELTA[ch]
        current_row = current_row + row_delta
        current_col = current_col + col_delta
        append (current_row, current_col) to result

    return result
```

**Example:**
```
start = (0, 0), directions = "SE"
→ step S: (0,0) + (1,0) = (1,0)
→ step E: (1,0) + (0,1) = (1,1)
→ result = [(0,0), (1,0), (1,1)]
```

---

## `parse_hex_file`

**Type signature:**
```python
def parse_hex_file(filepath: str) -> MazeData:
```

**What it does:**
Opens and parses a maze output file. Returns a `MazeData` dict with the grid,
entry position, exit position, and solution path.

**Why it's needed:**
The renderer needs structured data to work with. The file format is compact
and needs to be decoded: hex digits → wall bitmasks, coordinate strings →
`(row, col)` tuples, direction string → list of cells.

**Pseudocode:**
```
function parse_hex_file(filepath: str) -> MazeData:

    # --- 1. Read the file ---
    # Use `open(filepath)` as a context manager (with statement).
    # Call `.read()` on the file object to get the full content as one string.
    content: str = open(filepath).read()

    # --- 2. Split into two sections ---
    # The grid and the metadata are separated by a blank line ("\n\n").
    # Use content.split("\n\n", 1) — the second argument 1 means stop after
    # the first match, so you always get at most 2 parts.
    sections: list[str] = content.split("\n\n", 1)
    part1: str = sections[0]              ← always present: the hex grid rows
    part2: str = sections[1] if len(sections) > 1 else ""   ← metadata or ""

    # --- 3. Parse the grid ---
    # part1 looks like this (each line is one row of the maze):
    #   "fcd6\nb5a4\n9996"
    #
    # Step A: cut it into individual lines using .splitlines()
    #   ["fcd6", "b5a4", "9996"]
    all_lines: list[str] = part1.splitlines()

    # Step B: remove any blank lines that might appear (e.g. leading newlines)
    #   Loop through all_lines and keep only lines that are not empty.
    #   ln.strip() removes whitespace — if nothing is left, the line is blank.
    #   A blank string is falsy in Python, so `if ln.strip()` skips it.
    #
    #   Long form of what the list comprehension does:
    grid_lines: list[str] = []
    for ln: str in all_lines:
        if ln.strip():          ← True if the line has actual content
            grid_lines.append(ln)

    # Step C: for each line, convert every hex character into an integer
    #   "fcd6"  →  [15, 12, 13, 6]
    #   Each character is one cell's wall bitmask.
    #   int("f", 16) == 15,  int("3", 16) == 3, etc.
    grid: list[list[int]] = []
    for line: str in grid_lines:
        row: list[int] = []
        # .strip() cleans the line before iterating:
        #   "fcd6\r"  →  "fcd6"
        clean_line: str = line.strip()

        # Iterate over each character in the cleaned line.
        # A string in Python is iterable — each step gives one character.
        #   "fcd6"  →  "f", "c", "d", "6"
        for ch: str in clean_line:

            # int(ch, 16) converts a hex character to its integer value.
            # The second argument 16 means "read this as base 16 (hexadecimal)".
            #   int("f", 16) → 15
            #   int("c", 16) → 12
            #   int("d", 16) → 13
            #   int("6", 16) →  6
            cell_value: int = int(ch, 16)
            row.append(cell_value)

        # row is now one complete maze row, e.g. [15, 12, 13, 6]
        grid.append(row)

    # --- 4. Set defaults ---
    # These are used if the metadata section is missing or incomplete.
    entry: tuple[int, int] = (0, 0)
    exit_: tuple[int, int] = (0, 0)
    path:  list[tuple[int, int]] = []

    # --- 5. Parse metadata ---
    if part2:   ← only enter this block if part2 is a non-empty string

        # Step A: split part2 into clean lines, same technique as the grid.
        # part2 looks like:
        #   "0,0\n3,2\nSESES"
        all_meta: list[str] = part2.splitlines()

        meta_lines: list[str] = []
        for ln: str in all_meta:
            if ln.strip():               ← skip blank lines
                meta_lines.append(ln.strip())
        # meta_lines is now: ["0,0", "3,2", "SESES"]

        # Step B: entry coordinates (meta_lines[0])
        # The file stores coordinates as "col,row" — col comes FIRST.
        # Internally we always use (row, col), so we must swap them.
        #
        # Example: "0,0"
        #   .split(",")  →  ["0", "0"]
        #   parts[0] is col ("0"),  parts[1] is row ("0")
        #   entry = (int("0"), int("0")) = (0, 0)
        #
        # Example: "3,2"
        #   .split(",")  →  ["3", "2"]
        #   parts[0] is col ("3"),  parts[1] is row ("2")
        #   entry = (int("2"), int("3")) = (2, 3)
        if len(meta_lines) >= 1:
            parts: list[str] = meta_lines[0].split(",")
            col_str: str = parts[0]     ← first value is the column
            row_str: str = parts[1]     ← second value is the row
            entry = (int(row_str), int(col_str))   ← store as (row, col)

        # Step C: exit coordinates (meta_lines[1])
        # Exact same format and swap as the entry above.
        if len(meta_lines) >= 2:
            parts = meta_lines[1].split(",")
            col_str = parts[0]
            row_str = parts[1]
            exit_ = (int(row_str), int(col_str))

        # Step D: direction string (meta_lines[2])
        # The string is a sequence of N/E/S/W letters, e.g. "SESES".
        #
        # .strip()  — removes any accidental whitespace at the edges
        # .upper()  — normalises to uppercase so "sese" works too
        #
        # Example: "  seses\n"  →  .strip() → "seses"  →  .upper() → "SESES"
        #
        # Pass it to _directions_to_cells which will walk each letter
        # and return the full list of (row, col) cells on the solution path.
        if len(meta_lines) >= 3:
            direction_str: str = meta_lines[2].strip().upper()
            path = _directions_to_cells(entry, direction_str)

    # --- 6. Return ---
    return MazeData(grid=grid, entry=entry, exit_=exit_, path=path)
```

**Method reference:**
| Method | What it does here |
|---|---|
| `open(filepath)` | opens the file for reading (text mode, UTF-8 by default) |
| `.read()` | reads the entire file as a single `str` |
| `str.split(sep, maxsplit)` | splits on `sep` at most `maxsplit` times |
| `str.splitlines()` | splits on `\n`, `\r\n`, etc. — never adds empty trailing entry |
| `str.strip()` | removes leading/trailing whitespace (spaces, `\n`, `\r`) |
| `int(ch, 16)` | parses a single hex character into an integer (base 16) |
| `str.upper()` | converts direction string to uppercase so `"s"` works too |

---

## `class Renderer`

**What it is:**
The central class of the module. It owns all the state needed to display the
maze and react to user input. One instance lives as long as one maze is shown.
When the user presses `r` to regenerate, the old instance is discarded and a
new one is created with fresh data.

---

### `Renderer.__init__`

**Type signature:**
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

**What it does:**
Stores all the data the renderer needs and pre-computes a few derived values.

**Why pre-compute:**
`_char_rows` and `_char_cols` are used in almost every method. Computing them
once here avoids repeated arithmetic everywhere else.

**Pseudocode:**
```
method __init__(
    grid: list[list[int]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> None:

    self._grid:           list[list[int]]            = grid
    self._entry:          tuple[int, int]            = entry
    self._exit:           tuple[int, int]            = exit_
    self._path:           list[tuple[int, int]]      = path
    self._on_regenerate:  Callable[[], None]         = on_regenerate

    self._rows:           int                        = number of rows in grid
    self._cols:           int                        = number of columns in grid[0]
    self._char_rows:      int                        = 2 * self._rows + 1
    self._char_cols:      int                        = 2 * self._cols + 1

    self._show_path:      bool                       = False
    self._color_index:    int                        = 0
    self._path_set:       frozenset[tuple[int, int]] = frozenset(path)
```

---

### `Renderer.from_cell_grid` *(classmethod)*

**Type signature:**
```python
@classmethod
def from_cell_grid(
    cls,
    cells: list[list],                  # list[list[Cell]]
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> "Renderer":
```

**What it does:**
An alternate way to create a `Renderer` when you have a 2D list of `Cell`
objects from the maze generator instead of raw integers.

**Why it's needed:**
The rest of the project uses `Cell` objects internally. This method bridges
the gap between the generator's output format and what the renderer expects.

**Pseudocode:**
```
classmethod from_cell_grid(
    cells: list[list[Cell]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> Renderer:

    grid: list[list[int]] = []

    for each row in cells:
        new_row: list[int] = []
        for each cell in row:
            append cell.walls to new_row    ← .walls is the bitmask int
        append new_row to grid

    return Renderer(grid, entry, exit_, path, on_regenerate)
```

---

### `Renderer._current_wall_color`

**Type signature:**
```python
def _current_wall_color(self) -> str:
```

**What it does:**
Returns the ANSI color string for the currently selected wall color preset.

**Why it's a method:**
`self._color_index` can change at runtime (with `c`). Wrapping the lookup
in a method means every drawing operation always gets the current color
without needing to pass it around.

**Pseudocode:**
```
method _current_wall_color() -> str:
    return WALL_COLORS[self._color_index]
```

---

### `Renderer._cycle_color`

**Type signature:**
```python
def _cycle_color(self) -> None:
```

**What it does:**
Advances to the next wall color preset, wrapping back to the first after
the last one.

**Pseudocode:**
```
method _cycle_color() -> None:
    self._color_index = (self._color_index + 1) modulo len(WALL_COLORS)
```

---

### `Renderer._build_char_grid`

**Type signature:**
```python
def _build_char_grid(self) -> list[list[str]]:
```

**What it does:**
Converts the numeric maze grid into a 2D list of single characters that can
be printed to the terminal. This is the core rendering algorithm.

**Why this shape:**
For a maze with M rows and N columns of cells, the printed grid needs
`(2M + 1)` character rows and `(2N + 1)` character columns. The extra
row/column comes from the borders and the wall characters that sit between
cells.

**Coordinate mapping (memorise this):**
```
Grid cell (r, c)      ──►  character at (2r+1, 2c+1)   ← cell interior " "
North wall of (r,c)   ──►  character at (2r,   2c+1)   ← "-" or " "
West  wall of (r,c)   ──►  character at (2r+1, 2c  )   ← "|" or " "
Grid intersection     ──►  character at (2r,   2c  )   ← always "+"
```

**Pseudocode:**
```
method _build_char_grid() -> list[list[str]]:

    # 1. Create blank buffer
    # We need a 2D grid of characters, one " " per position.
    # Build it as a list of rows, where each row is a list of spaces.
    #
    # Start with one row of spaces:
    #   [" "] * char_cols  →  [" ", " ", " ", " ", " "]  (for char_cols = 5)
    #
    # Repeat that for every row:
    #   [[" ", " ", ...], [" ", " ", ...], ...]  (char_rows times)
    #
    # In Python this is written as a list comprehension.
    # If that syntax is unfamiliar, here is the explicit loop that does
    # exactly the same thing:
    #
    buf: list[list[str]] = []
    for _ in range(self._char_rows):   ← run once per row (_  means we don't use the counter)
        row: list[str] = [" "] * self._char_cols   ← make one row of spaces
        #   [" "] * 5  →  [" ", " ", " ", " ", " "]
        buf.append(row)
    #
    # After this loop, for a 2×2 maze (char_rows=5, char_cols=5) buf is:
    #   [" ", " ", " ", " ", " "]   ← row 0
    #   [" ", " ", " ", " ", " "]   ← row 1
    #   [" ", " ", " ", " ", " "]   ← row 2
    #   [" ", " ", " ", " ", " "]   ← row 3
    #   [" ", " ", " ", " ", " "]   ← row 4
    # All positions are blank — walls and markers will be filled in next.

    # 2. Place "+" at every grid-line intersection
    for r: int from 0 to self._rows (inclusive):
        for c: int from 0 to self._cols (inclusive):
            buf[2*r][2*c] = "+"

    # 3. Fill in each cell's north and west walls
    for r: int from 0 to self._rows - 1:
        for c: int from 0 to self._cols - 1:
            walls: int = self._grid[r][c]

            if walls has N_WALL bit set:
                buf[2*r][2*c + 1] = "-"
            else:
                buf[2*r][2*c + 1] = " "

            if walls has W_WALL bit set:
                buf[2*r + 1][2*c] = "|"
            else:
                buf[2*r + 1][2*c] = " "

        # 4. East border — rightmost cell of this row
        walls: int = self._grid[r][self._cols - 1]
        if walls has E_WALL bit set:
            buf[2*r + 1][2 * self._cols] = "|"
        else:
            buf[2*r + 1][2 * self._cols] = " "

    # 5. South border — bottom row of cells
    for c: int from 0 to self._cols - 1:
        walls: int = self._grid[self._rows - 1][c]
        if walls has S_WALL bit set:
            buf[2 * self._rows][2*c + 1] = "-"
        else:
            buf[2 * self._rows][2*c + 1] = " "

    return buf
```

**Visualised for a 2×2 maze (char grid is 5×5):**
```
+ - + - +       ← row 0: corners + north walls
|   |   |       ← row 1: west walls + cell interiors
+ - +   +       ← row 2: corners + north walls of row 1
|   |   |       ← row 3: west walls + cell interiors
+ - + - +       ← row 4: corners + south walls
```

---

### `Renderer._apply_overlays`

**Type signature:**
```python
def _apply_overlays(self, buf: list[list[str]]) -> None:
```

**What it does:**
Stamps special characters on top of the base character grid to mark the
solution path, entry, and exit. Modifies `buf` in-place — no return value.

**Why overlays are separate:**
The character grid represents pure wall structure. Keeping overlays separate
makes it easy to toggle the path on/off without rebuilding the whole grid.

**Order matters:** entry and exit are stamped last so they are never hidden
by a path `*` marker.

**Pseudocode:**
```
method _apply_overlays(buf: list[list[str]]) -> None:

    # Path markers — only if path is visible
    if self._show_path is True:
        for each (r, c): tuple[int, int] in self._path:
            buf[2*r + 1][2*c + 1] = "*"

    # Entry marker — always shown
    er: int, ec: int = self._entry
    buf[2*er + 1][2*ec + 1] = "E"

    # Exit marker — always shown, drawn after path so it overrides "*"
    xr: int, xc: int = self._exit
    buf[2*xr + 1][2*xc + 1] = "X"
```

---

### `Renderer._render`

**Type signature:**
```python
def _render(self) -> None:
```

**What it does:**
Performs a complete screen redraw: clears the terminal, builds the character
buffer, applies overlays, and prints everything with the correct ANSI colors.

**Why a full redraw every time:**
Mazes are small. A full redraw is simpler, correct, and fast enough that the
user won't notice any flicker.

**Pseudocode:**
```
method _render() -> None:

    # 0. Check terminal size
    term_cols: int, term_rows: int = os.get_terminal_size()

    if term_rows < self._char_rows OR term_cols < self._char_cols:

        # Clear the screen and move the cursor to the top-left.
        # "\033[2J" = erase entire screen
        # "\033[H"  = move cursor to row 1, col 1
        # They are written together as one call so they happen atomically.
        sys.stdout.write("\033[2J\033[H")

        # Build the message using an f-string so the actual numbers appear.
        # Example: if char_cols=41 and char_rows=21 the message will be:
        #   "Terminal too small: need 41x21"
        msg: str = f"Terminal too small: need {self._char_cols}x{self._char_rows}"
        sys.stdout.write(msg + "\n")

        # flush() forces Python to send everything in the output buffer to
        # the terminal immediately — without it the message may not appear.
        sys.stdout.flush()

        return   ← abort — terminal is too small to draw anything

    # 1. Build the character buffer
    buf: list[list[str]] = self._build_char_grid()
    self._apply_overlays(buf)

    # 2. Clear the screen and move the cursor to the top-left corner.
    # This is the same two-code sequence used in the "too small" check above:
    #   "\033[2J"  — erases everything currently visible on the screen
    #   "\033[H"   — moves the cursor to row 1, col 1 (the top-left corner)
    # Writing them together means the next character we print lands at (0, 0).
    sys.stdout.write("\033[2J\033[H")

    # 3. Print each row with colors
    for row_index: int from 0 to self._char_rows - 1:
        line: str = ""

        for each character ch: str in buf[row_index]:
            if ch == "E":
                line += COLOR_ENTRY + "E" + RESET
            else if ch == "X":
                line += COLOR_EXIT + "X" + RESET
            else if ch == "*":
                line += COLOR_PATH + "*" + RESET
            else if ch is "+", "-", or "|":
                line += self._current_wall_color() + ch + RESET
            else:
                line += ch   ← plain space, no color escape needed

        write line + "\n" to stdout

    # 4. Print the hint bar below the maze
    write " [p] path  [c] color  [r] regen  [q] quit\n" to stdout

    # 5. Flush so everything appears at once
    flush stdout
```

---

### `Renderer.run`

**Type signature:**
```python
def run(self) -> None:
```

**What it does:**
The main interactive loop. Sets up the terminal, draws the initial maze, then
waits for keypresses and reacts to them until the user quits or regenerates.

**Why try/finally:**
The terminal must always be restored (cursor shown) even if the program crashes
or the user sends Ctrl-C. `try/finally` guarantees the cleanup code runs.

**Pseudocode:**
```
method run() -> None:

    # Setup
    write ANSI "hide cursor" sequence to stdout
    flush stdout
    # Tell the OS: "when the terminal is resized, call _on_resize automatically".
    # Use signal.signal() which takes two arguments:
    #   1. the signal to watch for — signal.SIGWINCH is the resize signal
    #   2. the function to call when that signal fires — our _on_resize handler
    #
    # In Python:
    #   signal.signal(signal.SIGWINCH, _on_resize)
    #                 ↑                ↑
    #                 which signal     which function to call
    #
    # Note: pass _on_resize without parentheses — you are passing the function
    # itself as an object, NOT calling it. Writing _on_resize() would call it
    # immediately instead of registering it.

    self._render()   ← draw immediately before entering the loop

    try:
        loop forever:
            # Handle resize between keypresses
            if global _resize_flag is True:
                _resize_flag = False
                self._render()

            key: str = _getch()   ← blocks until user presses a key

            if key == "q":
                break

            else if key == "p":
                self._show_path = not self._show_path
                self._render()

            else if key == "c":
                self._cycle_color()
                self._render()

            else if key == "r":
                self._on_regenerate()
                break   ← caller builds a new Renderer with fresh data

    finally:
        # This block runs no matter how the loop ended — normal quit,
        # regenerate, or even an unexpected crash (Ctrl-C etc.).

        # Show the cursor again — we hid it at the start of run().
        # "\033[?25h" is the exact opposite of "\033[?25l"
        sys.stdout.write("\033[?25h")

        # Move the cursor to a row below the maze so the shell prompt
        # appears cleanly underneath it instead of on top of the drawing.
        #
        # The ANSI sequence to move the cursor to a specific row is:
        #   "\033[{row};{col}H"   ← row and col are 1-indexed
        #
        # We want to land just below the maze and the hint bar, so we use:
        #   row = self._char_rows + 3   (maze height + hint line + one gap)
        #   col = 1                     (left edge)
        #
        # Example: for a 4-row maze, char_rows = 9, so we move to row 12.
        #   "\033[12;1H"
        sys.stdout.write(f"\033[{self._char_rows + 3};1H")

        sys.stdout.flush()   ← send both sequences to the terminal immediately
```

---

## `launch`

**Type signature:**
```python
def launch(
    grid: list[list[int]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> None:
```

**What it does:**
The single public function that the main program imports. Creates a `Renderer`
and starts it. The main program never touches `Renderer` directly.

**Why this wrapper:**
It keeps the public API minimal — one import, one call. If you ever swap the
rendering backend, only this function changes.

**Pseudocode:**
```
function launch(
    grid: list[list[int]],
    entry: tuple[int, int],
    exit_: tuple[int, int],
    path: list[tuple[int, int]],
    on_regenerate: Callable[[], None],
) -> None:

    renderer: Renderer = Renderer(grid, entry, exit_, path, on_regenerate)
    renderer.run()
```

---

## Build order checklist

Implement in this order — each item depends on the ones above it.

- [ ] 1. Imports + constants (with type annotations)
- [ ] 2. `MazeData` TypedDict
- [ ] 3. `_getch() -> str`
- [ ] 4. `_on_resize(signum: int, frame: object) -> None`
- [ ] 5. `_directions_to_cells(tuple[int,int], str) -> list[tuple[int,int]]`
- [ ] 6. `parse_hex_file(str) -> MazeData`
- [ ] 7. `Renderer.__init__(...) -> None`
- [ ] 8. `Renderer.from_cell_grid(...) -> Renderer`
- [ ] 9. `Renderer._current_wall_color() -> str` + `_cycle_color() -> None`
- [ ] 10. `Renderer._build_char_grid() -> list[list[str]]`
- [ ] 11. `Renderer._apply_overlays(list[list[str]]) -> None`
- [ ] 12. `Renderer._render() -> None`
- [ ] 13. `Renderer.run() -> None`
- [ ] 14. `launch(...) -> None`

---

## Quick-test at each stage

After step 6, test parsing alone:
```bash
python3 -c "from render import parse_hex_file; print(parse_hex_file('test_maze.txt'))"
```

After step 10, test the character buffer alone:
```bash
python3 -c "
from render import parse_hex_file, Renderer
d = parse_hex_file('test_maze.txt')
r = Renderer(d['grid'], d['entry'], d['exit_'], d['path'], lambda: None)
buf = r._build_char_grid()
for row in buf:
    print(''.join(row))
"
```

After step 14, full interactive test:
```bash
python3 -c "
from render import parse_hex_file, launch
d = parse_hex_file('test_maze.txt')
launch(d['grid'], d['entry'], d['exit_'], d['path'], lambda: None)
"
```
