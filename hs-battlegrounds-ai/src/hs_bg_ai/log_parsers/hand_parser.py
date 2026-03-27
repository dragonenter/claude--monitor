"""Parse hand zone events from Hearthstone logs."""

from __future__ import annotations

import re

from .base import BaseLogParser, LogEvent

# A card entering or leaving the HAND zone.
_HAND_ZONE_CHANGE = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<card_id>\w+).*?id=(?P<entity_id>\d+).*?\]\s+"
    r"tag=ZONE\s+value=(?P<zone>\w+)"
)

# A card's zone position (slot within hand).
_ZONE_POSITION = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<card_id>\w+).*?id=(?P<entity_id>\d+).*?\]\s+"
    r"tag=ZONE_POSITION\s+value=(?P<position>\d+)"
)


class HandParser(BaseLogParser):
    PARSER_NAME = "hand"
    LINE_PATTERNS = [_HAND_ZONE_CHANGE, _ZONE_POSITION]

    def parse(self, line: str) -> LogEvent | None:
        m = _HAND_ZONE_CHANGE.search(line)
        if m:
            zone = m.group("zone")
            card_id = m.group("card_id")
            entity_id = int(m.group("entity_id"))

            if zone == "HAND":
                return LogEvent(
                    event_type="card_to_hand",
                    data={"card_id": card_id, "entity_id": entity_id},
                )
            # Card left hand (played, sold, etc.) — recorded as a generic zone move.
            # Only emit if previous zone was HAND; caller must track that.

        m = _ZONE_POSITION.search(line)
        if m:
            return LogEvent(
                event_type="hand_position",
                data={
                    "card_id": m.group("card_id"),
                    "entity_id": int(m.group("entity_id")),
                    "position": int(m.group("position")),
                },
            )

        return None
