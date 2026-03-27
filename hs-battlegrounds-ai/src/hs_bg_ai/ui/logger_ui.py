"""LoggerUI: loguru-based logging with per-game log files and terminal output."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    from loguru import logger as _loguru_logger  # type: ignore

    _LOGURU_AVAILABLE = True
except ImportError:
    _LOGURU_AVAILABLE = False
    import logging as _std_logging

    _loguru_logger = None  # type: ignore


class LoggerUI:
    """Configures loguru for dual output: rotating file per game and terminal.

    Parameters
    ----------
    log_dir:
        Directory where per-game log files are stored.
    log_level:
        Minimum log level (e.g. ``"INFO"``, ``"DEBUG"``).
    """

    def __init__(
        self,
        log_dir: str | Path = "logs",
        log_level: str = "INFO",
    ) -> None:
        self._log_dir = Path(log_dir)
        self._log_level = log_level.upper()
        self._file_handler_id: int | None = None
        self._terminal_handler_id: int | None = None
        self._current_game_id: str | None = None

        if _LOGURU_AVAILABLE:
            # Remove the default loguru handler
            _loguru_logger.remove()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup(self, game_id: str = "default") -> None:
        """Configure loguru sinks for *game_id*.

        Creates a log file ``{log_dir}/{game_id}.log`` and a coloured
        terminal sink.
        """
        if not _LOGURU_AVAILABLE:
            self._setup_stdlib(game_id)
            return

        # Remove previous file handler (if any)
        if self._file_handler_id is not None:
            try:
                _loguru_logger.remove(self._file_handler_id)
            except Exception:  # noqa: BLE001
                pass

        if self._terminal_handler_id is not None:
            try:
                _loguru_logger.remove(self._terminal_handler_id)
            except Exception:  # noqa: BLE001
                pass

        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._current_game_id = game_id

        log_file = self._log_dir / f"{game_id}.log"
        self._file_handler_id = _loguru_logger.add(
            str(log_file),
            level=self._log_level,
            rotation="50 MB",
            retention="7 days",
            encoding="utf-8",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} — {message}",
        )
        self._terminal_handler_id = _loguru_logger.add(
            sys.stderr,
            level=self._log_level,
            colorize=True,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        )

    def _setup_stdlib(self, game_id: str) -> None:
        """Fallback setup using stdlib logging when loguru is not installed."""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self._log_dir / f"{game_id}.log"
        logging = _std_logging
        logging.basicConfig(
            level=getattr(logging, self._log_level, logging.INFO),
            format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d — %(message)s",
            handlers=[
                logging.FileHandler(str(log_file), encoding="utf-8"),
                logging.StreamHandler(sys.stderr),
            ],
        )
        self._current_game_id = game_id

    # ------------------------------------------------------------------
    # Convenience passthrough
    # ------------------------------------------------------------------

    @property
    def logger(self) -> Any:
        """Return the configured logger (loguru or stdlib)."""
        if _LOGURU_AVAILABLE:
            return _loguru_logger
        return _std_logging.getLogger("hs_bg_ai")

    @property
    def current_game_id(self) -> str | None:
        return self._current_game_id
