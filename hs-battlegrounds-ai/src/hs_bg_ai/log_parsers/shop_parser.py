"""Parse shop (Bob's Tavern) events from Hearthstone logs."""

from __future__ import annotations

import re

from .base import BaseLogParser, LogEvent

# Minion entering the SETASIDE zone with BACON tag indicates shop offering.
_ZONE_SETASIDE = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<card_id>\w+).*?zone=SETASIDE.*?\]\s+"
    r"tag=ZONE\s+value=SETASIDE"
)

# A minion moving to the shop zone (PLAY zone for the tavern side).
_SHOP_OFFER = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*FULL_ENTITY\s+-\s+Updating\s+"
    r"\[.*?cardId=(?P<card_id>\w+).*?\]\s+CardID=(?P<card_id2>\w+)"
)

# Tag changes on a shop entity (ATK, HEALTH, ZONE, etc.)
_TAG_CHANGE_ENTITY = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<card_id>\w+).*?id=(?P<entity_id>\d+).*?\]\s+"
    r"tag=(?P<tag>\w+)\s+value=(?P<value>\w+)"
)

# Refresh / reroll indication.
_SHOP_REFRESH = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=.*?tag=BACON_REFRESH\s+value=(?P<value>\d+)"
)

# Freeze indication.
_SHOP_FREEZE = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=.*?tag=BACON_FROZEN\s+value=(?P<value>\d+)"
)


class ShopParser(BaseLogParser):
    PARSER_NAME = "shop"
    LINE_PATTERNS = [_TAG_CHANGE_ENTITY, _SHOP_REFRESH, _SHOP_FREEZE]

    def parse(self, line: str) -> LogEvent | None:
        m = _SHOP_FREEZE.search(line)
        if m:
            frozen = int(m.group("value")) > 0
            return LogEvent(
                event_type="shop_frozen",
                data={"frozen": frozen},
            )

        m = _SHOP_REFRESH.search(line)
        if m:
            return LogEvent(
                event_type="shop_refresh",
                data={},
            )

        m = _TAG_CHANGE_ENTITY.search(line)
        if m:
            tag = m.group("tag")
            value = m.group("value")
            card_id = m.group("card_id")
            entity_id = m.group("entity_id")

            # Minion entering shop zone.
            if tag == "ZONE" and value == "SETASIDE":
                return LogEvent(
                    event_type="shop_offer",
                    data={
                        "card_id": card_id,
                        "entity_id": int(entity_id),
                    },
                )

            # Minion bought (moved from SETASIDE to HAND).
            if tag == "ZONE" and value == "HAND":
                return LogEvent(
                    event_type="minion_bought",
                    data={
                        "card_id": card_id,
                        "entity_id": int(entity_id),
                    },
                )

        return None
