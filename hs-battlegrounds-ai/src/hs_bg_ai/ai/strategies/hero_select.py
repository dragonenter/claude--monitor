"""HeroSelectStrategy — pick the best hero during selection phase."""

from __future__ import annotations

from hs_bg_ai.models.actions import GameAction
from hs_bg_ai.models.enums import ActionType
from hs_bg_ai.models.game_state import GameState
from hs_bg_ai.models.heroes import Hero

# Hero tier list (rough ranking for 6000-7000 rating).
# Higher score = stronger hero.
_HERO_RATINGS: dict[str, float] = {
    # S tier
    "TB_BaconShop_HERO_01": 9.0,   # A.F.Kay
    # A tier — add more as needed
}


class HeroSelectStrategy:
    """Pick the best hero from the selection.

    Uses a tier-list lookup with fallback to hero power analysis.
    """

    def plan(self, state: GameState) -> list[GameAction]:
        """Return a SELECT_HERO action for the best available hero."""
        if not state.hero_choices:
            return []

        best_idx = 0
        best_score = -1.0

        for i, hero in enumerate(state.hero_choices):
            score = self._rate_hero(hero)
            if score > best_score:
                best_score = score
                best_idx = i

        return [
            GameAction(
                action_type=ActionType.SELECT_HERO,
                source_index=best_idx,
                card_id=state.hero_choices[best_idx].hero_id,
                priority=100,
                reason=f"Select hero: {state.hero_choices[best_idx].name}",
            )
        ]

    def _rate_hero(self, hero: Hero) -> float:
        """Rate a hero. Uses tier list, falls back to heuristics."""
        if hero.hero_id in _HERO_RATINGS:
            return _HERO_RATINGS[hero.hero_id]

        # Fallback: rate by hero power characteristics.
        score = 5.0  # Default average.
        if hero.hero_power:
            if hero.hero_power.is_passive:
                score += 1.0  # Passive powers are generally solid.
            if hero.hero_power.cost == 0:
                score += 0.5  # Free hero powers are nice.
        if hero.armor > 0:
            score += hero.armor * 0.1

        return score
