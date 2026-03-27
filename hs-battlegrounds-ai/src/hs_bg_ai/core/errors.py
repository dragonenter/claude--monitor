"""Project-specific error hierarchy."""


class HSBGError(Exception):
    """Base exception for all HS Battlegrounds AI errors."""


class LogReadError(HSBGError):
    """Failed to read or tail the game log file."""


class StateError(HSBGError):
    """Game state is inconsistent or unexpected."""


class ExecutionError(HSBGError):
    """An action could not be executed (click failed, timeout, etc.)."""


class WindowNotFoundError(HSBGError):
    """The Hearthstone game window could not be located."""


class DisconnectError(HSBGError):
    """The game appears to have disconnected."""


class CoordMappingError(HSBGError):
    """A screen coordinate could not be mapped to a game element."""
