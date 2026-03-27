"""Tests for BaseRecovery and the recover_with_retries helper."""

from __future__ import annotations

import asyncio

import pytest

from hs_bg_ai.recovery.base import BaseRecovery


# ---------------------------------------------------------------------------
# Concrete stub implementations
# ---------------------------------------------------------------------------


class AlwaysDetectedRecovery(BaseRecovery):
    """Simulates a condition that is always detected but always fails to recover."""

    MAX_RETRIES = 3
    RETRY_DELAY = 0.0  # instant for tests

    def detect(self) -> bool:
        return True

    async def recover(self, timeout: float = 30.0) -> bool:
        return False


class EventuallyRecovery(BaseRecovery):
    """Recovers on the N-th attempt."""

    MAX_RETRIES = 3
    RETRY_DELAY = 0.0

    def __init__(self, succeed_on: int = 2) -> None:
        self._attempts = 0
        self._succeed_on = succeed_on

    def detect(self) -> bool:
        return self._attempts < self._succeed_on

    async def recover(self, timeout: float = 30.0) -> bool:
        self._attempts += 1
        return self._attempts >= self._succeed_on


class ImmediateRecovery(BaseRecovery):
    """Always succeeds on first attempt."""

    MAX_RETRIES = 3
    RETRY_DELAY = 0.0

    def detect(self) -> bool:
        return True

    async def recover(self, timeout: float = 30.0) -> bool:
        return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDetect:
    def test_always_detected(self) -> None:
        r = AlwaysDetectedRecovery()
        assert r.detect() is True

    def test_not_detected_after_recovery(self) -> None:
        # succeed_on=1: after one successful recover(), _attempts==1 >= 1, so detect() is False
        r = EventuallyRecovery(succeed_on=1)
        # Run recovery to advance _attempts to 1
        asyncio.get_event_loop().run_until_complete(r.recover())
        assert not r.detect()


class TestRecover:
    @pytest.mark.asyncio
    async def test_immediate_recover_returns_true(self) -> None:
        r = ImmediateRecovery()
        assert await r.recover() is True

    @pytest.mark.asyncio
    async def test_always_fail_recover_returns_false(self) -> None:
        r = AlwaysDetectedRecovery()
        assert await r.recover() is False

    @pytest.mark.asyncio
    async def test_eventual_recover_succeeds_on_nth(self) -> None:
        r = EventuallyRecovery(succeed_on=2)
        assert await r.recover() is False  # 1st attempt
        assert await r.recover() is True   # 2nd attempt


class TestRecoverWithRetries:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self) -> None:
        r = ImmediateRecovery()
        result = await r.recover_with_retries(timeout=5.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_exhausts_retries_and_returns_false(self) -> None:
        r = AlwaysDetectedRecovery()
        result = await r.recover_with_retries(timeout=5.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self) -> None:
        r = EventuallyRecovery(succeed_on=2)
        result = await r.recover_with_retries(timeout=5.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_timeout_stops_retries(self) -> None:
        """With timeout=0 the first retry should exhaust the budget."""
        r = AlwaysDetectedRecovery()
        result = await r.recover_with_retries(timeout=0.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_count_matches_max(self) -> None:
        attempt_log: list[int] = []

        class CountingRecovery(BaseRecovery):
            MAX_RETRIES = 3
            RETRY_DELAY = 0.0

            def detect(self) -> bool:
                return True

            async def recover(self, timeout: float = 30.0) -> bool:
                attempt_log.append(1)
                return False

        r = CountingRecovery()
        await r.recover_with_retries(timeout=60.0)
        assert len(attempt_log) == CountingRecovery.MAX_RETRIES
