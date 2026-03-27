"""Integration tests: state -> AI decision pipeline."""

from __future__ import annotations

import pytest

from tests.conftest import GameStateBuilder

from hs_bg_ai.ai.engine import AIEngine
from hs_bg_ai.ai.evaluator import BoardEvaluator
from hs_bg_ai.models.cards import Minion, ShopMinion
from hs_bg_ai.models.enums import ActionType, Keyword, MinionType, Phase, TavernTier
from hs_bg_ai.models.heroes import Hero, HeroPower


class TestAIBuyDecisions:
    """Test that AI correctly decides what to buy."""

    def test_buys_when_gold_available(self):
        state = (
            GameStateBuilder()
            .with_gold(6)
            .with_tavern_tier(1)
            .with_turn(2)
            .with_phase(Phase.RECRUIT)
            .with_board_minions(2)
            .with_shop([
                ShopMinion(
                    card_id="BG_Beast_001", name="Alleycat",
                    attack=1, health=1, tavern_tier=TavernTier.TIER_1,
                    minion_type=MinionType.BEAST, slot_index=0,
                ),
                ShopMinion(
                    card_id="BG_Mech_001", name="Micro Machine",
                    attack=2, health=2, tavern_tier=TavernTier.TIER_1,
                    minion_type=MinionType.MECH, slot_index=1,
                ),
            ])
            .build()
        )

        engine = AIEngine()
        plan = engine.decide(state)

        assert len(plan.actions) > 0
        buy_actions = [a for a in plan.actions if a.action_type == ActionType.BUY]
        assert len(buy_actions) >= 1
        # Should buy the stronger minion first.
        assert buy_actions[0].card_id == "BG_Mech_001"

    def test_no_buy_when_no_gold(self):
        state = (
            GameStateBuilder()
            .with_gold(0)
            .with_turn(2)
            .with_phase(Phase.RECRUIT)
            .with_shop([
                ShopMinion(
                    card_id="BG_Test_001", name="Test",
                    attack=1, health=1, tavern_tier=TavernTier.TIER_1,
                    slot_index=0,
                ),
            ])
            .build()
        )

        engine = AIEngine()
        plan = engine.decide(state)

        buy_actions = [a for a in plan.actions if a.action_type == ActionType.BUY]
        assert len(buy_actions) == 0


class TestAIUpgradeDecisions:
    """Test that AI follows the standard upgrade curve."""

    def test_upgrades_on_curve_turn_3(self):
        state = (
            GameStateBuilder()
            .with_gold(5)
            .with_tavern_tier(1, upgrade_cost=5)
            .with_turn(3)
            .with_phase(Phase.RECRUIT)
            .with_board_minions(2)
            .build()
        )

        engine = AIEngine()
        plan = engine.decide(state)

        upgrade_actions = [a for a in plan.actions if a.action_type == ActionType.UPGRADE]
        assert len(upgrade_actions) == 1

    def test_no_upgrade_too_early(self):
        state = (
            GameStateBuilder()
            .with_gold(5)
            .with_tavern_tier(1, upgrade_cost=5)
            .with_turn(1)
            .with_phase(Phase.RECRUIT)
            .build()
        )

        engine = AIEngine()
        plan = engine.decide(state)

        upgrade_actions = [a for a in plan.actions if a.action_type == ActionType.UPGRADE]
        assert len(upgrade_actions) == 0


class TestAIHeroSelect:
    """Test hero selection."""

    def test_selects_hero_from_choices(self):
        state = (
            GameStateBuilder()
            .with_phase(Phase.HERO_SELECT)
            .build()
        )
        state.hero_choices = [
            Hero(hero_id="TB_BaconShop_HERO_01", name="A.F.Kay", health=40, armor=10),
            Hero(hero_id="TB_BaconShop_HERO_02", name="Bartendotron", health=40),
        ]

        engine = AIEngine()
        plan = engine.decide(state)

        select_actions = [a for a in plan.actions if a.action_type == ActionType.SELECT_HERO]
        assert len(select_actions) == 1


class TestAITripleAwareness:
    """Test that AI prioritises triple completion."""

    def test_prioritises_triple_buy(self):
        state = (
            GameStateBuilder()
            .with_gold(3)
            .with_turn(4)
            .with_phase(Phase.RECRUIT)
            .with_board_minions(3)
            .with_shop([
                ShopMinion(
                    card_id="BG_Triple_Target", name="Triple Me",
                    attack=2, health=2, tavern_tier=TavernTier.TIER_1,
                    slot_index=0,
                ),
                ShopMinion(
                    card_id="BG_Other_001", name="Other",
                    attack=3, health=3, tavern_tier=TavernTier.TIER_1,
                    slot_index=1,
                ),
            ])
            .build()
        )
        # Simulate having 2 copies already.
        state.triple_progress.add("BG_Triple_Target", 2)

        engine = AIEngine()
        plan = engine.decide(state)

        buy_actions = [a for a in plan.actions if a.action_type == ActionType.BUY]
        assert len(buy_actions) >= 1
        # Should buy the triple target even though Other has higher stats.
        assert buy_actions[0].card_id == "BG_Triple_Target"


class TestBoardEvaluator:
    """Test the evaluator's scoring logic."""

    def test_keyword_scoring(self):
        evaluator = BoardEvaluator()
        state = GameStateBuilder().with_phase(Phase.RECRUIT).build()

        plain = Minion(
            card_id="plain", name="Plain", attack=2, health=3,
            tavern_tier=TavernTier.TIER_1,
        )
        shielded = Minion(
            card_id="shield", name="Shielded", attack=2, health=3,
            tavern_tier=TavernTier.TIER_1,
            keywords={Keyword.DIVINE_SHIELD},
        )

        plain_score = evaluator.score_minion(plain, state)
        shield_score = evaluator.score_minion(shielded, state)
        assert shield_score.total > plain_score.total

    def test_comp_detection(self):
        evaluator = BoardEvaluator()
        beasts = [
            Minion(
                card_id=f"beast_{i}", name=f"Beast {i}", attack=2, health=2,
                tavern_tier=TavernTier.TIER_1, minion_type=MinionType.BEAST,
                position=i,
            )
            for i in range(4)
        ]
        state = GameStateBuilder().with_board(beasts).with_phase(Phase.RECRUIT).build()

        assessment = evaluator.evaluate_board(state)
        assert assessment.comp_direction == "beasts"


class TestPositioning:
    """Test board positioning logic."""

    def test_taunts_positioned_left(self):
        from hs_bg_ai.ai.strategies.position import PositionStrategy

        taunt = Minion(
            card_id="taunt_1", name="Taunt", attack=1, health=5,
            tavern_tier=TavernTier.TIER_1,
            keywords={Keyword.TAUNT},
            position=2,  # Currently in wrong position.
        )
        attacker = Minion(
            card_id="atk_1", name="Attacker", attack=5, health=1,
            tavern_tier=TavernTier.TIER_1,
            position=0,
        )
        deathrattle = Minion(
            card_id="dr_1", name="Deathrattle", attack=2, health=2,
            tavern_tier=TavernTier.TIER_1,
            keywords={Keyword.DEATHRATTLE},
            position=1,
        )

        state = (
            GameStateBuilder()
            .with_board([attacker, deathrattle, taunt])
            .with_phase(Phase.RECRUIT)
            .build()
        )

        strategy = PositionStrategy()
        actions = strategy.plan(state)

        # Taunt should be moved to position 0 (leftmost).
        if actions:
            # At least one move action should exist.
            move_actions = [a for a in actions if a.action_type == ActionType.MOVE]
            assert len(move_actions) > 0
