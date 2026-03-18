# flake8: noqa: F401
__version__ = "1.0.0"
__author__ = "esnavarr, mju-ferr"

__all__ = ["Maze", "MazeError", "Cell"]

from .maze import Maze, MazeError
from .cell import Cell