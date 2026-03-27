"""BaseRecovery: abstract base class for all recovery strategies."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod


class BaseRecovery(ABC):
    """Abstract base for error-recovery handlers.

    Subclasses implement :meth:`detect` and :meth:`recover`.

    Class-level constants
    ---------------------
    MAX_RETRIES:
        Maximum number of recovery attempts before giving up.
    RETRY_DELAY:
        Seconds to wait between consecutive retry attempts.
    """

    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 2.0

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def detect(self) -> bool:
        """Return ``True`` when this recovery handler's error condition is active."""

    @abstractmethod
    async def recover(self, timeout: float = 30.0) -> bool:
        """Attempt to recover from the error condition.

        Parameters
        ----------
        timeout:
            Maximum wall-clock seconds to spend on the recovery attempt.

        Returns
        -------
        bool
            ``True`` if recovery succeeded, ``False`` otherwise.
        """

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    async def recover_with_retries(self, timeout: float = 30.0) -> bool:
        """Call :meth:`recover` up to :attr:`MAX_RETRIES` times.

        Waits :attr:`RETRY_DELAY` seconds between attempts (deducted from
        *timeout*).  Returns ``True`` as soon as one attempt succeeds.
        """
        deadline = time.monotonic() + timeout
        for attempt in range(1, self.MAX_RETRIES + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            success = await self.recover(timeout=remaining)
            if success:
                return True
            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_DELAY)
        return False
