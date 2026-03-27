"""MouseController: human-like mouse movement using bezier curves."""

from __future__ import annotations

import asyncio
import random
import time

try:
    import pyautogui  # type: ignore

    _PYAUTOGUI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYAUTOGUI_AVAILABLE = False

from hs_bg_ai.config import MouseConfig
from hs_bg_ai.core.errors import ExecutionError

from .timing import TimingController


class MouseController:
    """Performs mouse actions with bezier curve movement to mimic human behaviour.

    Uses *pyautogui* when available; falls back to a no-op stub so that
    code can be tested on headless systems.
    """

    def __init__(
        self,
        config: MouseConfig | None = None,
        timing: TimingController | None = None,
    ) -> None:
        self._config = config or MouseConfig()
        self._timing = timing or TimingController()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_path(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """Return a list of integer pixel waypoints from *start* to *end*."""
        ctrl_pts = self._timing.bezier_control_points(
            start, end, deviation=self._config.bezier_deviation
        )
        # More steps for longer distances, min 10
        dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
        steps = max(10, int(dist / 20))
        return TimingController.interpolate_bezier(ctrl_pts, steps=steps)

    def _move_along_path(self, path: list[tuple[int, int]]) -> None:
        """Move the cursor along *path* using pyautogui (or stub)."""
        if not _PYAUTOGUI_AVAILABLE:
            return
        for x, y in path:
            pyautogui.moveTo(x, y, duration=0)

    def _click_delay(self) -> float:
        return random.uniform(
            self._config.click_delay_min, self._config.click_delay_max
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def move(self, x: int, y: int) -> None:
        """Move cursor to *(x, y)* via a bezier curve."""
        if _PYAUTOGUI_AVAILABLE:
            current = pyautogui.position()
            start = (current.x, current.y)
        else:
            start = (x, y)

        path = self._build_path(start, (x, y))
        await asyncio.to_thread(self._move_along_path, path)

    async def click(self, x: int, y: int) -> None:
        """Move to *(x, y)* and perform a left click."""
        try:
            await self.move(x, y)
            await asyncio.sleep(self._click_delay())
            if _PYAUTOGUI_AVAILABLE:
                pyautogui.click(x, y)
        except Exception as exc:
            raise ExecutionError(f"click({x}, {y}) failed: {exc}") from exc

    async def right_click(self, x: int, y: int) -> None:
        """Move to *(x, y)* and perform a right click."""
        try:
            await self.move(x, y)
            await asyncio.sleep(self._click_delay())
            if _PYAUTOGUI_AVAILABLE:
                pyautogui.rightClick(x, y)
        except Exception as exc:
            raise ExecutionError(f"right_click({x}, {y}) failed: {exc}") from exc

    async def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
    ) -> None:
        """Drag from *(from_x, from_y)* to *(to_x, to_y)* with bezier movement."""
        try:
            await self.move(from_x, from_y)
            await asyncio.sleep(self._click_delay())
            if _PYAUTOGUI_AVAILABLE:
                path = self._build_path((from_x, from_y), (to_x, to_y))
                pyautogui.mouseDown(from_x, from_y)
                await asyncio.to_thread(self._move_along_path, path)
                pyautogui.mouseUp(to_x, to_y)
        except Exception as exc:
            raise ExecutionError(
                f"drag({from_x},{from_y} -> {to_x},{to_y}) failed: {exc}"
            ) from exc
