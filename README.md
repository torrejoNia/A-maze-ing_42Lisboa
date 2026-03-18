*This project has been created as part of the 42 curriculum by esnavarr, mju-ferr.*

# A-Maze-ing

## Description

A-Maze-ing is a terminal-based maze generator and solver. Given a configuration
file, the program generates a 2D maze using a randomised depth-first search
algorithm, solves it with breadth-first search, writes the result to an output
file, and renders everything in an interactive ASCII TUI with step-by-step
animations for both generation and path discovery.

Key features:
- Perfect (no loops) or imperfect maze generation, controlled via config
- Optional seed for reproducible mazes
- "42" logo embedded as reserved cells in the centre of every maze
- Cell-by-cell generation animation in the terminal
- Toggleable animated path overlay (`p`)
- Cyclic wall colour themes (`c`)
- In-place regeneration without leaving the alternate screen (`r`)
- Alternate screen buffer — the terminal scroll history is never polluted

---

## Instructions

### Requirements

- Python 3.10 or later
- `flake8` and `mypy` (installed via `make install`)

### Installation

```bash
# Clone the repo, then inside the project root:
make install
```

### Running

```bash
make run          # runs a_maze_ing.py with config.txt
make debug        # same, but under pdb
```

Or directly:

```bash
python3 a_maze_ing.py config.txt
```

### Lint

```bash
make lint         # flake8 + mypy (standard)
make lint-strict  # flake8 + mypy --strict
```

### Clean

```bash
make clean        # removes __pycache__, .mypy_cache, *.pyc, dist/
```

### Building the mazegen package

```bash
# In a clean virtualenv:
pip install build
python -m build --outdir .
# Produces mazegen-1.0.0-py3-none-any.whl and mazegen-1.0.0.tar.gz
```

---

## Config File

The config file uses a simple `KEY=VALUE` format — one key per line. Blank
lines and lines starting with `#` are ignored.

| Key           | Type    | Required | Description                                        |
|---------------|---------|----------|----------------------------------------------------|
| `WIDTH`       | int     | yes      | Number of columns in the maze (must be ≥ 2)        |
| `HEIGHT`      | int     | yes      | Number of rows in the maze (must be ≥ 2)           |
| `ENTRY`       | `x,y`   | yes      | Entry cell in **col,row** order (0-indexed)        |
| `EXIT`        | `x,y`   | yes      | Exit cell in **col,row** order (0-indexed)         |
| `OUTPUT_FILE` | string  | yes      | Path where the maze file will be written           |
| `PERFECT`     | bool    | yes      | `True` for perfect maze, `False` for imperfect     |
| `SEED`        | int     | no       | RNG seed for reproducible generation               |

Example `config.txt`:

```
WIDTH=20
HEIGHT=20
ENTRY=0,0
EXIT=19,19
OUTPUT_FILE=maze.txt
PERFECT=True
SEED=42
```

Coordinates follow the file convention `col,row` (i.e. x,y). The program
converts them internally to `(row, col)` for grid indexing.

---

## Maze Generation Algorithm

The maze is generated using **randomised depth-first search** (recursive
backtracker).

### How it works

1. All cells start with every wall closed (bitmask `0b1111`).
2. Start a stack at the entry cell, mark it visited.
3. While the stack is non-empty:
   - Look at all unvisited, in-bounds neighbours that are not reserved for
     the "42" logo.
   - If any exist, pick one at random, remove the shared wall, push the
     neighbour onto the stack, mark it visited.
   - Otherwise backtrack (pop the stack).
4. For *imperfect* mazes, a second pass opens every dead-end into a corridor,
   creating extra loops.

### Why DFS?

DFS was chosen because:
- It naturally produces **long winding corridors** with few branches, giving
  visually interesting mazes without post-processing.
- It is simple to implement correctly and easy to audit.
- The stack-based iterative form avoids Python's recursion limit for large
  grids.
- It supports a seed trivially — a single `random.seed(seed)` call makes the
  entire generation deterministic and reproducible.

---

## Reusable Module: `mazegen`

The maze generation logic lives in the standalone `mazegen` package located in
the `mazegen/` directory. It is distributed as a pip-installable wheel.

### Installation

```bash
pip install mazegen-1.0.0-py3-none-any.whl
```

Or from source:

```bash
pip install build
python -m build --outdir .
pip install mazegen-1.0.0-py3-none-any.whl
```

### Basic usage

```python
from mazegen import Maze

# Generate a 15×15 perfect maze with default entry (0,0) and exit (14,14)
maze = Maze()

# Print wall values as hex digits
maze.print_hex()
```

### Custom parameters

```python
from mazegen import Maze

maze = Maze(
    width=20,        # number of columns
    height=20,       # number of rows
    entry=(0, 0),    # entry as (x, y) = (col, row)
    exit=(19, 19),   # exit  as (x, y) = (col, row)
    perfect=True,    # True → no loops; False → dead-ends opened
    seed=42,         # omit or pass 0 for a random maze
)
```

All parameters have defaults and are optional.

### Accessing the maze structure

```python
# maze.grid is a 2D list of Cell objects indexed as grid[y][x]
cell = maze.grid[0][0]      # top-left cell
print(cell.walls)           # integer bitmask: N=1, E=2, S=4, W=8

# Check individual walls
print(cell.has_wall("N"))   # True if north wall is closed
print(cell.has_wall("E"))   # True if east wall is closed

# maze dimensions
print(maze.width, maze.height)

# entry and exit coordinates (x, y) = (col, row)
print(maze.entry)   # e.g. (0, 0)
print(maze.exit)    # e.g. (19, 19)
```

### Accessing the solution

The `mazegen` package exposes the maze structure only. To solve, use the
`solve_maze` function from `solver.py` (included in this repository but not
part of the installable package):

```python
from mazegen import Maze
from solver import solve_maze

maze = Maze(width=10, height=10, entry=(0, 0), exit=(9, 9), seed=1)
path = solve_maze(maze)
print(path)         # e.g. "SSENNEESE..."
print(len(path))    # number of steps
```

`solve_maze` uses BFS and returns a direction string (`N`, `E`, `S`, `W`).

### Regenerating a maze in-place

```python
maze.generate()   # re-runs DFS with the same (or new random) seed
```

---

## Team and Project Management

### Team members

| Login     | Role                                                                 |
|-----------|----------------------------------------------------------------------|
| esnavarr  | Maze generation module (`mazegen`), `Cell` class, DFS algorithm, solver (BFS), packaging |
| mju-ferr  | TUI renderer (`render.py`), ANSI animations, terminal raw-mode input, writer, `a_maze_ing.py` wiring, config parser|

### Planning

The project was split into three phases:

1. **Core** — `mazegen` module (maze generation + Cell), solver, config parser.
   This phase was completed largely as planned with the main unexpected cost
   being the coordinate-system translation between the Maze class (`x,y`) and
   the internal grid/renderer (`row,col`).

2. **Rendering** — ASCII TUI, ANSI colours, raw-mode keyboard input. The
   original plan assumed a simple blocking `getch()` per frame; the actual
   implementation needed `select.select` with a timeout to drive two
   independent animation timers (generation and path) without blocking.

3. **Integration & polish** — Alternate screen buffer, scroll-blocking,
   packaging, README. This phase expanded significantly as we added the
   generation animation and the `mazegen` pip package requirement.

### What worked well

- Separating concerns into dedicated files (`config.py`, `writer.py`,
  `solver.py`, `render.py`, `a_maze_ing.py`) made parallel development easy.
- The bitmask wall representation is compact, fast, and maps directly to
  the hex file format with no conversion.
- Using `select.select` with a per-phase frame delay gave smooth, independent
  control over the two animations without threading.

### What could be improved

- The coordinate system has three representations (file `col,row`, internal
  `(row,col)`, Maze `(x,y)`). Unifying these from the start would have
  avoided several late-stage bugs.
- The renderer's `_build_char_grid` and `_apply_overlays` methods are long;
  they could be broken into smaller helpers.
- Adding unit tests earlier would have caught the raw-mode buffering bug
  before integration.

### Tools used

- **Python 3.10** — language
- **flake8** — style linting
- **mypy** — static type checking
- **pdb** — debugging
- **build** — packaging (`pyproject.toml` + setuptools)

---

## Resources

### Maze generation

- [Buckblog: Maze generation algorithms](https://weblog.jamisbuck.org/2011/2/7/maze-generation-algorithm-recap)
  Overview and interactive demos of common algorithms.
- [Wikipedia — Maze generation algorithm](https://en.wikipedia.org/wiki/Maze_generation_algorithm)

### BFS / pathfinding

- [Wikipedia — Breadth-first search](https://en.wikipedia.org/wiki/Breadth-first_search)
- [Red Blob Games — Introduction to A*](https://www.redblobgames.com/pathfinding/a-star/introduction.html)
  Explains BFS, Dijkstra, and A* with visual walkthroughs.

### Python packaging

- [Python Packaging User Guide](https://packaging.python.org/en/latest/)
- [pyproject.toml reference (setuptools)](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)

### Terminal / ANSI

- [ANSI escape codes — Wikipedia](https://en.wikipedia.org/wiki/ANSI_escape_code)
- [Python `termios` documentation](https://docs.python.org/3/library/termios.html)

### AI usage

**AI was used throughout the project for:**

- Researching different execution methods and for quick Q&As
- Debugging terminal-input issues (phantom keypresses due to Python
  `TextIOWrapper` buffering — fixed with `os.read` + `termios.tcflush`).
- Writing and iterating Google-style docstrings across all modules.
- Writing this README.
