"""UpgradeStrategy — decide when to upgrade the tavern."""

from __future__ import annotations

from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType
from hs_bg_ai.models.game_state import GameState

# Standard upgrade curve: (turn_number, target_tier).
# Upgrade on the listed turn so that the new tier is active next recruit phase.
_UPGRADE_CURVE: dict[int, int] = {
    3: 2,   # Turn 3 -> tier 2
    5: 3,   # Turn 5 -> tier 3 (can delay to 6)
    7: 4,   # Turn 7 -> tier 4 (can delay to 8)
    9: 5,   # Turn 9 -> tier 5
    11: 6,  # Turn 11 -> tier 6
}


class UpgradeStrategy:
    """Decide whether to upgrade the tavern this turn.

    Standard curve: tier up on turns 3(T2), 5-6(T3), 7-8(T4).
    """

    def plan(self, state: GameState) -> list[GameAction]:
        actions: list[GameAction] = []

        current_tier = state.resources.tavern_tier
        if current_tier >= 6:
            return actions  # Already max tier.

        upgrade_cost = state.resources.upgrade_cost
        gold = state.resources.gold
        turn = state.turn.turn_number

        if gold < upgrade_cost:
            return actions

        # Check if we should upgrade based on the curve.
        target_tier = self._target_tier_for_turn(turn, current_tier)
        if target_tier is None or target_tier <= current_tier:
            return actions

        # Only upgrade if we can still buy afterwards, or if it's a curve turn.
        gold_after_upgrade = gold - upgrade_cost
        is_curve_turn = turn in _UPGRADE_CURVE and _UPGRADE_CURVE[turn] == current_tier + 1

        if is_curve_turn:
            actions.append(
                GameAction(
                    action_type=ActionType.UPGRADE,
                    priority=110,  # Higher than any buy action (max 100) per PRD: upgrade > buy.
                    reason=f"Curve upgrade: T{current_tier}->T{current_tier + 1} on turn {turn}",
                )
            )
        elif gold_after_upgrade >= 3:
            # Off-curve but can still buy after upgrading.
            actions.append(
                GameAction(
                    action_type=ActionType.UPGRADE,
                    priority=60,
                    reason=f"Upgrade T{current_tier}->T{current_tier + 1} (${gold_after_upgrade} left)",
                )
            )

        return actions

    def _target_tier_for_turn(self, turn: int, current_tier: int) -> int | None:
        """Determine target tier for the given turn."""
        # Find the highest tier we should be at by this turn.
        target = current_tier
        for t, tier in sorted(_UPGRADE_CURVE.items()):
            if turn >= t:
                target = max(target, tier)
        return target if target > current_tier else None
