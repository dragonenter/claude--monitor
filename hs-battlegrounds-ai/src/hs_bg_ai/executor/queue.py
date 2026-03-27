"""ActionQueue: FIFO execution queue for game actions."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Callable, Coroutine

from hs_bg_ai.core.errors import ExecutionError
from hs_bg_ai.models.actions import ActionPlan, ActionResult, GameAction

MAX_QUEUE_SIZE = 10


class ActionQueue:
    """FIFO queue that executes GameAction items sequentially.

    Attributes
    ----------
    max_size:
        Maximum number of pending actions (default 10).  Attempting to
        enqueue beyond this limit raises ``ExecutionError``.
    """

    def __init__(self, max_size: int = MAX_QUEUE_SIZE) -> None:
        self.max_size = max_size
        self._queue: deque[GameAction] = deque()
        self._cancelled = False
        self._running = False

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def enqueue(self, action: GameAction) -> None:
        """Add *action* to the tail of the queue.

        Raises
        ------
        ExecutionError
            If the queue is full.
        """
        if len(self._queue) >= self.max_size:
            raise ExecutionError(
                f"ActionQueue is full ({self.max_size} items). "
                "Cannot enqueue more actions."
            )
        self._queue.append(action)

    def cancel_remaining(self) -> int:
        """Discard all pending actions.

        Returns the number of actions that were cancelled.
        """
        count = len(self._queue)
        self._queue.clear()
        self._cancelled = True
        return count

    @property
    def pending(self) -> int:
        """Number of actions currently waiting in the queue."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        return len(self._queue) == 0

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_plan(
        self,
        plan: ActionPlan,
        executor: Callable[[GameAction], Coroutine[None, None, bool]] | None = None,
    ) -> list[ActionResult]:
        """Load *plan* into the queue and execute all actions sequentially.

        Parameters
        ----------
        plan:
            The ``ActionPlan`` whose actions are to be executed.
        executor:
            An async callable ``(action) -> bool`` that performs the action
            and returns ``True`` on success.  When ``None``, a stub that
            always succeeds is used (useful for testing).

        Returns
        -------
        list[ActionResult]
            One result per action in the plan, in order.
        """
        self._cancelled = False
        self._running = True

        # Enqueue all actions from the plan
        for action in plan.actions:
            self.enqueue(action)

        results: list[ActionResult] = []

        try:
            while self._queue and not self._cancelled:
                action = self._queue.popleft()
                start_ms = int(time.monotonic() * 1000)

                try:
                    if executor is not None:
                        success = await executor(action)
                    else:
                        # Default stub: always succeed
                        await asyncio.sleep(0)
                        success = True
                    duration = int(time.monotonic() * 1000) - start_ms
                    results.append(
                        ActionResult(action=action, success=success, duration_ms=duration)
                    )
                except Exception as exc:  # noqa: BLE001
                    duration = int(time.monotonic() * 1000) - start_ms
                    results.append(
                        ActionResult(
                            action=action,
                            success=False,
                            error=str(exc),
                            duration_ms=duration,
                        )
                    )
        finally:
            self._running = False

        return results
