"""Tests for ActionQueue."""

from __future__ import annotations

import asyncio

import pytest

from hs_bg_ai.core.errors import ExecutionError
from hs_bg_ai.executor.queue import ActionQueue, MAX_QUEUE_SIZE
from hs_bg_ai.models.actions import ActionPlan, ActionResult, GameAction
from hs_bg_ai.models.enums import ActionType


def make_action(action_type: ActionType = ActionType.REFRESH) -> GameAction:
    return GameAction(action_type=action_type)


def make_plan(n: int = 3) -> ActionPlan:
    return ActionPlan(actions=[make_action() for _ in range(n)])


@pytest.fixture
def queue() -> ActionQueue:
    return ActionQueue()


class TestEnqueue:
    def test_enqueue_single(self, queue: ActionQueue) -> None:
        queue.enqueue(make_action())
        assert queue.pending == 1

    def test_enqueue_up_to_max(self, queue: ActionQueue) -> None:
        for _ in range(MAX_QUEUE_SIZE):
            queue.enqueue(make_action())
        assert queue.pending == MAX_QUEUE_SIZE

    def test_enqueue_beyond_max_raises(self, queue: ActionQueue) -> None:
        for _ in range(MAX_QUEUE_SIZE):
            queue.enqueue(make_action())
        with pytest.raises(ExecutionError):
            queue.enqueue(make_action())

    def test_is_empty_initially(self, queue: ActionQueue) -> None:
        assert queue.is_empty

    def test_not_empty_after_enqueue(self, queue: ActionQueue) -> None:
        queue.enqueue(make_action())
        assert not queue.is_empty


class TestCancelRemaining:
    def test_cancel_clears_queue(self, queue: ActionQueue) -> None:
        for _ in range(5):
            queue.enqueue(make_action())
        count = queue.cancel_remaining()
        assert count == 5
        assert queue.is_empty

    def test_cancel_empty_queue_returns_zero(self, queue: ActionQueue) -> None:
        assert queue.cancel_remaining() == 0


class TestExecutePlan:
    @pytest.mark.asyncio
    async def test_execute_plan_returns_results(self, queue: ActionQueue) -> None:
        plan = make_plan(3)
        results = await queue.execute_plan(plan)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, ActionResult)
            assert r.success is True

    @pytest.mark.asyncio
    async def test_execute_empty_plan(self, queue: ActionQueue) -> None:
        plan = make_plan(0)
        results = await queue.execute_plan(plan)
        assert results == []

    @pytest.mark.asyncio
    async def test_executor_failure_recorded(self, queue: ActionQueue) -> None:
        async def failing_executor(action: GameAction) -> bool:
            raise RuntimeError("boom")

        plan = make_plan(2)
        results = await queue.execute_plan(plan, executor=failing_executor)
        for r in results:
            assert r.success is False
            assert "boom" in (r.error or "")

    @pytest.mark.asyncio
    async def test_custom_executor_called(self, queue: ActionQueue) -> None:
        called: list[GameAction] = []

        async def tracking_executor(action: GameAction) -> bool:
            called.append(action)
            return True

        plan = make_plan(4)
        await queue.execute_plan(plan, executor=tracking_executor)
        assert len(called) == 4

    @pytest.mark.asyncio
    async def test_results_have_duration_ms(self, queue: ActionQueue) -> None:
        plan = make_plan(2)
        results = await queue.execute_plan(plan)
        for r in results:
            assert r.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_cancel_mid_execution(self) -> None:
        """Cancelling while executing stops remaining actions."""
        q = ActionQueue()
        actions_executed: list[int] = []

        async def slow_executor(action: GameAction) -> bool:
            actions_executed.append(1)
            if len(actions_executed) == 1:
                q.cancel_remaining()
            return True

        plan = ActionPlan(actions=[make_action() for _ in range(5)])
        results = await q.execute_plan(plan, executor=slow_executor)
        # Only 1 action ran (the queue was cleared after that)
        assert len(results) == 1
