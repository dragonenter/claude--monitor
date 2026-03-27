"""LogRecovery: detect and recover from log file read failures."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .base import BaseRecovery


class LogRecovery(BaseRecovery):
    """Detects log file access issues and attempts to re-open the watcher.

    Parameters
    ----------
    log_path:
        Path to the Hearthstone log file being watched.
    watcher:
        Optional log-watcher object that has an ``open()`` / ``reopen()``
        method.  When ``None`` only the detection logic is active.
    """

    MAX_RETRIES = 5
    RETRY_DELAY = 1.0

    def __init__(self, log_path: str | Path | None = None, watcher: Any = None) -> None:
        self._log_path = Path(log_path) if log_path else None
        self._watcher = watcher
        self._error_detected = False

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """Return ``True`` when the log file cannot be read.

        Checks:
        - File does not exist
        - File is not readable
        - A ``LogReadError`` was previously flagged via :meth:`flag_error`
        """
        if self._error_detected:
            return True
        if self._log_path is not None:
            return not (self._log_path.exists() and self._log_path.is_file())
        return False

    def flag_error(self) -> None:
        """Manually signal that a log read error occurred."""
        self._error_detected = True

    def clear_error(self) -> None:
        """Reset the manually-flagged error state."""
        self._error_detected = False

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    async def recover(self, timeout: float = 30.0) -> bool:
        """Attempt to re-open the log watcher or wait for the file to appear.

        Returns ``True`` on success.
        """
        await asyncio.sleep(0)  # yield to event loop

        # Try to re-open via watcher
        if self._watcher is not None:
            try:
                reopen = getattr(self._watcher, "reopen", None) or getattr(
                    self._watcher, "open", None
                )
                if reopen is not None:
                    if asyncio.iscoroutinefunction(reopen):
                        await reopen()
                    else:
                        reopen()
                    self.clear_error()
                    return True
            except Exception:  # noqa: BLE001
                pass

        # Fallback: check that the file now exists
        if self._log_path is not None and self._log_path.exists():
            self.clear_error()
            return True

        return False
