"""ScreenCapturer: capture the game window using mss."""

from __future__ import annotations

from typing import Any

try:
    import mss  # type: ignore
    import mss.tools  # type: ignore

    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False

from .regions import ScreenRegion


class ScreenCapturer:
    """Captures screenshots of the Hearthstone game window (or specific regions).

    Falls back to ``None`` on headless systems where *mss* is unavailable or
    no display is present.
    """

    def __init__(self, window_title: str = "炉石传说") -> None:
        self._window_title = window_title
        self._sct: Any = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_sct(self) -> Any:
        """Lazily initialise the mss screen-capture context."""
        if self._sct is None:
            if not _MSS_AVAILABLE:
                return None
            try:
                self._sct = mss.mss()
            except Exception:  # noqa: BLE001
                return None
        return self._sct

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_game_window(self) -> bool:
        """Attempt to locate the game window.

        Returns ``True`` if found, ``False`` otherwise.  On non-Windows
        platforms this is a best-effort stub that always returns ``False``
        (actual window detection requires platform-specific APIs).
        """
        try:
            import ctypes  # noqa: F401 — Windows-only

            import win32gui  # type: ignore

            hwnd = win32gui.FindWindow(None, self._window_title)
            return hwnd != 0
        except ImportError:
            return False

    def capture(self) -> Any | None:
        """Capture the full primary monitor.

        Returns an mss screenshot object, or ``None`` when unavailable.
        """
        sct = self._get_sct()
        if sct is None:
            return None
        monitor = sct.monitors[1]  # primary monitor
        return sct.grab(monitor)

    def capture_region(self, region: ScreenRegion) -> Any | None:
        """Capture a specific *region* of the screen.

        Returns an mss screenshot object, or ``None`` when unavailable.
        """
        sct = self._get_sct()
        if sct is None:
            return None
        return sct.grab(region.as_dict())

    def close(self) -> None:
        """Release the mss context."""
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:  # noqa: BLE001
                pass
            self._sct = None

    def __enter__(self) -> ScreenCapturer:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
