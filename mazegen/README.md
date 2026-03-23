*This project has been created as part of the 42 curriculum by esnavarr, mju-ferr.*

# Reusable Module: `mazegen`

The maze generation logic lives in the standalone `mazegen` package located in
the `mazegen/` directory. It is distributed as a pip-installable wheel.

## Maze Generation Algorithms

Two algorithms are available:

### DFS — randomised depth-first search (default)

1. All cells start with every wall closed (bitmask `0b1111`).
2. Start a stack at the entry cell, mark it visited.
3. While the stack is non-empty:
   - Look at all unvisited, in-bounds neighbours not reserved for the logo.
   - If any exist, pick one at random, remove the shared wall, push the
     neighbour onto the stack, mark it visited.
   - Otherwise backtrack (pop the stack).
4. For *imperfect* mazes, a second pass opens every dead-end into a corridor,
   creating extra loops.

**Character:** long winding corridors, sparse dead ends, river-like paths.

### Prim's — randomised Prim's algorithm

1. Start with the entry cell in the visited set and add its neighbours to a
   frontier list.
2. While the frontier is non-empty:
   - Pick a random frontier edge (visited cell → unvisited neighbour).
   - If the neighbour is already visited, discard the edge.
   - Otherwise open the wall between them, add the neighbour to visited, and
     add its unvisited neighbours to the frontier.

**Character:** bushy, many short dead ends radiating outward — structurally
opposite to DFS.

---

## Logo

A pixel-art logo is reserved as a solid block of cells in the centre of every
maze. By default this is the built-in `42` pattern. 

### Logo file format

- Each non-blank, non-comment line is one row of the pattern.
- `X` = filled cell (wall kept closed, unreachable by the solver).
- `.` = empty cell (treated as normal maze).
- All rows must have the same width.
- Lines starting with `#` and blank lines are ignored.

```
# my-logo.logo
X.X.XXX
X.X...X
XXX.XXX
..X.X..
..X.XXX
```

The logo is automatically centred in the maze. The maze must be at least
`logo_width + 2` columns wide and `logo_height + 2` rows tall; a clear error
is raised otherwise.

---

### Installation

Create a virtual environment in the same folder where you cloned the repository:

```bash
python3 -m venv venv
```
Activate virtual environment

```bash
source venv/bin/activate
```
Installing the module

```bash
pip install mazegen-1.0.0-py3-none-any.whl
```

Or from source:

```bash
pip install build
python -m build --outdir .
pip install mazegen-1.0.0-py3-none-any.whl
```
Exit venv when done

```bash
deactivate
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
    width=20,           # number of columns
    height=20,          # number of rows
    entry=(0, 0),       # entry as (x, y) = (col, row)
    exit=(19, 19),      # exit  as (x, y) = (col, row)
    perfect=True,       # True → no loops; False → dead-ends opened
    seed=42,            # omit or pass 0 for a random maze
    algorithm="prim",   # "dfs" (default) or "prim"
    logo_pattern=[      # custom pixel-art logo; omit for built-in "42"
        "X.X.XXX",
        "X.X...X",
        "XXX.XXX",
        "..X.X..",
        "..X.XXX",
    ],
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