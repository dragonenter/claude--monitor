"""DisconnectRecovery: detect and wait for reconnect after a game disconnect."""

from __future__ import annotations

import asyncio
import time
from typing import Callable

from .base import BaseRecovery


class DisconnectRecovery(BaseRecovery):
    """Recovery handler for network disconnects.

    Waits until the game reconnects or *timeout* expires.

    Parameters
    ----------
    reconnect_check:
        Optional callable ``() -> bool`` that returns ``True`` when the
        connection is restored.  Defaults to a stub that always returns
        ``False`` (useful for testing).
    poll_interval:
        Seconds between reconnect-check polls.
    """

    MAX_RETRIES = 5
    RETRY_DELAY = 5.0

    def __init__(
        self,
        reconnect_check: Callable[[], bool] | None = None,
        poll_interval: float = 2.0,
    ) -> None:
        self._disconnected = False
        self._reconnect_check = reconnect_check
        self._poll_interval = poll_interval

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """Return ``True`` when a disconnect has been flagged."""
        return self._disconnected

    def flag_disconnect(self) -> None:
        """Mark the connection as lost."""
        self._disconnected = True

    def flag_reconnect(self) -> None:
        """Mark the connection as restored."""
        self._disconnected = False

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    async def recover(self, timeout: float = 60.0) -> bool:
        """Poll for reconnection until it succeeds or *timeout* expires.

        Returns ``True`` once connected, ``False`` on timeout.
        """
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            await asyncio.sleep(self._poll_interval)

            # Delegate to the external checker if provided
            if self._reconnect_check is not None:
                try:
                    connected = self._reconnect_check()
                except Exception:  # noqa: BLE001
                    connected = False
            else:
                # No checker — cannot confirm reconnect automatically
                connected = False

            if connected:
                self.flag_reconnect()
                return True

        return False
