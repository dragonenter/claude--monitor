"""Parse resource (gold, tavern tier, upgrade cost) events from Hearthstone logs."""

from __future__ import annotations

import re

from .base import BaseLogParser, LogEvent

# Gold / resource changes — RESOURCES tag on the player entity.
_RESOURCES_TAG = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=(?P<entity>[^\[]+?\S)\s+"
    r"tag=(?P<tag>RESOURCES|RESOURCES_USED|TEMP_RESOURCES)\s+value=(?P<value>\d+)"
)

# Tavern tier (PLAYER_TECH_LEVEL).
_TECH_LEVEL = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=.*?tag=PLAYER_TECH_LEVEL\s+value=(?P<tier>\d+)"
)

# Upgrade cost tracking.
_UPGRADE_COST = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=.*?tag=BACON_UPGRADE_COST\s+value=(?P<cost>\d+)"
)


class ResourceParser(BaseLogParser):
    PARSER_NAME = "resource"
    LINE_PATTERNS = [_RESOURCES_TAG, _TECH_LEVEL, _UPGRADE_COST]

    def parse(self, line: str) -> LogEvent | None:
        m = _TECH_LEVEL.search(line)
        if m:
            return LogEvent(
                event_type="tavern_tier_change",
                data={"tavern_tier": int(m.group("tier"))},
            )

        m = _UPGRADE_COST.search(line)
        if m:
            return LogEvent(
                event_type="upgrade_cost_change",
                data={"upgrade_cost": int(m.group("cost"))},
            )

        m = _RESOURCES_TAG.search(line)
        if m:
            tag = m.group("tag")
            value = int(m.group("value"))
            if tag == "RESOURCES":
                return LogEvent(
                    event_type="gold_change",
                    data={"max_gold": value},
                )
            elif tag == "RESOURCES_USED":
                return LogEvent(
                    event_type="gold_spent",
                    data={"gold_used": value},
                )
            elif tag == "TEMP_RESOURCES":
                return LogEvent(
                    event_type="temp_gold",
                    data={"temp_gold": value},
                )

        return None
