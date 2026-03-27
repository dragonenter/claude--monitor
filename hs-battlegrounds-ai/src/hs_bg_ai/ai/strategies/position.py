"""PositionStrategy — optimal minion positioning on the board."""

from __future__ import annotations

from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType, Keyword
from hs_bg_ai.models.game_state import GameState


class PositionStrategy:
    """Determine optimal board positioning.

    General rules:
    - Taunts on the left (positions 0-2) to soak hits.
    - Deathrattles that summon tokens on the right.
    - Cleave attackers on the far left (position 0).
    - Windfury on positions where they attack early.
    """

    def plan(self, state: GameState) -> list[GameAction]:
        """Return MOVE actions to reorder the board optimally."""
        if len(state.board) <= 1:
            return []

        # Build desired order.
        board = list(state.board)

        # Partition minions by role.
        taunts = [m for m in board if Keyword.TAUNT in m.keywords]
        deathrattles = [m for m in board if Keyword.DEATHRATTLE in m.keywords and Keyword.TAUNT not in m.keywords]
        others = [m for m in board if m not in taunts and m not in deathrattles]

        # Sort within groups: higher attack first for taunts, higher health first for deathrattles.
        taunts.sort(key=lambda m: m.attack + m.health, reverse=True)
        deathrattles.sort(key=lambda m: m.health, reverse=True)
        others.sort(key=lambda m: m.attack, reverse=True)

        # Desired order: taunts left, others middle, deathrattles right.
        desired = taunts + others + deathrattles

        # Generate move actions where positions differ.
        actions: list[GameAction] = []
        for target_pos, minion in enumerate(desired):
            current_pos = minion.position
            if current_pos != target_pos:
                actions.append(
                    GameAction(
                        action_type=ActionType.MOVE,
                        source_index=current_pos,
                        target_index=target_pos,
                        card_id=minion.card_id,
                        priority=20,
                        reason=f"Move {minion.name} from pos {current_pos} to {target_pos}",
                    )
                )

        return actions
