"""Parse turn transitions and phase changes from Hearthstone logs."""

from __future__ import annotations

import re

from .base import BaseLogParser, LogEvent

# Turn / step changes in PowerTaskList format.
_STEP_CHANGE = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+Entity=GameEntity\s+"
    r"tag=STEP\s+value=(?P<step>\w+)"
)
_TURN_CHANGE = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+Entity=GameEntity\s+"
    r"tag=TURN\s+value=(?P<turn>\d+)"
)
_NEXT_STEP = re.compile(
    r"GameState\.DebugPrintPower\(\)\s*-\s*TAG_CHANGE\s+Entity=GameEntity\s+"
    r"tag=NEXT_STEP\s+value=(?P<step>\w+)"
)

# Map HS step values to meaningful phase names.
_STEP_MAP = {
    "MAIN_ACTION": "recruit",
    "MAIN_START": "combat_start",
    "MAIN_END": "combat_end",
    "FINAL_WRAPUP": "game_over",
}


class TurnParser(BaseLogParser):
    PARSER_NAME = "turn"
    LINE_PATTERNS = [_STEP_CHANGE, _TURN_CHANGE, _NEXT_STEP]

    def parse(self, line: str) -> LogEvent | None:
        m = _TURN_CHANGE.search(line)
        if m:
            return LogEvent(
                event_type="turn_change",
                data={"turn_number": int(m.group("turn"))},
            )

        m = _STEP_CHANGE.search(line)
        if m:
            step = m.group("step")
            phase = _STEP_MAP.get(step, step.lower())
            return LogEvent(
                event_type="phase_change",
                data={"step": step, "phase": phase},
            )

        m = _NEXT_STEP.search(line)
        if m:
            step = m.group("step")
            phase = _STEP_MAP.get(step, step.lower())
            return LogEvent(
                event_type="next_phase",
                data={"step": step, "phase": phase},
            )

        return None
