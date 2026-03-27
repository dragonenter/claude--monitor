"""TripleStrategy — manage triple awareness and discover decisions."""

from __future__ import annotations

from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType
from hs_bg_ai.models.game_state import GameState


class TripleStrategy:
    """Manage triple (golden) minion awareness.

    - If 2 copies of a minion exist on board/hand, prioritise buying the 3rd.
    - On discover from a triple, pick the highest-tier minion that fits comp.
    """

    def get_triple_targets(self, state: GameState) -> list[str]:
        """Return card_ids that are one copy away from tripling."""
        return state.triple_progress.get_candidates()

    def should_prioritise_buy(self, card_id: str, state: GameState) -> bool:
        """Return True if buying this card_id would complete a triple."""
        return state.triple_progress.get_count(card_id) >= 2

    def plan_discover(self, state: GameState) -> list[GameAction]:
        """If discover choices are available, pick the best one.

        This is a placeholder — real implementation would score each
        discover option based on comp direction and tier.
        """
        if not state.discover_choices:
            return []

        # Pick first discover option by default (placeholder).
        return [
            GameAction(
                action_type=ActionType.TRIPLE_DISCOVER,
                source_index=0,
                priority=95,
                reason="Triple discover: pick best option",
            )
        ]
