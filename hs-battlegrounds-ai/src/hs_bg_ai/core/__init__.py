"""Core infrastructure — event bus, errors."""

from .errors import (
    CoordMappingError,
    DisconnectError,
    ExecutionError,
    HSBGError,
    LogReadError,
    StateError,
    WindowNotFoundError,
)
from .events import EventBus, EventType

__all__ = [
    "CoordMappingError",
    "DisconnectError",
    "EventBus",
    "EventType",
    "ExecutionError",
    "HSBGError",
    "LogReadError",
    "StateError",
    "WindowNotFoundError",
]
