#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import List
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
import numpy as np


@dataclass
class Region:
    """Rectangle region for LiDAR point filtering"""
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    color: QColor = field(default_factory=lambda: QColor(0x4e, 0xc9, 0xb0))
    label: str = ""

    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside region"""
        return (self.x_min <= x <= self.x_max and
                self.y_min <= y <= self.y_max)

    def width(self) -> float:
        """Get region width"""
        return self.x_max - self.x_min

    def height(self) -> float:
        """Get region height"""
        return self.y_max - self.y_min


class RegionManager(QObject):
    """Manager for multiple ROI regions"""

    # Signal emitted when regions list changes
    regions_changed = pyqtSignal()

    # Color palette for regions (8 distinct colors for dark background)
    _color_palette = [
        QColor(0x4e, 0xc9, 0xb0),  # teal
        QColor(0xce, 0x91, 0x78),  # salmon
        QColor(0xdc, 0xdc, 0xaa),  # khaki
        QColor(0x9c, 0xdc, 0xfe),  # light blue
        QColor(0xc5, 0x86, 0xc0),  # purple
        QColor(0x6a, 0x99, 0x55),  # green
        QColor(0xd7, 0xba, 0x7d),  # gold
        QColor(0x56, 0x9c, 0xd6),  # blue
    ]

    def __init__(self):
        super().__init__()
        self._regions: List[Region] = []

    def add_region(self, x1: float, y1: float, x2: float, y2: float) -> int:
        """
        Add new region with coordinates sorted to min/max.
        Returns region index.
        """
        # Sort coordinates to ensure min/max
        x_min = min(x1, x2)
        x_max = max(x1, x2)
        y_min = min(y1, y2)
        y_max = max(y1, y2)

        # Assign color from palette (cycle through)
        color_index = len(self._regions) % len(self._color_palette)
        color = self._color_palette[color_index]

        # Create region with label
        region_number = len(self._regions) + 1
        label = f"Region {region_number}"

        region = Region(
            x_min=x_min,
            y_min=y_min,
            x_max=x_max,
            y_max=y_max,
            color=color,
            label=label
        )

        self._regions.append(region)
        self.regions_changed.emit()

        return len(self._regions) - 1

    def remove_region(self, index: int):
        """Remove region by index"""
        if 0 <= index < len(self._regions):
            self._regions.pop(index)
            self.regions_changed.emit()

    def clear_all(self):
        """Remove all regions"""
        if self._regions:
            self._regions.clear()
            self.regions_changed.emit()

    def get_regions(self) -> List[Region]:
        """Get copy of regions list"""
        return self._regions.copy()

    def get_region(self, index: int) -> Region:
        """Get single region by index"""
        return self._regions[index]

    def region_count(self) -> int:
        """Get number of regions"""
        return len(self._regions)


def filter_points(points: np.ndarray, region: Region) -> np.ndarray:
    """
    Filter points array to only include points inside region.

    Args:
        points: numpy array of shape (N, 2) with [x, y] coordinates
        region: Region to filter by

    Returns:
        numpy array of shape (M, 2) where M <= N, containing only points inside region
    """
    if points.size == 0:
        return points

    # Boolean mask for points inside rectangle
    mask = (points[:, 0] >= region.x_min) & (points[:, 0] <= region.x_max) & \
           (points[:, 1] >= region.y_min) & (points[:, 1] <= region.y_max)

    return points[mask]
