"""Tests for TimingController."""

from __future__ import annotations

import asyncio

import pytest

from hs_bg_ai.config import TimingConfig
from hs_bg_ai.executor.timing import TimingController


@pytest.fixture
def timing() -> TimingController:
    return TimingController()


@pytest.fixture
def tight_timing() -> TimingController:
    """TimingController with very short delays for fast tests."""
    cfg = TimingConfig(
        action_delay_min=0.0,
        action_delay_max=0.001,
        think_delay_min=0.0,
        think_delay_max=0.001,
    )
    return TimingController(config=cfg)


class TestRandomDelays:
    def test_action_delay_in_range(self, timing: TimingController) -> None:
        for _ in range(20):
            d = timing.random_action_delay()
            assert 0.2 <= d <= 0.6

    def test_think_delay_in_range(self, timing: TimingController) -> None:
        for _ in range(20):
            d = timing.random_think_delay()
            assert 0.3 <= d <= 1.0

    def test_custom_config(self) -> None:
        cfg = TimingConfig(action_delay_min=1.0, action_delay_max=2.0)
        tc = TimingController(config=cfg)
        for _ in range(10):
            d = tc.random_action_delay()
            assert 1.0 <= d <= 2.0


class TestAsyncSleep:
    @pytest.mark.asyncio
    async def test_sleep_action_completes(self, tight_timing: TimingController) -> None:
        await tight_timing.sleep_action()  # should not raise

    @pytest.mark.asyncio
    async def test_sleep_think_completes(self, tight_timing: TimingController) -> None:
        await tight_timing.sleep_think()


class TestBezierControlPoints:
    def test_returns_list_including_start_and_end(self) -> None:
        start = (0.0, 0.0)
        end = (100.0, 100.0)
        pts = TimingController.bezier_control_points(start, end, deviation=5.0, num_controls=2)
        assert pts[0] == start
        assert pts[-1] == end
        assert len(pts) == 4  # start + 2 controls + end

    def test_single_control_point(self) -> None:
        pts = TimingController.bezier_control_points(
            (0.0, 0.0), (50.0, 50.0), deviation=0.0, num_controls=1
        )
        assert len(pts) == 3

    def test_no_deviation_midpoint_on_line(self) -> None:
        pts = TimingController.bezier_control_points(
            (0.0, 0.0), (100.0, 0.0), deviation=0.0, num_controls=1
        )
        mid = pts[1]
        # With zero deviation the midpoint should be exactly on the line
        assert mid == (50.0, 0.0)


class TestInterpolateBezier:
    def test_returns_correct_step_count(self) -> None:
        pts = [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]
        result = TimingController.interpolate_bezier(pts, steps=10)
        assert len(result) == 10

    def test_starts_and_ends_at_endpoints(self) -> None:
        pts = [(0.0, 0.0), (100.0, 0.0)]
        result = TimingController.interpolate_bezier(pts, steps=5)
        assert result[0] == (0, 0)
        assert result[-1] == (100, 0)

    def test_returns_int_tuples(self) -> None:
        pts = [(10.5, 20.5), (90.5, 80.5)]
        result = TimingController.interpolate_bezier(pts, steps=5)
        for x, y in result:
            assert isinstance(x, int)
            assert isinstance(y, int)

    def test_minimum_steps(self) -> None:
        pts = [(0.0, 0.0), (10.0, 10.0)]
        result = TimingController.interpolate_bezier(pts, steps=1)
        # steps is clamped to min 2
        assert len(result) >= 2
