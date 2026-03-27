"""Action-related data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import ActionType


@dataclass
class GameAction:
    """A single action the bot wants to perform."""

    action_type: ActionType
    source_index: int | None = None
    target_index: int | None = None
    card_id: str | None = None
    priority: int = 0
    reason: str = ""


@dataclass
class ActionResult:
    """Outcome of executing a single action."""

    action: GameAction
    success: bool
    error: str | None = None
    duration_ms: int = 0


@dataclass
class ActionPlan:
    """A sequence of actions for one turn."""

    actions: list[GameAction] = field(default_factory=list)
    estimated_time_seconds: float = 0.0
    confidence: float = 0.0
    turn_number: int = 0
