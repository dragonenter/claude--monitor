"""Tests for MouseController (headless — no real display required)."""

from __future__ import annotations

import pytest

from hs_bg_ai.config import MouseConfig
from hs_bg_ai.executor.mouse import MouseController
from hs_bg_ai.executor.timing import TimingController


@pytest.fixture
def mouse() -> MouseController:
    cfg = MouseConfig(bezier_deviation=5.0, click_delay_min=0.0, click_delay_max=0.001)
    tc = TimingController()
    return MouseController(config=cfg, timing=tc)


class TestMouseController:
    @pytest.mark.asyncio
    async def test_click_does_not_raise_without_display(self, mouse: MouseController) -> None:
        """click() should succeed silently on headless systems."""
        await mouse.click(100, 200)

    @pytest.mark.asyncio
    async def test_right_click_does_not_raise(self, mouse: MouseController) -> None:
        await mouse.right_click(300, 400)

    @pytest.mark.asyncio
    async def test_drag_does_not_raise(self, mouse: MouseController) -> None:
        await mouse.drag(100, 100, 500, 500)

    @pytest.mark.asyncio
    async def test_move_does_not_raise(self, mouse: MouseController) -> None:
        await mouse.move(960, 540)

    def test_build_path_returns_list_of_int_tuples(self, mouse: MouseController) -> None:
        path = mouse._build_path((0, 0), (200, 200))
        assert len(path) > 0
        for x, y in path:
            assert isinstance(x, int)
            assert isinstance(y, int)

    def test_build_path_starts_and_ends_at_endpoints(self, mouse: MouseController) -> None:
        path = mouse._build_path((10, 20), (310, 420))
        assert path[0] == (10, 20)
        assert path[-1] == (310, 420)

    def test_default_config(self) -> None:
        mc = MouseController()
        assert mc._config is not None

    def test_click_delay_in_range(self, mouse: MouseController) -> None:
        for _ in range(20):
            delay = mouse._click_delay()
            assert 0.0 <= delay <= 0.001
