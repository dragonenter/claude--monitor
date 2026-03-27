"""Screenshot capture and recognition subsystem."""

from .capturer import ScreenCapturer
from .recognizer import ScreenRecognizer, StubScreenRecognizer
from .regions import (
    REGION_BOARD,
    REGION_GOLD,
    REGION_HAND,
    REGION_HERO_POWER,
    REGION_SHOP,
    REGION_TAVERN_TIER,
    ScreenRegion,
)

__all__ = [
    "ScreenCapturer",
    "ScreenRecognizer",
    "StubScreenRecognizer",
    "ScreenRegion",
    "REGION_SHOP",
    "REGION_BOARD",
    "REGION_HAND",
    "REGION_GOLD",
    "REGION_HERO_POWER",
    "REGION_TAVERN_TIER",
]
