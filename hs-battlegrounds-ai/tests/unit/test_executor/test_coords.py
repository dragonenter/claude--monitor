"""Tests for CoordMapper."""

from __future__ import annotations

import pytest

from hs_bg_ai.core.errors import CoordMappingError
from hs_bg_ai.executor.coords import (
    CoordMapper,
    _BOARD_SLOT_COUNT,
    _HAND_SLOT_COUNT,
    _SHOP_SLOT_COUNT,
)


@pytest.fixture
def mapper() -> CoordMapper:
    return CoordMapper()


class TestShopSlot:
    def test_first_slot(self, mapper: CoordMapper) -> None:
        x, y = mapper.shop_slot(0)
        assert isinstance(x, int)
        assert isinstance(y, int)

    def test_last_slot(self, mapper: CoordMapper) -> None:
        x, y = mapper.shop_slot(_SHOP_SLOT_COUNT - 1)
        assert x > 0
        assert y > 0

    def test_all_slots_unique_x(self, mapper: CoordMapper) -> None:
        xs = [mapper.shop_slot(i)[0] for i in range(_SHOP_SLOT_COUNT)]
        assert len(set(xs)) == _SHOP_SLOT_COUNT, "Each shop slot should have a unique X coord"

    def test_negative_index_raises(self, mapper: CoordMapper) -> None:
        with pytest.raises(CoordMappingError):
            mapper.shop_slot(-1)

    def test_out_of_range_raises(self, mapper: CoordMapper) -> None:
        with pytest.raises(CoordMappingError):
            mapper.shop_slot(_SHOP_SLOT_COUNT)

    def test_same_y_for_all(self, mapper: CoordMapper) -> None:
        ys = {mapper.shop_slot(i)[1] for i in range(_SHOP_SLOT_COUNT)}
        assert len(ys) == 1, "All shop slots should share the same Y coordinate"


class TestBoardSlot:
    def test_valid_range(self, mapper: CoordMapper) -> None:
        for i in range(_BOARD_SLOT_COUNT):
            x, y = mapper.board_slot(i)
            assert x > 0 and y > 0

    def test_invalid_high(self, mapper: CoordMapper) -> None:
        with pytest.raises(CoordMappingError):
            mapper.board_slot(_BOARD_SLOT_COUNT)

    def test_invalid_low(self, mapper: CoordMapper) -> None:
        with pytest.raises(CoordMappingError):
            mapper.board_slot(-1)

    def test_monotonically_increasing_x(self, mapper: CoordMapper) -> None:
        xs = [mapper.board_slot(i)[0] for i in range(_BOARD_SLOT_COUNT)]
        assert xs == sorted(xs)


class TestHandSlot:
    def test_valid_range(self, mapper: CoordMapper) -> None:
        for i in range(_HAND_SLOT_COUNT):
            x, y = mapper.hand_slot(i)
            assert x > 0 and y > 0

    def test_invalid_raises(self, mapper: CoordMapper) -> None:
        with pytest.raises(CoordMappingError):
            mapper.hand_slot(_HAND_SLOT_COUNT)


class TestButtons:
    def test_all_buttons_return_valid_coords(self, mapper: CoordMapper) -> None:
        for fn_name in (
            "hero_power_button",
            "refresh_button",
            "upgrade_button",
            "freeze_button",
            "end_turn_button",
        ):
            x, y = getattr(mapper, fn_name)()
            assert isinstance(x, int) and x > 0, f"{fn_name} x invalid"
            assert isinstance(y, int) and y > 0, f"{fn_name} y invalid"

    def test_all_buttons_within_1080p(self, mapper: CoordMapper) -> None:
        for fn_name in (
            "hero_power_button",
            "refresh_button",
            "upgrade_button",
            "freeze_button",
            "end_turn_button",
        ):
            x, y = getattr(mapper, fn_name)()
            assert 0 <= x <= 1920, f"{fn_name} x={x} out of screen"
            assert 0 <= y <= 1080, f"{fn_name} y={y} out of screen"
