"""Parse hero-related events from Hearthstone logs."""

from __future__ import annotations

import re

from .base import BaseLogParser, LogEvent

# Hero entity creation / selection.
_HERO_ENTITY = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*FULL_ENTITY\s+-\s+Updating\s+"
    r"\[.*?cardId=(?P<hero_id>TB_BaconShop_HERO_\w+).*?\]"
)

# Hero damage / health change.
_HERO_HEALTH = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<hero_id>TB_BaconShop_HERO_\w+).*?\]\s+"
    r"tag=(?P<tag>HEALTH|DAMAGE|ARMOR)\s+value=(?P<value>\d+)"
)

# Hero power used.
_HERO_POWER_USED = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<power_id>TB_BaconShop_HP_\w+).*?\]\s+"
    r"tag=EXHAUSTED\s+value=(?P<value>\d+)"
)

# Hero selection choices (in hero pick phase).
_HERO_CHOICE = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<hero_id>TB_BaconShop_HERO_\w+).*?\]\s+"
    r"tag=BACON_HERO_CAN_BE_DRAFTED\s+value=1"
)


class HeroParser(BaseLogParser):
    PARSER_NAME = "hero"
    LINE_PATTERNS = [_HERO_ENTITY, _HERO_HEALTH, _HERO_POWER_USED, _HERO_CHOICE]

    def parse(self, line: str) -> LogEvent | None:
        m = _HERO_CHOICE.search(line)
        if m:
            return LogEvent(
                event_type="hero_choice",
                data={"hero_id": m.group("hero_id")},
            )

        m = _HERO_POWER_USED.search(line)
        if m:
            exhausted = int(m.group("value")) > 0
            return LogEvent(
                event_type="hero_power_used",
                data={
                    "power_id": m.group("power_id"),
                    "exhausted": exhausted,
                },
            )

        m = _HERO_HEALTH.search(line)
        if m:
            return LogEvent(
                event_type="hero_health_change",
                data={
                    "hero_id": m.group("hero_id"),
                    "tag": m.group("tag").lower(),
                    "value": int(m.group("value")),
                },
            )

        m = _HERO_ENTITY.search(line)
        if m:
            return LogEvent(
                event_type="hero_discovered",
                data={"hero_id": m.group("hero_id")},
            )

        return None
