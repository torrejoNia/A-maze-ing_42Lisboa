import sys
import random

from cell import Cell


ALL_WALLS = 0b1111
"""Bitmask representing a cell with all four walls closed."""

DIRECTIONS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}
"""Coordinate offsets for moving north, east, south, and west."""

OPPOSITE = {
    "N": "S",
    "E": "W",
    "S": "N",
    "W": "E",
}
"""Opposite wall direction used when opening passages between cells."""

class MazeError(Exception):
    """Custom exception for maze-related errors."""
    pass


class Maze:
    """Represent a maze and provide generation utilities.

    A maze is built as a 2D grid of Cell objects, where each cell stores
    wall information using a 4-bit mask.

    Attributes:
        width: Number of columns in the maze.
        height: Number of rows in the maze.
        entry: Starting coordinate of the maze.
        exit: Exit coordinate of the maze.
        perfect: If True, generate a perfect maze (no loops).
        seed: Random seed for reproducible generation.
        logo: Coordinates reserved for the 42 logo.
        grid: 2D list of Cell objects.
    """

    def __init__(
            self,
            width: int = 15,
            height: int = 15,
            entry: tuple[int, int] = (0, 0),
            exit: tuple[int, int] = (14, 14),
            perfect: bool = False,
            seed: int = 0
            ) -> None:
        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit
        self.perfect = perfect
        self.seed = seed
        self.logo = self._logo_cells()
        self.grid = [
            [Cell() for _ in range(self.width)]
            for _ in range(self.height)
        ]

        # Validate maze dimensions.
        if self.width <= 1:
            raise ValueError("Maze width invalid, must be more than 1")
        if self.height <= 1:
            raise ValueError("Maze height invalid, must be more than 1")
        # Validate entry coordinate.
        x, y = self.entry
        if not 0 <= x < width or not 0 <= y < height:
            raise ValueError("Entry coordinates are out of bounds.")
        # Validate exit coordinate.
        x, y = self.exit
        if not 0 <= x < width or not 0 <= y < height:
            raise ValueError("Exit coordinates are out of bounds.")
        # Entry and exit must be different.
        if self.entry == self.exit:
            raise ValueError("Entry and exit share coordinates.")
            

        self.generate()

    def __repr__(self) -> str:
        """Return user-friendly maze representation."""
        return f"Maze({self.width=}, " \
               f"{self.height=}, " \
               f"{self.entry=}, " \
               f"{self.exit=}, " \
               f"{self.perfect=}, " \
               f"{self.seed=}" \
                ")".replace("self.", "")

    def generate(self) -> None:
        """Generate maze passages using depth-first search."""
        if self.seed:
            random.seed(self.seed)

        # Reset every cell to fully closed.
        for row in self.grid:
            for cell in row:
                cell.walls = ALL_WALLS

        # DFS starts at entry.
        visited = {self.entry}
        stack = [self.entry]

        while stack:
            current = stack[-1]
            x, y = current
            # Get unvisited neighbors not reserved by logo.
            unvisited = []
            for nx, ny in self._neighbors(x, y):
                if (nx, ny) not in visited and (nx, ny) not in self.logo:
                    unvisited.append((nx, ny))

            if unvisited:
                # Randomly extend maze path.
                neighbor = random.choice(unvisited)
                self._knock_down_wall(current, neighbor)
                visited.add(neighbor)
                stack.append(neighbor)
            else:
                # Backtrack when no neighbors remain.
                stack.pop()

        if not self.perfect:
            self._open_dead_ends()

    def _neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """Return neighboring coordinates inside maze bounds."""
        neighbors = []

        for dx, dy in DIRECTIONS.values():
            nx = x + dx
            ny = y + dy

            if 0 <= nx < self.width and 0 <= ny < self.height:
                neighbors.append((nx, ny))

        return neighbors

    def _knock_down_wall(
        self,
        current: tuple[int, int],
        neighbor: tuple[int, int],
    ) -> None:
        """Remove walls between two adjacent cells."""

        x1, y1 = current
        x2, y2 = neighbor

        dx = x2 - x1
        dy = y2 - y1

        for direction, (mx, my) in DIRECTIONS.items():
            if (dx, dy) == (mx, my):
                self.grid[y1][x1].open_wall(direction)
                self.grid[y2][x2].open_wall(OPPOSITE[direction])
                return

    def _open_dead_ends(self) -> None:
        """Convert all eligible dead-ends into corridors."""
        # Which dead-end orientation corresponds to which direction.
        dead_end_targets = {
            0b1110: (0, +1), # north open → knock down south
            0b1101: (-1, 0), # east open → knock down west
            0b1011: (0, -1), # south open → knock down north
            0b0111: (+1, 0) # west open → knock down east
        }

        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                # Check that we're dealing with any of the dead-end variants.
                if cell.walls not in dead_end_targets:
                    continue

                direction = dead_end_targets[cell.walls]
                nx, ny = (direction[0] + x, direction[1] + y)  # Target cell.
                # Validate that the target is within the maze bounds,
                # and that the target is not part of the logo.
                if 0 <= nx < self.width and 0 <= ny < self.height \
                        and (nx, ny) not in self.logo:
                    self._knock_down_wall((x, y), (nx, ny))

    def _logo_cells(self) -> set[tuple[int, int]]:
        """Return coordinates reserved for the central '42' logo."""
        
        min_width = 9
        min_height = 7

        #if self.width < min_width or self.height < min_height:
            #raise ValueError("Maze too small for '42' logo .")


        if self.width < min_width or self.height < min_height:
            print(
                f"Maze too small for '42' logo "
                f"(minimum {min_width}x{min_height}, got {self.width}x{self.height})",
                file=sys.stderr,
            )
            return set()

        center_x = self.width // 2
        center_y = self.height // 2

        # Pixel art pattern for "42" (relative offsets from center-left)
        # Each tuple is (col_offset, row_offset) from anchor point
        four = [
            (0, 0), (0, 1), (0, 2),          # left vertical
                    (1, 2), (2, 2),          # horizontal bar
                    (2, 0), (2, 1), (2, 3), (2, 4)  # right vertical
        ]
        two = [
            (4, 0), (5, 0), (6, 0),          # top bar
                            (6, 1),          # top-right
            (4, 2), (5, 2), (6, 2),          # middle bar
            (4, 3),                          # bottom-left
            (4, 4), (5, 4), (6, 4),          # bottom bar
        ]

        anchor_x = center_x - 3
        anchor_y = center_y - 2

        logo_cells = set()

        for dx, dy in four + two:
            x = anchor_x + dx
            y = anchor_y + dy

            if 0 <= x < self.width and 0 <= y < self.height:
                logo_cells.add((x, y))

        return logo_cells

    def print_hex(self):
        """Print maze cells as hexadecimal wall values."""
        for row in self.grid:
            for cell in row:
                print(format(cell.walls, "x"), end="")
            print()


maze = Maze(width=20, height=20, entry=(0, 0), exit=(19, 19), perfect=True, seed=0)
#maze.print_hex()
