"""ExecRecovery: detect execution failures and retry or skip actions."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

from .base import BaseRecovery


class ExecRecovery(BaseRecovery):
    """Recovery handler for action execution failures.

    When an action fails :attr:`MAX_RETRIES` times, it is skipped so the
    bot can continue with the remainder of the plan.

    Parameters
    ----------
    on_skip:
        Optional async callback invoked when an action is permanently skipped.
        Signature: ``async def on_skip(action: Any) -> None``.
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 0.5

    def __init__(
        self,
        on_skip: Callable[[Any], Coroutine[None, None, None]] | None = None,
    ) -> None:
        self._failure_count: int = 0
        self._last_failed_action: Any = None
        self._on_skip = on_skip

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        """Return ``True`` when the failure counter exceeds zero."""
        return self._failure_count > 0

    def record_failure(self, action: Any = None) -> None:
        """Increment the failure counter and store the failing action."""
        self._failure_count += 1
        self._last_failed_action = action

    def reset(self) -> None:
        """Clear failure state after a successful action or skip."""
        self._failure_count = 0
        self._last_failed_action = None

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    async def recover(self, timeout: float = 30.0) -> bool:  # noqa: ARG002
        """Decide whether to retry or skip the last failed action.

        Returns ``True`` if the caller should retry, ``False`` to skip.
        """
        await asyncio.sleep(0)

        if self._failure_count < self.MAX_RETRIES:
            # Signal retry
            return True

        # Max retries exceeded — skip and notify
        if self._on_skip is not None:
            try:
                await self._on_skip(self._last_failed_action)
            except Exception:  # noqa: BLE001
                pass

        self.reset()
        return False

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def last_failed_action(self) -> Any:
        return self._last_failed_action
