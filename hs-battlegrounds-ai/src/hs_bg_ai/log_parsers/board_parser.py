"""Parse board zone events from Hearthstone logs."""

from __future__ import annotations

import re

from .base import BaseLogParser, LogEvent

# Entity entering or leaving the PLAY (board) zone.
_BOARD_ZONE_CHANGE = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<card_id>\w+).*?id=(?P<entity_id>\d+).*?\]\s+"
    r"tag=ZONE\s+value=PLAY"
)

# Entity leaving the board (zone changes away from PLAY).
_LEAVE_BOARD = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<card_id>\w+).*?id=(?P<entity_id>\d+)"
    r".*?zone=PLAY.*?\]\s+tag=ZONE\s+value=(?P<new_zone>\w+)"
)

# Stat changes for entities on the board.
_STAT_CHANGE = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<card_id>\w+).*?id=(?P<entity_id>\d+).*?\]\s+"
    r"tag=(?P<tag>ATK|HEALTH)\s+value=(?P<value>\d+)"
)


class BoardParser(BaseLogParser):
    PARSER_NAME = "board"
    LINE_PATTERNS = [_BOARD_ZONE_CHANGE, _LEAVE_BOARD, _STAT_CHANGE]

    def parse(self, line: str) -> LogEvent | None:
        # Check board entry first.
        m = _BOARD_ZONE_CHANGE.search(line)
        if m:
            return LogEvent(
                event_type="minion_to_board",
                data={
                    "card_id": m.group("card_id"),
                    "entity_id": int(m.group("entity_id")),
                },
            )

        # Check board exit.
        m = _LEAVE_BOARD.search(line)
        if m:
            new_zone = m.group("new_zone")
            if new_zone != "PLAY":
                return LogEvent(
                    event_type="minion_left_board",
                    data={
                        "card_id": m.group("card_id"),
                        "entity_id": int(m.group("entity_id")),
                        "new_zone": new_zone,
                    },
                )

        # Stat changes.
        m = _STAT_CHANGE.search(line)
        if m:
            tag = m.group("tag").lower()  # "atk" or "health"
            return LogEvent(
                event_type="stat_change",
                data={
                    "card_id": m.group("card_id"),
                    "entity_id": int(m.group("entity_id")),
                    "stat": tag,
                    "value": int(m.group("value")),
                },
            )

        return None
