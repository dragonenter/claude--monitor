"""SellStrategy — decide which minions to sell."""

from __future__ import annotations

from hs_bg_ai.ai.evaluator import BoardEvaluator
from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType
from hs_bg_ai.models.game_state import GameState


class SellStrategy:
    """Decide when and what to sell.

    Sell the weakest minion on the board if:
    - Board is full and we want to buy a better minion.
    - Need gold for an upgrade.
    """

    def __init__(self, evaluator: BoardEvaluator) -> None:
        self._evaluator = evaluator

    def plan(self, state: GameState, need_space: bool = False, need_gold: int = 0) -> list[GameAction]:
        """Return sell actions if selling is beneficial."""
        actions: list[GameAction] = []
        if not state.board:
            return actions

        assessment = self._evaluator.evaluate_board(state)
        if assessment.weakest_index < 0:
            return actions

        should_sell = False

        # Sell if board is full and we need space for a better minion.
        if need_space and state.board_space() == 0:
            should_sell = True

        # Sell if we need gold (e.g. to upgrade).
        if need_gold > 0 and state.resources.gold < need_gold:
            gold_after_sell = state.resources.gold + 1  # Sell gives 1 gold.
            if gold_after_sell >= need_gold or need_gold - gold_after_sell < need_gold - state.resources.gold:
                should_sell = True

        if should_sell:
            idx = assessment.weakest_index
            minion = state.board[idx]
            actions.append(
                GameAction(
                    action_type=ActionType.SELL,
                    source_index=idx,
                    card_id=minion.card_id,
                    priority=50,
                    reason=f"Sell weakest ({minion.name}) for space/gold",
                )
            )

        return actions
