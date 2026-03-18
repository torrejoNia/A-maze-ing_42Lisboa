# Calculate solution for the maze

from typing import List, Tuple, Optional

from mazegen.maze import Maze

DIRECTIONS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}


def solve_maze(maze: Maze) -> str:
    """
    Solve a maze using Breadth-First Search (BFS).

    Args:
        maze (Maze):
            A Maze object containing:
            - maze.grid : 2D list of Cell objects
            - maze.entry : starting coordinates (x, y)
            - maze.exit : ending coordinates (x, y)

    Returns:
        List[str]:
            A list of directions ('N', 'E', 'S', 'W')
            representing the shortest path from entry to exit.

            Example:
                ['E', 'E', 'S', 'S']
    """

    # Starting and ending positions
    start = maze.entry
    end = maze.exit

    # Queue for BFS exploration.
    # Starts with the entry cell.
    queue: List[Tuple[int, int]] = [start]

    # Stores how each cell was reached.
    # Format:
    # cell -> (previous_cell, direction_taken)
    #
    # Example:
    # (2,3): ((2,2), 'S')
    #
    # Means:
    # we reached (2,3) from (2,2) by moving South.
    came_from: dict[
        Tuple[int, int],
        Optional[Tuple[Tuple[int, int], str]]
    ] = {start: None}

    # BFS loop: continues until queue is empty
    while queue:
        current = queue.pop(0)  # First in, first out queue behavior

        if current == end:
            break

        x, y = current
        cell = maze.grid[y][x]

        # Check all four directions
        for direction, (dx, dy) in DIRECTIONS.items():

            # Neighbor coordinates
            nx = x + dx
            ny = y + dy

            # Check if neighbor is inside maze bounds
            if 0 <= nx < maze.width and 0 <= ny < maze.height:

                # Only move if:
                # 1. there is no wall
                # 2. cell was not visited before
                if not cell.has_wall(direction) and (nx, ny) not in came_from:

                    # Add neighbor to queue
                    queue.append((nx, ny))

                    # Record how we reached it
                    came_from[(nx, ny)] = (current, direction)

    # Reconstruct the path
    path: List[str] = []
    if end not in came_from:
        print("No path found - exit is unreachable.")
        return ""

    # Start from exit and go backwards
    current = end
    while True:
        step = came_from[current]
        if step is None:
            break
        previous, direction = step

        # Save direction used to reach current cell
        path.append(direction)

        # Move backwards
        current = previous

    # Reverse because we built path backwards
    path.reverse()

    return "".join(path)


if __name__ == "__main__":

    maze = Maze(
        width=20,
        height=20,
        entry=(0, 0),
        exit=(19, 19),
        perfect=True,
        seed=0
    )
    maze.print_hex()
    path = solve_maze(maze)

    print(path)
    print("Path length:", len(path))
