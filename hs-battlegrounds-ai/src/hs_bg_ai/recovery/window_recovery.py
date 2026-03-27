"""WindowRecovery: detect when the game window is lost and try to restore it."""

from __future__ import annotations

import asyncio

from hs_bg_ai.platform_utils import (
    activate_window_by_title,
    default_window_title,
    find_window_by_title,
)

from .base import BaseRecovery


class WindowRecovery(BaseRecovery):
    """Detects a missing game window and attempts to locate/activate it.

    Parameters
    ----------
    window_title:
        Title of the Hearthstone window to search for.
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 3.0

    def __init__(self, window_title: str | None = None) -> None:
        self._window_title = window_title or default_window_title()
        self._window_lost = False

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """Return ``True`` when the window cannot be found."""
        if self._window_lost:
            return True
        return not self._find_window()

    def flag_lost(self) -> None:
        """Manually mark the window as lost."""
        self._window_lost = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_window(self) -> bool:
        """Return ``True`` if the game window exists on this system."""
        return find_window_by_title(self._window_title)

    def _activate_window(self) -> bool:
        """Bring the game window to the foreground. Returns success flag."""
        return activate_window_by_title(self._window_title)

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    async def recover(self, timeout: float = 30.0) -> bool:
        """Attempt to find and activate the game window.

        Returns ``True`` on success, ``False`` otherwise.
        """
        await asyncio.sleep(0)

        found = self._find_window()
        if not found:
            return False

        activated = self._activate_window()
        if activated or self._find_window():
            self._window_lost = False
            return True

        return False
