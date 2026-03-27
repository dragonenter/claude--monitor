"""HeroPowerStrategy — decide when to use the hero power."""

from __future__ import annotations

from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType
from hs_bg_ai.models.game_state import GameState


class HeroPowerStrategy:
    """Decide whether to use the hero power this turn.

    Simple heuristic: use hero power if available and affordable.
    Passive hero powers are always active (no action needed).
    """

    def plan(self, state: GameState) -> list[GameAction]:
        actions: list[GameAction] = []

        hero = state.hero
        if hero is None or hero.hero_power is None:
            return actions

        hp = hero.hero_power

        # Passive powers don't require activation.
        if hp.is_passive:
            return actions

        # Check availability and cost.
        if not hp.is_available:
            return actions
        if state.resources.gold < hp.cost:
            return actions

        # Use hero power — in most cases this is correct for basic play.
        # Advanced: could evaluate whether HP value exceeds buying a minion.
        actions.append(
            GameAction(
                action_type=ActionType.HERO_POWER,
                priority=70,
                reason=f"Use hero power ({hp.name}, cost={hp.cost})",
            )
        )

        return actions
