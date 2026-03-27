"""BuyStrategy — decide which minions to buy from the shop."""

from __future__ import annotations

from hs_bg_ai.ai.evaluator import BoardEvaluator
from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType
from hs_bg_ai.models.game_state import GameState


class BuyStrategy:
    """Pick the best minion(s) to buy given current gold and board state.

    Rules:
    - Buy strongest minion that fits composition direction.
    - Prioritise triple completion (if 2 copies exist, buy the 3rd).
    - Don't buy if no gold or no board/hand space.
    """

    def __init__(self, evaluator: BoardEvaluator) -> None:
        self._evaluator = evaluator

    def plan(self, state: GameState) -> list[GameAction]:
        """Return buy actions ranked by priority."""
        actions: list[GameAction] = []
        gold = state.resources.gold
        buy_cost = 3  # Standard buy cost.

        if gold < buy_cost or not state.shop:
            return actions

        # Score all shop minions.
        scored = []
        for i, minion in enumerate(state.shop):
            score = self._evaluator.score_shop_minion(minion, state)
            scored.append((i, minion, score))

        # Sort by score descending.
        scored.sort(key=lambda x: x[2], reverse=True)

        remaining_gold = gold
        hand_space = 10 - state.hand_count()
        board_space = state.board_space()
        available_space = hand_space  # Bought minions go to hand first.

        for i, (slot, minion, score) in enumerate(scored):
            if remaining_gold < buy_cost:
                break
            if available_space <= 0:
                break
            # Only buy if the minion adds value.
            if score < 1.0 and not state.triple_progress.get_count(minion.card_id) >= 2:
                continue

            actions.append(
                GameAction(
                    action_type=ActionType.BUY,
                    source_index=slot,
                    card_id=minion.card_id,
                    priority=100 - i,
                    reason=f"Buy {minion.name} (score={score:.1f})",
                )
            )
            remaining_gold -= buy_cost
            available_space -= 1

        return actions
