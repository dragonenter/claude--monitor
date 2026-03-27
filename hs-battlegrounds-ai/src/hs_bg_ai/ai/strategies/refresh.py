"""RefreshStrategy — decide whether to reroll the shop."""

from __future__ import annotations

from hs_bg_ai.ai.evaluator import BoardEvaluator
from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType
from hs_bg_ai.models.game_state import GameState


class RefreshStrategy:
    """Decide when refreshing is worthwhile.

    Rules:
    - Don't refresh if gold < 2 (need 1 for refresh + at least 1 to buy).
    - Refresh if shop has no good options and we have gold to spare.
    - Cap refreshes per turn (configurable).
    """

    def __init__(self, evaluator: BoardEvaluator, max_refreshes: int = 3) -> None:
        self._evaluator = evaluator
        self._max_refreshes = max_refreshes

    def plan(self, state: GameState, refreshes_done: int = 0) -> list[GameAction]:
        """Return a refresh action if refreshing is a good idea."""
        actions: list[GameAction] = []

        # Don't refresh with < 2 gold.
        if state.resources.gold < 2:
            return actions

        # Respect refresh cap.
        if refreshes_done >= self._max_refreshes:
            return actions

        # Evaluate current shop quality.
        if not state.shop:
            # Empty shop — should refresh.
            actions.append(
                GameAction(
                    action_type=ActionType.REFRESH,
                    priority=30,
                    reason="Shop empty, refresh",
                )
            )
            return actions

        # Score best available minion.
        best_score = max(
            self._evaluator.score_shop_minion(m, state) for m in state.shop
        )

        # Refresh if best shop option is weak.
        threshold = 3.0 + state.resources.tavern_tier * 0.5
        if best_score < threshold and state.resources.gold >= 4:
            # Need at least 4 gold: 1 refresh + 3 buy.
            actions.append(
                GameAction(
                    action_type=ActionType.REFRESH,
                    priority=25,
                    reason=f"Shop weak (best={best_score:.1f} < {threshold:.1f})",
                )
            )

        return actions
