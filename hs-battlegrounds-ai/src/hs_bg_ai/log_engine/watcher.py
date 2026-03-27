"""LogWatcher — async tail-follow of the Hearthstone output_log.txt."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator

from hs_bg_ai.core.errors import LogReadError

logger = logging.getLogger(__name__)

# How often to poll for new data (seconds).
_POLL_INTERVAL = 0.1
# How often to check for file rotation (seconds).
_ROTATION_CHECK_INTERVAL = 2.0


class LogWatcher:
    """Tail-follow a log file asynchronously, yielding new lines.

    Features:
        - Seeks to end of file on startup (ignores historical data).
        - Detects file rotation (truncation / recreation) and resets.
        - Cooperative cancellation via ``stop()``.
    """

    def __init__(self, log_path: str | Path, *, seek_to_end: bool = True) -> None:
        self._path = Path(log_path)
        self._seek_to_end = seek_to_end
        self._running = False
        self._position: int = 0
        self._inode: int | None = None

    # ── Public API ────────────────────────────────────────────────

    async def watch(self) -> AsyncIterator[str]:
        """Yield new lines as they appear.

        This is an async generator — use ``async for line in watcher.watch()``.
        Call ``stop()`` from another coroutine to terminate.
        """
        self._running = True
        self._open_and_seek()

        rotation_counter = 0
        polls_per_rotation_check = max(1, int(_ROTATION_CHECK_INTERVAL / _POLL_INTERVAL))

        while self._running:
            try:
                lines = self._read_new_lines()
                for line in lines:
                    yield line

                rotation_counter += 1
                if rotation_counter >= polls_per_rotation_check:
                    rotation_counter = 0
                    if self._file_rotated():
                        logger.info("Log file rotation detected — resetting position.")
                        self._position = 0
                        self._update_inode()

            except FileNotFoundError:
                logger.warning("Log file not found: %s — waiting for it to appear.", self._path)
                self._position = 0
                self._inode = None
            except OSError as exc:
                logger.error("OS error reading log: %s", exc)

            await asyncio.sleep(_POLL_INTERVAL)

    def stop(self) -> None:
        """Signal the watcher to stop after the current poll cycle."""
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Internal helpers ──────────────────────────────────────────

    def _open_and_seek(self) -> None:
        """Set initial file position and inode."""
        if not self._path.exists():
            logger.warning("Log file does not exist yet: %s", self._path)
            self._position = 0
            self._inode = None
            return

        stat = self._path.stat()
        self._inode = stat.st_ino
        if self._seek_to_end:
            self._position = stat.st_size
        else:
            self._position = 0

    def _read_new_lines(self) -> list[str]:
        """Read all new complete lines since last position."""
        if not self._path.exists():
            raise FileNotFoundError(self._path)

        with open(self._path, "rb") as f:
            f.seek(self._position)
            raw = f.read()

        if not raw:
            return []

        # Only process complete lines (ending with newline).
        if not raw.endswith(b"\n"):
            # Keep partial line for next read.
            last_nl = raw.rfind(b"\n")
            if last_nl == -1:
                return []
            raw = raw[: last_nl + 1]

        self._position += len(raw)
        data = raw.decode("utf-8", errors="replace")
        lines = data.splitlines()
        return [line for line in lines if line.strip()]

    def _file_rotated(self) -> bool:
        """Detect if the file was truncated or replaced (new inode / smaller size)."""
        if not self._path.exists():
            return False
        stat = self._path.stat()
        if self._inode is not None and stat.st_ino != self._inode:
            return True
        if stat.st_size < self._position:
            return True
        return False

    def _update_inode(self) -> None:
        if self._path.exists():
            self._inode = self._path.stat().st_ino
