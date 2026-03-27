"""AppController: high-level lifecycle management for the bot."""

from __future__ import annotations

from enum import Enum, auto
from typing import Any


class BotStatus(Enum):
    """Current operational state of the bot."""

    STOPPED = auto()
    RUNNING = auto()
    PAUSED = auto()


class AppController:
    """Manages the overall run-state of the bot.

    This is intentionally decoupled from async internals so it can be driven
    by hotkeys or a UI without requiring an event loop in the controller itself.
    The actual bot loop is expected to poll :meth:`get_status` / observe
    the emitted event when the status changes.
    """

    def __init__(self) -> None:
        self._status: BotStatus = BotStatus.STOPPED
        # Optional callback invoked whenever the status changes.
        self._on_status_change: Any | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_bot(self) -> None:
        """Transition the bot to RUNNING state.

        No-op if already running.
        """
        if self._status != BotStatus.RUNNING:
            self._status = BotStatus.RUNNING
            self._notify()

    def stop_bot(self) -> None:
        """Transition the bot to STOPPED state."""
        if self._status != BotStatus.STOPPED:
            self._status = BotStatus.STOPPED
            self._notify()

    def toggle_pause(self) -> BotStatus:
        """Toggle between RUNNING and PAUSED.

        If the bot is STOPPED, this is a no-op and returns STOPPED.
        Returns the new status.
        """
        if self._status == BotStatus.RUNNING:
            self._status = BotStatus.PAUSED
            self._notify()
        elif self._status == BotStatus.PAUSED:
            self._status = BotStatus.RUNNING
            self._notify()
        return self._status

    def get_status(self) -> BotStatus:
        """Return the current :class:`BotStatus`."""
        return self._status

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._status == BotStatus.RUNNING

    @property
    def is_paused(self) -> bool:
        return self._status == BotStatus.PAUSED

    @property
    def is_stopped(self) -> bool:
        return self._status == BotStatus.STOPPED

    def set_status_change_callback(self, callback: Any) -> None:
        """Register a callback invoked with the new :class:`BotStatus` on changes."""
        self._on_status_change = callback

    def _notify(self) -> None:
        if self._on_status_change is not None:
            try:
                self._on_status_change(self._status)
            except Exception:  # noqa: BLE001
                pass
