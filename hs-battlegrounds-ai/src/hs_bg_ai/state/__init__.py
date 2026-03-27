"""Game state management — apply events, fuse data sources."""

from .fusion import DataFusion
from .manager import StateManager

__all__ = ["DataFusion", "StateManager"]
