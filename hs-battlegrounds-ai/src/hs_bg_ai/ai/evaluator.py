"""BoardEvaluator — score minions, board strength, and composition direction."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from hs_bg_ai.models.cards import Minion, ShopMinion
from hs_bg_ai.models.enums import Keyword, MinionType, TavernTier
from hs_bg_ai.models.game_state import GameState

logger = logging.getLogger(__name__)

# Recognised composition archetypes and their primary tribes.
COMP_ARCHETYPES: dict[str, set[MinionType]] = {
    "beasts": {MinionType.BEAST},
    "mechs": {MinionType.MECH},
    "dragons": {MinionType.DRAGON},
    "murlocs": {MinionType.MURLOC},
    "elementals": {MinionType.ELEMENTAL},
    "undead": {MinionType.UNDEAD},
    "nagas": {MinionType.NAGA},
    "quilboar": {MinionType.QUILBOAR},
    "pirates": {MinionType.PIRATE},
    "demons": {MinionType.DEMON},
    "menagerie": {MinionType.ALL},
}


@dataclass
class MinionScore:
    """Score breakdown for a single minion."""

    card_id: str
    name: str
    stat_score: float = 0.0
    keyword_score: float = 0.0
    synergy_score: float = 0.0
    tier_score: float = 0.0
    total: float = 0.0


@dataclass
class BoardAssessment:
    """Overall board evaluation result."""

    total_stats: int = 0
    board_strength: float = 0.0
    comp_direction: str = "none"
    comp_scores: dict[str, float] = field(default_factory=dict)
    minion_scores: list[MinionScore] = field(default_factory=list)
    weakest_index: int = -1


class BoardEvaluator:
    """Evaluate board strength, individual minions, and detect composition direction."""

    # ── Keyword value weights ─────────────────────────────────────

    _KEYWORD_WEIGHTS: dict[Keyword, float] = {
        Keyword.TAUNT: 1.5,
        Keyword.DIVINE_SHIELD: 3.0,
        Keyword.POISONOUS: 4.0,
        Keyword.WINDFURY: 2.0,
        Keyword.REBORN: 2.5,
        Keyword.DEATHRATTLE: 1.5,
    }

    def evaluate_board(self, state: GameState) -> BoardAssessment:
        """Produce a full board assessment."""
        assessment = BoardAssessment()

        if not state.board:
            return assessment

        # Score each minion.
        for i, minion in enumerate(state.board):
            score = self.score_minion(minion, state)
            assessment.minion_scores.append(score)

        # Total stats.
        assessment.total_stats = sum(m.attack + m.health for m in state.board)

        # Board strength = sum of minion scores.
        assessment.board_strength = sum(s.total for s in assessment.minion_scores)

        # Detect composition direction.
        assessment.comp_scores = self._score_compositions(state.board)
        if assessment.comp_scores:
            assessment.comp_direction = max(assessment.comp_scores, key=assessment.comp_scores.get)

        # Weakest minion index.
        if assessment.minion_scores:
            assessment.weakest_index = min(
                range(len(assessment.minion_scores)),
                key=lambda i: assessment.minion_scores[i].total,
            )

        return assessment

    def score_minion(self, minion: Minion, state: GameState) -> MinionScore:
        """Score a single minion considering stats, keywords, synergy, tier."""
        score = MinionScore(card_id=minion.card_id, name=minion.name)

        # Stat score: attack + health, weighted.
        score.stat_score = minion.attack * 1.0 + minion.health * 1.2

        # Keyword value.
        for kw in minion.keywords:
            score.keyword_score += self._KEYWORD_WEIGHTS.get(kw, 0.0)

        # Tier score: higher tier minions are generally better.
        score.tier_score = (minion.tavern_tier.value - 1) * 0.5

        # Synergy: bonus if minion type matches board majority.
        score.synergy_score = self._synergy_bonus(minion, state.board)

        # Golden bonus.
        golden_bonus = 3.0 if minion.is_golden else 0.0

        score.total = (
            score.stat_score
            + score.keyword_score
            + score.tier_score
            + score.synergy_score
            + golden_bonus
        )
        return score

    def score_shop_minion(self, minion: ShopMinion, state: GameState) -> float:
        """Quick score for a shop minion (for buy decisions)."""
        stat_score = minion.attack * 1.0 + minion.health * 1.2
        tier_score = (minion.tavern_tier.value - 1) * 0.5
        triple_bonus = 0.0

        # Triple candidate bonus.
        # Must be large enough to outweigh even high-stat minions (PRD: 差1三连时购买率≥90%).
        # A T1 6/6 minion scores 6+7.2=13.2; we need the triple target to beat that reliably.
        count = state.triple_progress.get_count(minion.card_id)
        if count >= 2:
            triple_bonus = 20.0  # Decisive priority: buying completes a triple.
        elif count == 1:
            triple_bonus = 2.0

        # Type synergy with current board.
        synergy = 0.0
        if state.board:
            board_types = [m.minion_type for m in state.board if m.minion_type != MinionType.NONE]
            if board_types and minion.minion_type in board_types:
                synergy = 2.0

        return stat_score + tier_score + triple_bonus + synergy

    # ── Internals ─────────────────────────────────────────────────

    def _score_compositions(self, board: list[Minion]) -> dict[str, float]:
        """Score how well the board matches each archetype."""
        scores: dict[str, float] = {}
        types_on_board = [m.minion_type for m in board if m.minion_type != MinionType.NONE]
        if not types_on_board:
            return scores
        for name, tribes in COMP_ARCHETYPES.items():
            if MinionType.ALL in tribes:
                # Menagerie: score based on unique types.
                unique = len(set(types_on_board))
                scores[name] = unique * 1.5
            else:
                count = sum(1 for t in types_on_board if t in tribes)
                scores[name] = count * 2.0
        return scores

    def _synergy_bonus(self, minion: Minion, board: list[Minion]) -> float:
        """Bonus if this minion's type matches the dominant board type."""
        if not board or minion.minion_type == MinionType.NONE:
            return 0.0
        types = [m.minion_type for m in board if m.minion_type != MinionType.NONE and m is not minion]
        if not types:
            return 0.0
        # Find most common type.
        from collections import Counter
        most_common = Counter(types).most_common(1)
        if most_common and minion.minion_type == most_common[0][0]:
            return 2.0
        if minion.minion_type == MinionType.ALL:
            return 1.0
        return 0.0
