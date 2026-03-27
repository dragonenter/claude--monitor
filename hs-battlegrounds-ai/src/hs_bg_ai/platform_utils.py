"""Platform detection utilities for cross-platform compatibility."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Literal

PlatformName = Literal["windows", "macos", "linux"]


def current_platform() -> PlatformName:
    """Return the current operating system as a normalised string."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


# -- Log paths ----------------------------------------------------------------

_LOG_PATHS: dict[PlatformName, str] = {
    "windows": os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Low",
        "Blizzard Entertainment",
        "Hearthstone",
        "output_log.txt",
    ),
    "macos": str(Path("~/Library/Logs/Unity/Player.log").expanduser()),
    "linux": str(Path("~/.config/unity3d/Blizzard Entertainment/Hearthstone/Player.log").expanduser()),
}


def default_log_path(plat: PlatformName | None = None) -> str:
    """Return the default Hearthstone log path for the given (or current) platform."""
    plat = plat or current_platform()
    return _LOG_PATHS.get(plat, _LOG_PATHS["linux"])


# -- Window titles -------------------------------------------------------------

_WINDOW_TITLES: dict[PlatformName, str] = {
    "windows": "\u7089\u77f3\u4f20\u8bf4",  # 炉石传说
    "macos": "Hearthstone",
    "linux": "Hearthstone",
}


def default_window_title(plat: PlatformName | None = None) -> str:
    """Return the expected game window title for the given (or current) platform."""
    plat = plat or current_platform()
    return _WINDOW_TITLES.get(plat, "Hearthstone")


# -- Window finding (platform-specific) ----------------------------------------

def find_window_by_title(title: str) -> bool:
    """Return True if a window with the given *title* exists."""
    plat = current_platform()
    if plat == "windows":
        return _find_window_win32(title)
    if plat == "macos":
        return _find_window_macos(title)
    return _find_window_linux(title)


def activate_window_by_title(title: str) -> bool:
    """Bring the window with *title* to the foreground. Returns success flag."""
    plat = current_platform()
    if plat == "windows":
        return _activate_window_win32(title)
    if plat == "macos":
        return _activate_window_macos(title)
    return False


def get_window_bounds(title: str) -> dict[str, int] | None:
    """Return {'left', 'top', 'width', 'height'} for the window, or None."""
    plat = current_platform()
    if plat == "windows":
        return _get_bounds_win32(title)
    if plat == "macos":
        return _get_bounds_macos(title)
    return None


# -- macOS accessibility check -------------------------------------------------

def check_macos_accessibility() -> bool:
    """Check (and warn) if the current process has macOS accessibility permissions.

    Returns True if permissions are granted or not on macOS.
    """
    if current_platform() != "macos":
        return True
    try:
        # This is a best-effort check; the actual test happens at runtime when
        # pynput tries to listen for events.
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to return name of first process'],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            import logging
            logging.getLogger(__name__).warning(
                "macOS accessibility permissions may not be granted. "
                "Go to System Preferences > Privacy & Security > Accessibility "
                "and add your terminal / Python to the allowed apps."
            )
            return False
        return True
    except Exception:
        return True  # Can't check — assume OK


# -- Windows helpers -----------------------------------------------------------

def _find_window_win32(title: str) -> bool:
    try:
        import win32gui  # type: ignore
        hwnd = win32gui.FindWindow(None, title)
        return hwnd != 0
    except ImportError:
        return False


def _activate_window_win32(title: str) -> bool:
    try:
        import win32con  # type: ignore
        import win32gui  # type: ignore
        hwnd = win32gui.FindWindow(None, title)
        if hwnd == 0:
            return False
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except ImportError:
        return False


def _get_bounds_win32(title: str) -> dict[str, int] | None:
    try:
        import win32gui  # type: ignore
        hwnd = win32gui.FindWindow(None, title)
        if hwnd == 0:
            return None
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return {"left": left, "top": top, "width": right - left, "height": bottom - top}
    except ImportError:
        return None


# -- macOS helpers (AppleScript via osascript) ---------------------------------

def _find_window_macos(title: str) -> bool:
    try:
        script = (
            f'tell application "System Events" to return '
            f'(exists (first process whose name is "{title}"))'
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip().lower() == "true"
    except Exception:
        return False


def _activate_window_macos(title: str) -> bool:
    try:
        script = f'tell application "{title}" to activate'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_bounds_macos(title: str) -> dict[str, int] | None:
    try:
        script = (
            f'tell application "System Events"\n'
            f'  tell process "{title}"\n'
            f'    set p to position of window 1\n'
            f'    set s to size of window 1\n'
            f'    return (item 1 of p) & "," & (item 2 of p) & "," & (item 1 of s) & "," & (item 2 of s)\n'
            f'  end tell\n'
            f'end tell'
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        parts = result.stdout.strip().split(",")
        if len(parts) != 4:
            return None
        left, top, width, height = (int(p.strip()) for p in parts)
        return {"left": left, "top": top, "width": width, "height": height}
    except Exception:
        return None


# -- Linux helpers -------------------------------------------------------------

def _find_window_linux(title: str) -> bool:
    try:
        result = subprocess.run(
            ["xdotool", "search", "--name", title],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False
