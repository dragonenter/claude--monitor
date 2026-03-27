"""TimeManager: per-turn timer tracking elapsed/remaining time."""

from __future__ import annotations

import time

from hs_bg_ai.config import TimeConfig


class TimeManager:
    """Tracks how much time is left in the current recruit phase.

    Call :meth:`start_turn` at the beginning of each recruit phase.
    """

    def __init__(self, config: TimeConfig | None = None) -> None:
        self._config = config or TimeConfig()
        self._turn_start: float | None = None
        self._turn_duration: float = self._config.turn_duration

    # ------------------------------------------------------------------
    # Turn lifecycle
    # ------------------------------------------------------------------

    def start_turn(self, is_first_turn: bool = False) -> None:
        """Record the start of a new recruit phase.

        Parameters
        ----------
        is_first_turn:
            When ``True``, uses the shorter ``first_turn_duration`` from config.
        """
        self._turn_start = time.monotonic()
        if is_first_turn:
            self._turn_duration = self._config.first_turn_duration
        else:
            self._turn_duration = self._config.turn_duration

    # ------------------------------------------------------------------
    # Time queries
    # ------------------------------------------------------------------

    @property
    def elapsed(self) -> float:
        """Seconds elapsed since :meth:`start_turn` was called.

        Returns 0.0 if no turn is in progress.
        """
        if self._turn_start is None:
            return 0.0
        return time.monotonic() - self._turn_start

    @property
    def remaining(self) -> float:
        """Seconds remaining in the current turn (clamped to 0).

        Returns the full ``turn_duration`` if no turn is in progress.
        """
        if self._turn_start is None:
            return self._turn_duration
        remaining = self._turn_duration - self.elapsed
        return max(0.0, remaining)

    def should_end_turn(self) -> bool:
        """Return ``True`` when time is within the safety margin or has expired."""
        return self.remaining <= self._config.safety_margin

    def can_fit_action(self, estimated_seconds: float) -> bool:
        """Return ``True`` when *estimated_seconds* fits within the safe window.

        An action "fits" if completing it still leaves enough time to end the
        turn safely (i.e. remaining time > safety_margin + estimated_seconds).
        """
        return self.remaining > (self._config.safety_margin + estimated_seconds)
