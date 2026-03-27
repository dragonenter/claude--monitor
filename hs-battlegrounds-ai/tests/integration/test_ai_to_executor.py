"""Integration tests: AI plan -> executor interface (dry-run)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from tests.conftest import GameStateBuilder

from hs_bg_ai.ai.engine import AIEngine
from hs_bg_ai.core.events import EventBus, EventType
from hs_bg_ai.core.orchestrator import Orchestrator
from hs_bg_ai.models.actions import ActionResult, GameAction
from hs_bg_ai.models.cards import ShopMinion
from hs_bg_ai.models.enums import ActionType, Phase, TavernTier


class MockExecutor:
    """A dry-run executor that records actions without performing them."""

    def __init__(self) -> None:
        self.executed: list[GameAction] = []

    async def execute(self, action: GameAction) -> ActionResult:
        self.executed.append(action)
        return ActionResult(action=action, success=True, duration_ms=50)


class TestDryRunExecution:
    """Test that AI plans can be executed through the mock executor."""

    def test_ai_produces_valid_plan(self):
        state = (
            GameStateBuilder()
            .with_gold(6)
            .with_tavern_tier(1)
            .with_turn(2)
            .with_phase(Phase.RECRUIT)
            .with_board_minions(2)
            .with_shop([
                ShopMinion(
                    card_id="BG_Test_001", name="Test Minion",
                    attack=2, health=2, tavern_tier=TavernTier.TIER_1,
                    slot_index=0,
                ),
            ])
            .build()
        )

        engine = AIEngine()
        plan = engine.decide(state)

        # Plan should have at least an end_turn action.
        assert len(plan.actions) >= 1
        assert plan.actions[-1].action_type == ActionType.END_TURN
        assert plan.turn_number == 2

    async def test_orchestrator_executes_plan(self):
        """Test full orchestrator -> AI -> executor flow."""
        bus = EventBus()
        executor = MockExecutor()
        engine = AIEngine()

        orchestrator = Orchestrator(
            event_bus=bus,
            ai_engine=engine,
            executor=executor,
        )
        # Must set running=True so _run_turn doesn't skip actions.
        orchestrator._running = True

        state = (
            GameStateBuilder()
            .with_gold(3)
            .with_tavern_tier(1)
            .with_turn(1)
            .with_phase(Phase.RECRUIT)
            .with_shop([
                ShopMinion(
                    card_id="BG_Test_001", name="Test Minion",
                    attack=2, health=2, tavern_tier=TavernTier.TIER_1,
                    slot_index=0,
                ),
            ])
            .build()
        )

        # Directly invoke turn execution.
        await orchestrator._run_turn(state)

        # Executor should have received actions.
        assert len(executor.executed) >= 1

    async def test_action_plan_all_valid_types(self):
        """Verify all actions in a plan have valid ActionType."""
        state = (
            GameStateBuilder()
            .with_gold(10)
            .with_tavern_tier(2, upgrade_cost=4)
            .with_turn(5)
            .with_phase(Phase.RECRUIT)
            .with_board_minions(4)
            .with_shop([
                ShopMinion(
                    card_id="BG_Test_001", name="Strong",
                    attack=4, health=4, tavern_tier=TavernTier.TIER_2,
                    slot_index=0,
                ),
                ShopMinion(
                    card_id="BG_Test_002", name="Weak",
                    attack=1, health=1, tavern_tier=TavernTier.TIER_1,
                    slot_index=1,
                ),
            ])
            .build()
        )

        engine = AIEngine()
        plan = engine.decide(state)

        valid_types = set(ActionType)
        for action in plan.actions:
            assert action.action_type in valid_types, (
                f"Invalid action type: {action.action_type}"
            )

    async def test_event_bus_receives_turn_events(self):
        """Test that turn start/end events are published."""
        bus = EventBus()
        executor = MockExecutor()
        engine = AIEngine()
        received_events: list[EventType] = []

        async def track_event(data):
            pass

        bus.subscribe(EventType.TURN_START, track_event)
        bus.subscribe(EventType.TURN_END, track_event)

        # Track what events are published.
        original_publish = bus.publish
        published: list[EventType] = []

        async def tracked_publish(event_type, data=None):
            published.append(event_type)
            await original_publish(event_type, data)

        bus.publish = tracked_publish

        orchestrator = Orchestrator(
            event_bus=bus,
            ai_engine=engine,
            executor=executor,
        )
        orchestrator._running = True

        state = (
            GameStateBuilder()
            .with_gold(3)
            .with_turn(1)
            .with_phase(Phase.RECRUIT)
            .build()
        )

        await orchestrator._run_turn(state)

        assert EventType.TURN_START in published
        assert EventType.TURN_END in published


class TestEdgeCases:
    """Test edge cases in the AI pipeline."""

    def test_empty_state_produces_plan(self):
        """AI should handle a minimal/empty state gracefully."""
        state = GameStateBuilder().with_gold(0).with_phase(Phase.RECRUIT).build()
        engine = AIEngine()
        plan = engine.decide(state)
        # Should at least have END_TURN.
        assert len(plan.actions) >= 1

    def test_hero_select_plan(self):
        """AI should produce a hero selection plan."""
        from hs_bg_ai.models.heroes import Hero

        state = GameStateBuilder().with_phase(Phase.HERO_SELECT).build()
        state.hero_choices = [
            Hero(hero_id="H1", name="Hero1", health=40),
            Hero(hero_id="H2", name="Hero2", health=40, armor=5),
        ]

        engine = AIEngine()
        plan = engine.decide(state)

        assert len(plan.actions) == 1
        assert plan.actions[0].action_type == ActionType.SELECT_HERO

    def test_full_board_no_crash(self):
        """AI should handle a full board (7 minions) without crashing."""
        state = (
            GameStateBuilder()
            .with_gold(10)
            .with_turn(8)
            .with_tavern_tier(3)
            .with_phase(Phase.RECRUIT)
            .with_board_minions(7)
            .with_shop([
                ShopMinion(
                    card_id="BG_Test_001", name="Test",
                    attack=5, health=5, tavern_tier=TavernTier.TIER_3,
                    slot_index=0,
                ),
            ])
            .build()
        )

        engine = AIEngine()
        plan = engine.decide(state)
        assert plan is not None
