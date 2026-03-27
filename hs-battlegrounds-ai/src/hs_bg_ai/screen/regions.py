"""Predefined screen regions for a 1920x1080 Hearthstone Battlegrounds window."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenRegion:
    """A rectangular region of the screen.

    Attributes
    ----------
    left:   X coordinate of the left edge.
    top:    Y coordinate of the top edge.
    width:  Width in pixels.
    height: Height in pixels.
    name:   Human-readable label for debugging.
    """

    left: int
    top: int
    width: int
    height: int
    name: str = ""

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def as_dict(self) -> dict[str, int]:
        """Return mss-compatible dict ``{"top", "left", "width", "height"}``."""
        return {
            "top": self.top,
            "left": self.left,
            "width": self.width,
            "height": self.height,
        }


# ---------------------------------------------------------------------------
# Predefined 1080p regions
# ---------------------------------------------------------------------------

REGION_SHOP = ScreenRegion(
    left=330,
    top=720,
    width=1260,
    height=180,
    name="REGION_SHOP",
)

REGION_BOARD = ScreenRegion(
    left=240,
    top=490,
    width=1440,
    height=220,
    name="REGION_BOARD",
)

REGION_HAND = ScreenRegion(
    left=550,
    top=900,
    width=820,
    height=160,
    name="REGION_HAND",
)

REGION_GOLD = ScreenRegion(
    left=100,
    top=820,
    width=200,
    height=60,
    name="REGION_GOLD",
)

REGION_HERO_POWER = ScreenRegion(
    left=870,
    top=840,
    width=180,
    height=100,
    name="REGION_HERO_POWER",
)

REGION_TAVERN_TIER = ScreenRegion(
    left=60,
    top=680,
    width=200,
    height=80,
    name="REGION_TAVERN_TIER",
)
