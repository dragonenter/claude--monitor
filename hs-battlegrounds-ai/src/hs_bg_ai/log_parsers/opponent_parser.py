"""Parse opponent-related events from Hearthstone logs."""

from __future__ import annotations

import re

from .base import BaseLogParser, LogEvent

# Opponent next combat assignment.
_NEXT_OPPONENT = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=(?P<player_name>[^\[]+?\S)\s+"
    r"tag=NEXT_OPPONENT_PLAYER_ID\s+value=(?P<opponent_id>\d+)"
)

# Opponent death / elimination.
_PLAYER_LEADERBOARD = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=(?P<player_name>[^\[]+?\S)\s+"
    r"tag=PLAYER_LEADERBOARD_PLACE\s+value=(?P<placement>\d+)"
)

# Opponent hero health (same format as own hero, but we track all hero entities).
_OPPONENT_HEALTH = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+"
    r"Entity=\[.*?cardId=(?P<hero_id>TB_BaconShop_HERO_\w+).*?zone=PLAY.*?\]\s+"
    r"tag=(?P<tag>HEALTH|DAMAGE)\s+value=(?P<value>\d+)"
)


class OpponentParser(BaseLogParser):
    PARSER_NAME = "opponent"
    LINE_PATTERNS = [_NEXT_OPPONENT, _PLAYER_LEADERBOARD, _OPPONENT_HEALTH]

    def parse(self, line: str) -> LogEvent | None:
        m = _NEXT_OPPONENT.search(line)
        if m:
            return LogEvent(
                event_type="next_opponent",
                data={
                    "player_name": m.group("player_name").strip(),
                    "opponent_id": int(m.group("opponent_id")),
                },
            )

        m = _PLAYER_LEADERBOARD.search(line)
        if m:
            return LogEvent(
                event_type="player_placement",
                data={
                    "player_name": m.group("player_name").strip(),
                    "placement": int(m.group("placement")),
                },
            )

        m = _OPPONENT_HEALTH.search(line)
        if m:
            return LogEvent(
                event_type="opponent_health_change",
                data={
                    "hero_id": m.group("hero_id"),
                    "tag": m.group("tag").lower(),
                    "value": int(m.group("value")),
                },
            )

        return None
