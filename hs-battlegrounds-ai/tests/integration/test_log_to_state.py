"""Integration tests: log parsing -> state update pipeline."""

from __future__ import annotations

import pytest

from hs_bg_ai.core.events import EventBus, EventType
from hs_bg_ai.log_engine.dispatcher import LogDispatcher
from hs_bg_ai.log_parsers.board_parser import BoardParser
from hs_bg_ai.log_parsers.hand_parser import HandParser
from hs_bg_ai.log_parsers.hero_parser import HeroParser
from hs_bg_ai.log_parsers.opponent_parser import OpponentParser
from hs_bg_ai.log_parsers.resource_parser import ResourceParser
from hs_bg_ai.log_parsers.shop_parser import ShopParser
from hs_bg_ai.log_parsers.turn_parser import TurnParser
from hs_bg_ai.models.enums import Phase
from hs_bg_ai.state.manager import StateManager


@pytest.fixture
def pipeline():
    """Set up a complete log -> state pipeline."""
    bus = EventBus()
    dispatcher = LogDispatcher(bus)
    dispatcher.register_parsers([
        TurnParser(),
        ShopParser(),
        HandParser(),
        BoardParser(),
        ResourceParser(),
        HeroParser(),
        OpponentParser(),
    ])
    state_mgr = StateManager(bus)
    return dispatcher, state_mgr


class TestTurnLifecycle:
    """Test that turn/phase log lines update the game state."""

    async def test_turn_number_updates(self, pipeline):
        dispatcher, state_mgr = pipeline
        line = (
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=GameEntity tag=TURN value=3"
        )
        await dispatcher.dispatch(line)
        state = state_mgr.get_state()
        assert state.turn.turn_number == 3

    async def test_recruit_phase_detected(self, pipeline):
        dispatcher, state_mgr = pipeline
        line = (
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=GameEntity tag=STEP value=MAIN_ACTION"
        )
        await dispatcher.dispatch(line)
        state = state_mgr.get_state()
        assert state.turn.phase == Phase.RECRUIT
        assert state.is_game_active is True

    async def test_game_over_phase(self, pipeline):
        dispatcher, state_mgr = pipeline
        # First start a game.
        await dispatcher.dispatch(
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=GameEntity tag=STEP value=MAIN_ACTION"
        )
        assert state_mgr.get_state().is_game_active is True

        # Then end it.
        await dispatcher.dispatch(
            "D 12:35:00.000 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=GameEntity tag=STEP value=FINAL_WRAPUP"
        )
        state = state_mgr.get_state()
        assert state.turn.phase == Phase.GAME_OVER
        assert state.is_game_active is False


class TestResourceTracking:
    """Test gold and tier tracking through logs."""

    async def test_gold_update(self, pipeline):
        dispatcher, state_mgr = pipeline
        line = (
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=PlayerName tag=RESOURCES value=7"
        )
        await dispatcher.dispatch(line)
        state = state_mgr.get_state()
        assert state.resources.max_gold == 7
        assert state.resources.gold == 7

    async def test_gold_spent(self, pipeline):
        dispatcher, state_mgr = pipeline
        # Set max gold first.
        await dispatcher.dispatch(
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=PlayerName tag=RESOURCES value=7"
        )
        # Spend some gold.
        await dispatcher.dispatch(
            "D 12:34:57.000 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=PlayerName tag=RESOURCES_USED value=3"
        )
        state = state_mgr.get_state()
        assert state.resources.gold == 4  # 7 - 3

    async def test_tavern_tier_change(self, pipeline):
        dispatcher, state_mgr = pipeline
        line = (
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=Player tag=PLAYER_TECH_LEVEL value=3"
        )
        await dispatcher.dispatch(line)
        state = state_mgr.get_state()
        assert state.resources.tavern_tier == 3


class TestHeroTracking:
    """Test hero-related log parsing into state."""

    async def test_hero_choice_populates(self, pipeline):
        dispatcher, state_mgr = pipeline
        line = (
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=[cardId=TB_BaconShop_HERO_01 ...] "
            "tag=BACON_HERO_CAN_BE_DRAFTED value=1"
        )
        await dispatcher.dispatch(line)
        state = state_mgr.get_state()
        assert len(state.hero_choices) == 1
        assert state.hero_choices[0].hero_id == "TB_BaconShop_HERO_01"
        assert state.turn.phase == Phase.HERO_SELECT

    async def test_hero_discovered(self, pipeline):
        dispatcher, state_mgr = pipeline
        line = (
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "FULL_ENTITY - Updating [cardId=TB_BaconShop_HERO_05 ...] "
            "CardID=TB_BaconShop_HERO_05"
        )
        await dispatcher.dispatch(line)
        state = state_mgr.get_state()
        assert state.hero is not None
        assert state.hero.hero_id == "TB_BaconShop_HERO_05"


class TestShopAndBoard:
    """Test shop offer and board placement flow."""

    async def test_shop_frozen(self, pipeline):
        dispatcher, state_mgr = pipeline
        line = (
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=Bob tag=BACON_FROZEN value=1"
        )
        await dispatcher.dispatch(line)
        state = state_mgr.get_state()
        assert state.is_shop_frozen is True

    async def test_shop_unfrozen(self, pipeline):
        dispatcher, state_mgr = pipeline
        await dispatcher.dispatch(
            "D 12:34:56.789 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=Bob tag=BACON_FROZEN value=1"
        )
        await dispatcher.dispatch(
            "D 12:34:57.000 GameState.DebugPrintPower() - "
            "TAG_CHANGE Entity=Bob tag=BACON_FROZEN value=0"
        )
        state = state_mgr.get_state()
        assert state.is_shop_frozen is False
