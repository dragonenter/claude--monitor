"""TimingController: random delays and bezier control point generation."""

from __future__ import annotations

import asyncio
import random

from hs_bg_ai.config import TimingConfig


class TimingController:
    """Manages inter-action timing with humanlike randomness.

    Delays are uniformly sampled from [action_delay_min, action_delay_max].
    Bezier control points are generated for smooth cursor trajectories.
    """

    def __init__(self, config: TimingConfig | None = None) -> None:
        self._config = config or TimingConfig()

    # ------------------------------------------------------------------
    # Delay helpers
    # ------------------------------------------------------------------

    def random_action_delay(self) -> float:
        """Return a random delay (seconds) between two actions."""
        return random.uniform(
            self._config.action_delay_min,
            self._config.action_delay_max,
        )

    def random_think_delay(self) -> float:
        """Return a random think/pause delay (seconds)."""
        return random.uniform(
            self._config.think_delay_min,
            self._config.think_delay_max,
        )

    async def sleep_action(self) -> None:
        """Async sleep for a random action delay (200–600 ms by default)."""
        await asyncio.sleep(self.random_action_delay())

    async def sleep_think(self) -> None:
        """Async sleep for a random think delay."""
        await asyncio.sleep(self.random_think_delay())

    # ------------------------------------------------------------------
    # Bezier helpers
    # ------------------------------------------------------------------

    @staticmethod
    def bezier_control_points(
        start: tuple[float, float],
        end: tuple[float, float],
        deviation: float = 15.0,
        num_controls: int = 2,
    ) -> list[tuple[float, float]]:
        """Generate *num_controls* random control points for a bezier curve.

        Points are placed roughly between *start* and *end* with perpendicular
        displacement sampled uniformly in [-deviation, deviation].

        Returns a list that includes start, control points, and end so callers
        can pass directly to a bezier interpolator.
        """
        sx, sy = start
        ex, ey = end
        points: list[tuple[float, float]] = [start]

        for i in range(1, num_controls + 1):
            t = i / (num_controls + 1)
            mid_x = sx + t * (ex - sx)
            mid_y = sy + t * (ey - sy)
            # Perpendicular offset
            dx = random.uniform(-deviation, deviation)
            dy = random.uniform(-deviation, deviation)
            points.append((mid_x + dx, mid_y + dy))

        points.append(end)
        return points

    @staticmethod
    def interpolate_bezier(
        points: list[tuple[float, float]], steps: int = 20
    ) -> list[tuple[int, int]]:
        """De Casteljau bezier interpolation over *steps* equally-spaced t values.

        Returns a list of integer (x, y) pixel positions along the curve.
        """
        if steps < 2:
            steps = 2

        result: list[tuple[int, int]] = []
        for i in range(steps):
            t = i / (steps - 1)
            pts = list(points)
            while len(pts) > 1:
                pts = [
                    (
                        pts[j][0] * (1 - t) + pts[j + 1][0] * t,
                        pts[j][1] * (1 - t) + pts[j + 1][1] * t,
                    )
                    for j in range(len(pts) - 1)
                ]
            result.append((int(pts[0][0]), int(pts[0][1])))
        return result
