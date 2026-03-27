"""QuestSelectStrategy — pick the best quest when offered."""

from __future__ import annotations

from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType
from hs_bg_ai.models.game_state import GameState


class QuestSelectStrategy:
    """Pick the best quest from the selection.

    Placeholder implementation — selects the first quest by default.
    Real implementation would evaluate quest difficulty vs. reward
    based on current board state and composition direction.
    """

    def plan(self, state: GameState) -> list[GameAction]:
        """Return a SELECT_QUEST action for the best available quest."""
        if not state.quest_choices:
            return []

        # Placeholder: pick the first quest.
        return [
            GameAction(
                action_type=ActionType.SELECT_QUEST,
                source_index=0,
                priority=100,
                reason="Select quest (placeholder: first option)",
            )
        ]
