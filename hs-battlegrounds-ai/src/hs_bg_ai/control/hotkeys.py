"""HotkeyManager: register and listen for global hotkeys (F9-F12 by default)."""

from __future__ import annotations

import logging
from typing import Any, Callable

from hs_bg_ai.config import HotkeyConfig

logger = logging.getLogger(__name__)

try:
    from pynput.keyboard import GlobalHotKeys, Key, KeyCode  # type: ignore

    _PYNPUT_AVAILABLE = True
except ImportError:
    _PYNPUT_AVAILABLE = False

# Mapping from simple key names (e.g. "f9") to pynput format (e.g. "<f9>").
_KEY_MAP: dict[str, str] = {}
for _i in range(1, 13):
    _KEY_MAP[f"f{_i}"] = f"<f{_i}>"


def _to_pynput_key(key: str) -> str:
    """Convert a simple key name to a pynput hotkey string."""
    return _KEY_MAP.get(key.lower(), key.lower())


class HotkeyManager:
    """Registers global hotkeys and dispatches them to callbacks.

    Uses ``pynput.keyboard.GlobalHotKeys`` for cross-platform support
    (Windows, macOS, Linux). Falls back to a harmless no-op stub when
    pynput is unavailable.

    Default hotkeys (from :class:`~hs_bg_ai.config.HotkeyConfig`):
    - F9  -- start/stop bot
    - F10 -- pause/resume
    - F11 -- manual takeover
    - F12 -- emergency stop
    """

    def __init__(self, config: HotkeyConfig | None = None) -> None:
        self._config = config or HotkeyConfig()
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._listening = False
        self._listener: Any = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, key: str, callback: Callable[[], None]) -> None:
        """Associate *callback* with *key* (e.g. ``"f9"``).

        Registration is idempotent -- registering the same key again replaces
        the previous callback.
        """
        self._callbacks[key.lower()] = callback

    def register_defaults(
        self,
        on_start_stop: Callable[[], None] | None = None,
        on_pause_resume: Callable[[], None] | None = None,
        on_manual_takeover: Callable[[], None] | None = None,
        on_emergency_stop: Callable[[], None] | None = None,
    ) -> None:
        """Register all default hotkeys at once using config-defined key names."""
        if on_start_stop is not None:
            self.register(self._config.start_stop, on_start_stop)
        if on_pause_resume is not None:
            self.register(self._config.pause_resume, on_pause_resume)
        if on_manual_takeover is not None:
            self.register(self._config.manual_takeover, on_manual_takeover)
        if on_emergency_stop is not None:
            self.register(self._config.emergency_stop, on_emergency_stop)

    # ------------------------------------------------------------------
    # Listening lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin intercepting hotkeys."""
        if self._listening:
            return
        self._listening = True
        if _PYNPUT_AVAILABLE and self._callbacks:
            hotkeys = {
                _to_pynput_key(key): cb for key, cb in self._callbacks.items()
            }
            try:
                self._listener = GlobalHotKeys(hotkeys)
                self._listener.start()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to start hotkey listener: %s", exc)
                self._listener = None

    def stop(self) -> None:
        """Stop intercepting hotkeys and clean up."""
        if not self._listening:
            return
        self._listening = False
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:  # noqa: BLE001
                pass
            self._listener = None

    @property
    def is_listening(self) -> bool:
        return self._listening
