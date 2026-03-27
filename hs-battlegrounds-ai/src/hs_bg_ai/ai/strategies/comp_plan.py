"""CompPlanStrategy — long-term composition planning."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from hs_bg_ai.ai.evaluator import BoardEvaluator, COMP_ARCHETYPES
from hs_bg_ai.models.enums import MinionType
from hs_bg_ai.models.game_state import GameState

logger = logging.getLogger(__name__)


@dataclass
class CompPlan:
    """Recommended composition direction and priority types."""

    direction: str = "flexible"
    priority_types: list[MinionType] = None  # type: ignore[assignment]
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.priority_types is None:
            self.priority_types = []


class CompPlanStrategy:
    """Determine the best composition direction for the game.

    Tracks:
    - 10 comp archetypes: beasts, mechs, dragons, murlocs, elementals,
      undead, nagas, quilboar, pirates, demons, menagerie.
    - Switches from "flexible" to a committed comp around tier 3-4.
    """

    def __init__(self, evaluator: BoardEvaluator) -> None:
        self._evaluator = evaluator

    def evaluate(self, state: GameState) -> CompPlan:
        """Return a composition plan based on the current board."""
        assessment = self._evaluator.evaluate_board(state)
        comp_scores = assessment.comp_scores

        if not comp_scores:
            return CompPlan(direction="flexible", confidence=0.0)

        # Sort by score.
        ranked = sorted(comp_scores.items(), key=lambda x: x[1], reverse=True)
        best_name, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        # Commitment threshold: higher tiers mean we should commit.
        tier = state.resources.tavern_tier
        board_size = len(state.board)

        # Confidence based on how dominant the leading comp is.
        if best_score > 0 and board_size > 0:
            confidence = min(1.0, best_score / (board_size * 2.0))
        else:
            confidence = 0.0

        # Only commit if we have enough evidence.
        commit_threshold = 0.4 if tier >= 3 else 0.6

        if confidence >= commit_threshold and best_score > second_score * 1.5:
            types = list(COMP_ARCHETYPES.get(best_name, set()))
            return CompPlan(
                direction=best_name,
                priority_types=types,
                confidence=confidence,
            )

        return CompPlan(direction="flexible", confidence=confidence)
