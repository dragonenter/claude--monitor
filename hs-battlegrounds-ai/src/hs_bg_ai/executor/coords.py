"""CoordMapper: maps game logical positions to screen pixel coordinates for 1920x1080."""

from __future__ import annotations

from hs_bg_ai.core.errors import CoordMappingError


# ---------------------------------------------------------------------------
# Layout constants for a 1920x1080 Hearthstone Battlegrounds window
# ---------------------------------------------------------------------------

# Shop slots: 7 slots across the bottom of the shop area
_SHOP_SLOT_Y = 820
_SHOP_SLOT_START_X = 420
_SHOP_SLOT_SPACING = 170
_SHOP_SLOT_COUNT = 7

# Board slots: up to 7 minion positions
_BOARD_SLOT_Y = 600
_BOARD_SLOT_START_X = 330
_BOARD_SLOT_SPACING = 180
_BOARD_SLOT_COUNT = 7

# Hand slots: cards in hand (typically represented as shop purchases or discover)
_HAND_SLOT_Y = 950
_HAND_SLOT_START_X = 650
_HAND_SLOT_SPACING = 150
_HAND_SLOT_COUNT = 10

# Button positions
_HERO_POWER_X = 960
_HERO_POWER_Y = 900

_REFRESH_X = 300
_REFRESH_Y = 850

_UPGRADE_X = 150
_UPGRADE_Y = 750

_FREEZE_X = 300
_FREEZE_Y = 920

_END_TURN_X = 1750
_END_TURN_Y = 540


class CoordMapper:
    """Maps game-logical positions to screen pixel coords for a 1920x1080 display.

    All methods return (x, y) tuples of integer pixel coordinates.
    Raises CoordMappingError when the given index is out of valid range.
    """

    def shop_slot(self, index: int) -> tuple[int, int]:
        """Return pixel center of shop slot *index* (0-based, 0..6)."""
        if not (0 <= index < _SHOP_SLOT_COUNT):
            raise CoordMappingError(
                f"shop_slot index {index!r} out of range [0, {_SHOP_SLOT_COUNT - 1}]"
            )
        x = _SHOP_SLOT_START_X + index * _SHOP_SLOT_SPACING
        return (x, _SHOP_SLOT_Y)

    def board_slot(self, index: int) -> tuple[int, int]:
        """Return pixel center of board slot *index* (0-based, 0..6)."""
        if not (0 <= index < _BOARD_SLOT_COUNT):
            raise CoordMappingError(
                f"board_slot index {index!r} out of range [0, {_BOARD_SLOT_COUNT - 1}]"
            )
        x = _BOARD_SLOT_START_X + index * _BOARD_SLOT_SPACING
        return (x, _BOARD_SLOT_Y)

    def hand_slot(self, index: int) -> tuple[int, int]:
        """Return pixel center of hand slot *index* (0-based, 0..9)."""
        if not (0 <= index < _HAND_SLOT_COUNT):
            raise CoordMappingError(
                f"hand_slot index {index!r} out of range [0, {_HAND_SLOT_COUNT - 1}]"
            )
        x = _HAND_SLOT_START_X + index * _HAND_SLOT_SPACING
        return (x, _HAND_SLOT_Y)

    def hero_power_button(self) -> tuple[int, int]:
        """Return pixel coordinates of the Hero Power button."""
        return (_HERO_POWER_X, _HERO_POWER_Y)

    def refresh_button(self) -> tuple[int, int]:
        """Return pixel coordinates of the Refresh button."""
        return (_REFRESH_X, _REFRESH_Y)

    def upgrade_button(self) -> tuple[int, int]:
        """Return pixel coordinates of the Tavern Upgrade button."""
        return (_UPGRADE_X, _UPGRADE_Y)

    def freeze_button(self) -> tuple[int, int]:
        """Return pixel coordinates of the Freeze button."""
        return (_FREEZE_X, _FREEZE_Y)

    def end_turn_button(self) -> tuple[int, int]:
        """Return pixel coordinates of the End Turn button."""
        return (_END_TURN_X, _END_TURN_Y)
