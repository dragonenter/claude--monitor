"""Shared test fixtures for HS Battlegrounds AI."""

from __future__ import annotations

import pytest

from hs_bg_ai.core.events import EventBus
from hs_bg_ai.models.cards import Minion, ShopMinion
from hs_bg_ai.models.enums import Keyword, MinionType, Phase, TavernTier
from hs_bg_ai.models.game_state import GameState, ResourceState, TurnInfo
from hs_bg_ai.models.heroes import Hero, HeroPower


# ── Helper: GameStateBuilder (fluent builder pattern) ────────────────


class GameStateBuilder:
    """Fluent builder for constructing GameState instances in tests.

    Usage:
        state = (GameStateBuilder()
            .with_hero("Deathwing")
            .with_gold(5)
            .with_tavern_tier(2)
            .with_board_minions(3)
            .with_phase(Phase.RECRUIT)
            .build())
    """

    def __init__(self) -> None:
        self._hero = Hero(
            hero_id="TB_BaconShop_HERO_05",
            name="Deathwing",
            health=40,
            armor=0,
            hero_power=HeroPower(
                power_id="TB_BaconShop_HP_05",
                name="ALL Will Burn!",
                cost=0,
                is_passive=True,
            ),
        )
        self._resources = ResourceState(gold=3, max_gold=3, tavern_tier=1, upgrade_cost=5)
        self._turn = TurnInfo(turn_number=1, phase=Phase.RECRUIT)
        self._board: list[Minion] = []
        self._hand: list[Minion] = []
        self._shop: list[ShopMinion] = []
        self._is_shop_frozen = False
        self._game_id = "test-game-001"
        self._is_game_active = True

    # ── Hero ─────────────────────────────────────────────────────

    def with_hero(self, name: str, health: int = 40, armor: int = 0) -> GameStateBuilder:
        self._hero = Hero(
            hero_id=f"TB_BaconShop_HERO_{name}",
            name=name,
            health=health,
            armor=armor,
        )
        return self

    def with_hero_power(
        self, name: str = "Test Power", cost: int = 1, is_passive: bool = False
    ) -> GameStateBuilder:
        self._hero.hero_power = HeroPower(
            power_id=f"TB_BaconShop_HP_{name}",
            name=name,
            cost=cost,
            is_passive=is_passive,
        )
        return self

    # ── Resources ────────────────────────────────────────────────

    def with_gold(self, gold: int, max_gold: int | None = None) -> GameStateBuilder:
        self._resources.gold = gold
        self._resources.max_gold = max_gold if max_gold is not None else gold
        return self

    def with_tavern_tier(self, tier: int, upgrade_cost: int = 5) -> GameStateBuilder:
        self._resources.tavern_tier = tier
        self._resources.upgrade_cost = upgrade_cost
        return self

    # ── Turn ─────────────────────────────────────────────────────

    def with_turn(self, turn_number: int) -> GameStateBuilder:
        self._turn.turn_number = turn_number
        return self

    def with_phase(self, phase: Phase) -> GameStateBuilder:
        self._turn.phase = phase
        return self

    # ── Board / Hand / Shop ──────────────────────────────────────

    def _make_minion(self, index: int, tier: int = 1) -> Minion:
        """Create a generic test minion."""
        return Minion(
            card_id=f"BG_Test_{index:03d}",
            name=f"Test Minion {index}",
            attack=index + 1,
            health=index + 1,
            tavern_tier=TavernTier(tier),
            minion_type=MinionType.NONE,
            position=index,
        )

    def with_board_minions(self, count: int, tier: int = 1) -> GameStateBuilder:
        """Add *count* generic minions to the board."""
        self._board = [self._make_minion(i, tier) for i in range(count)]
        return self

    def with_board(self, minions: list[Minion]) -> GameStateBuilder:
        self._board = minions
        return self

    def with_hand_minions(self, count: int, tier: int = 1) -> GameStateBuilder:
        self._hand = [self._make_minion(100 + i, tier) for i in range(count)]
        return self

    def with_hand(self, minions: list[Minion]) -> GameStateBuilder:
        self._hand = minions
        return self

    def with_shop(self, shop: list[ShopMinion]) -> GameStateBuilder:
        self._shop = shop
        return self

    def with_shop_frozen(self, frozen: bool = True) -> GameStateBuilder:
        self._is_shop_frozen = frozen
        return self

    # ── Game metadata ────────────────────────────────────────────

    def with_game_id(self, game_id: str) -> GameStateBuilder:
        self._game_id = game_id
        return self

    def inactive(self) -> GameStateBuilder:
        self._is_game_active = False
        return self

    # ── Build ────────────────────────────────────────────────────

    def build(self) -> GameState:
        return GameState(
            hero=self._hero,
            resources=self._resources,
            board=self._board,
            hand=self._hand,
            shop=self._shop,
            is_shop_frozen=self._is_shop_frozen,
            turn=self._turn,
            game_id=self._game_id,
            is_game_active=self._is_game_active,
        )


# ── Pytest fixtures ──────────────────────────────────────────────────


@pytest.fixture
def event_bus() -> EventBus:
    """Fresh EventBus instance -- no shared state between tests."""
    return EventBus()


@pytest.fixture
def sample_minion() -> Minion:
    """A basic tier-1 minion for testing."""
    return Minion(
        card_id="BG_Minion_001",
        name="Alleycat",
        attack=1,
        health=1,
        tavern_tier=TavernTier.TIER_1,
        minion_type=MinionType.BEAST,
        keywords=set(),
        position=0,
    )


@pytest.fixture
def sample_game_state() -> GameState:
    """A minimal but valid game state for testing."""
    return GameStateBuilder().build()


@pytest.fixture
def game_state_builder() -> GameStateBuilder:
    """Return a fresh GameStateBuilder for fluent test setup."""
    return GameStateBuilder()
