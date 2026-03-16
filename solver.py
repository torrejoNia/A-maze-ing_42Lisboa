#Calculate solution for the maze

from typing import List, Tuple, Optional

from mazegen.maze import Maze

DIRECTIONS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}

from typing import List, Tuple, Optional

def solve_maze(maze: Maze) -> List[str]:
    """Return path as list of directions 'N','E','S','W'."""
    
    start = maze.entry
    end = maze.exit

    # Use a list as a simple queue
    queue: List[Tuple[int,int]] = [start]
    came_from: dict[Tuple[int,int], Optional[Tuple[Tuple[int,int], str]]] = {start: None}

    while queue:
        current = queue.pop(0)  # FIFO queue behavior

        if current == end:
            break

        x, y = current
        cell = maze.grid[y][x]

        # Directions to neighbor cells
        for direction, (dx, dy) in DIRECTIONS.items():
            nx, ny = x + dx, y + dy

            if 0 <= nx < maze.width and 0 <= ny < maze.height:
                if not cell.has_wall(direction) and (nx, ny) not in came_from:
                    queue.append((nx, ny))
                    came_from[(nx, ny)] = (current, direction)

    # Reconstruct the path
    path: List[str] = []
    if end not in came_from:
        print("No path found - exit is unreachable.")
        return []

    current = end
    while came_from[current] is not None:
        previous, direction = came_from[current]
        path.append(direction)
        current = previous

    path.reverse()
    return path