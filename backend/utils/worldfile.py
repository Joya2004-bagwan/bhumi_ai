"""World file parser for georeferencing images."""

from pathlib import Path
from typing import Tuple, Optional


class WorldFile:
    """Parses and stores world file georeferencing parameters."""
    
    def __init__(self, path: str):
        """
        Parse a world file (.pgw, .tfw, .jgw).
        
        World file format (6 lines):
        Line 1: pixel size in X direction (scale X)
        Line 2: rotation about Y axis (usually 0)
        Line 3: rotation about X axis (usually 0)
        Line 4: pixel size in Y direction (scale Y, usually negative)
        Line 5: X coordinate of upper-left pixel center
        Line 6: Y coordinate of upper-left pixel center
        """
        self.path = Path(path)
        self.scale_x: float = 1.0
        self.rotation_y: float = 0.0
        self.rotation_x: float = 0.0
        self.scale_y: float = -1.0
        self.origin_x: float = 0.0
        self.origin_y: float = 0.0
        self._parse()
    
    def _parse(self):
        """Parse the world file."""
        if not self.path.exists():
            raise FileNotFoundError(f"World file not found: {self.path}")
        
        with open(self.path, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 6:
            raise ValueError(f"Invalid world file: expected 6 lines, got {len(lines)}")
        
        self.scale_x = float(lines[0].strip())
        self.rotation_y = float(lines[1].strip())
        self.rotation_x = float(lines[2].strip())
        self.scale_y = float(lines[3].strip())
        self.origin_x = float(lines[4].strip())
        self.origin_y = float(lines[5].strip())
    
    def pixel_to_world(self, pixel_x: float, pixel_y: float) -> Tuple[float, float]:
        """
        Convert pixel coordinates to world coordinates.
        
        Args:
            pixel_x: X coordinate in pixels (column)
            pixel_y: Y coordinate in pixels (row)
        
        Returns:
            Tuple of (world_x, world_y)
        """
        world_x = self.scale_x * pixel_x + self.rotation_x * pixel_y + self.origin_x
        world_y = self.rotation_y * pixel_x + self.scale_y * pixel_y + self.origin_y
        return (world_x, world_y)
    
    def to_dict(self) -> dict:
        """Return parameters as dictionary."""
        return {
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "origin_x": self.origin_x,
            "origin_y": self.origin_y
        }