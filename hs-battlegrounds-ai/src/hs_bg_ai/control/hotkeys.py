"""HotkeyManager: register and listen for global hotkeys (F9-F12 by default)."""

from __future__ import annotations

from typing import Any, Callable

from hs_bg_ai.config import HotkeyConfig

try:
    import keyboard  # type: ignore

    _KEYBOARD_AVAILABLE = True
except ImportError:
    _KEYBOARD_AVAILABLE = False


class HotkeyManager:
    """Registers global hotkeys and dispatches them to callbacks.

    Uses the ``keyboard`` library when available (Windows/Linux with root).
    On unsupported platforms the class is a harmless no-op stub.

    Default hotkeys (from :class:`~hs_bg_ai.config.HotkeyConfig`):
    - F9  — start/stop bot
    - F10 — pause/resume
    - F11 — manual takeover
    - F12 — emergency stop
    """

    def __init__(self, config: HotkeyConfig | None = None) -> None:
        self._config = config or HotkeyConfig()
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._listening = False
        self._hook_ids: list[Any] = []  # type: ignore[name-defined]

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, key: str, callback: Callable[[], None]) -> None:
        """Associate *callback* with *key* (e.g. ``"f9"``).

        Registration is idempotent — registering the same key again replaces
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
        if _KEYBOARD_AVAILABLE:
            for key, cb in self._callbacks.items():
                hook = keyboard.add_hotkey(key, cb)
                self._hook_ids.append(hook)

    def stop(self) -> None:
        """Stop intercepting hotkeys and clean up."""
        if not self._listening:
            return
        self._listening = False
        if _KEYBOARD_AVAILABLE:
            for hook in self._hook_ids:
                try:
                    keyboard.remove_hotkey(hook)
                except Exception:  # noqa: BLE001
                    pass
            self._hook_ids.clear()

    @property
    def is_listening(self) -> bool:
        return self._listening
