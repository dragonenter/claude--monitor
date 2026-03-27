"""StateManager — applies LogEvents to GameState, publishes updates."""

from __future__ import annotations

import copy
import logging
from typing import Any

from hs_bg_ai.core.events import EventBus, EventType
from hs_bg_ai.log_parsers.base import LogEvent
from hs_bg_ai.models.cards import Minion, ShopMinion
from hs_bg_ai.models.enums import MinionType, Phase, TavernTier
from hs_bg_ai.models.game_state import GameState, OpponentInfo, ResourceState, TurnInfo
from hs_bg_ai.models.heroes import Hero

logger = logging.getLogger(__name__)

# Map parser phase strings to Phase enum.
_PHASE_MAP = {
    "recruit": Phase.RECRUIT,
    "combat_start": Phase.COMBAT,
    "combat_end": Phase.COMBAT_RESULT,
    "game_over": Phase.GAME_OVER,
}


class StateManager:
    """Central game state manager.

    Subscribes to ``LOG_LINE`` events, updates internal ``GameState``,
    and publishes ``STATE_UPDATED``, ``TURN_START``, ``PHASE_CHANGE``,
    ``GAME_START``, ``GAME_OVER`` events as appropriate.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._state = GameState()
        self._event_bus.subscribe(EventType.LOG_LINE, self._on_log_event)

    # ── Public API ────────────────────────────────────────────────

    def get_state(self) -> GameState:
        """Return a deep-copy snapshot of the current game state."""
        return copy.deepcopy(self._state)

    def reset(self) -> None:
        """Reset to a fresh game state."""
        self._state = GameState()

    @property
    def state_ref(self) -> GameState:
        """Direct reference (not a copy) — for internal / test use only."""
        return self._state

    # ── Event handler ─────────────────────────────────────────────

    async def _on_log_event(self, event: LogEvent) -> None:
        """Route a LogEvent to the appropriate updater."""
        handler = self._HANDLERS.get(event.event_type)
        if handler is not None:
            self._phase_changed = None
            handler(self, event)
            snapshot = self.get_state()
            await self._event_bus.publish(EventType.STATE_UPDATED, snapshot)
            if self._phase_changed is not None:
                old_phase, new_phase = self._phase_changed
                await self._event_bus.publish(
                    EventType.PHASE_CHANGE,
                    {"old_phase": old_phase, "new_phase": new_phase, "state": snapshot},
                )

    # ── Individual updaters ───────────────────────────────────────

    def _handle_turn_change(self, event: LogEvent) -> None:
        turn_num = event.data.get("turn_number", 0)
        old_turn = self._state.turn.turn_number
        self._state.turn.turn_number = turn_num
        if turn_num > old_turn:
            logger.info("Turn %d started.", turn_num)

    def _handle_phase_change(self, event: LogEvent) -> None:
        phase_str = event.data.get("phase", "")
        new_phase = _PHASE_MAP.get(phase_str)
        if new_phase is None:
            return
        old_phase = self._state.turn.phase
        self._state.turn.phase = new_phase
        if new_phase == Phase.RECRUIT and old_phase != Phase.RECRUIT:
            self._state.is_game_active = True
        elif new_phase == Phase.GAME_OVER:
            self._state.is_game_active = False
        self._phase_changed = (old_phase, new_phase)

    def _handle_gold_change(self, event: LogEvent) -> None:
        max_gold = event.data.get("max_gold", 0)
        self._state.resources.max_gold = max_gold
        # At turn start, available gold = max_gold.
        self._state.resources.gold = max_gold

    def _handle_gold_spent(self, event: LogEvent) -> None:
        used = event.data.get("gold_used", 0)
        self._state.resources.gold = self._state.resources.max_gold - used

    def _handle_temp_gold(self, event: LogEvent) -> None:
        temp = event.data.get("temp_gold", 0)
        self._state.resources.gold += temp

    def _handle_tavern_tier(self, event: LogEvent) -> None:
        self._state.resources.tavern_tier = event.data.get("tavern_tier", 1)

    def _handle_upgrade_cost(self, event: LogEvent) -> None:
        self._state.resources.upgrade_cost = event.data.get("upgrade_cost", 5)

    def _handle_shop_offer(self, event: LogEvent) -> None:
        card_id = event.data.get("card_id", "")
        entity_id = event.data.get("entity_id", 0)
        # Avoid duplicates.
        for m in self._state.shop:
            if m.card_id == card_id and m.slot_index == entity_id:
                return
        slot = len(self._state.shop)
        minion = ShopMinion(
            card_id=card_id,
            name=card_id,  # Real name resolved from card DB later.
            attack=0,
            health=0,
            tavern_tier=TavernTier(self._state.resources.tavern_tier),
            slot_index=slot,
        )
        self._state.shop.append(minion)

    def _handle_shop_refresh(self, event: LogEvent) -> None:
        self._state.shop.clear()

    def _handle_shop_frozen(self, event: LogEvent) -> None:
        self._state.is_shop_frozen = event.data.get("frozen", False)

    def _handle_minion_bought(self, event: LogEvent) -> None:
        card_id = event.data.get("card_id", "")
        entity_id = event.data.get("entity_id", 0)
        slot_index = event.data.get("slot_index", -1)
        # Remove only the specific minion from shop (by entity_id or slot_index, not card_id).
        removed = False
        if entity_id:
            new_shop = []
            for m in self._state.shop:
                if not removed and m.slot_index == entity_id:
                    removed = True
                    continue
                new_shop.append(m)
            self._state.shop = new_shop
        elif slot_index >= 0:
            new_shop = []
            for i, m in enumerate(self._state.shop):
                if not removed and i == slot_index:
                    removed = True
                    continue
                new_shop.append(m)
            self._state.shop = new_shop
        else:
            # Fallback: remove first matching card_id only.
            new_shop = []
            for m in self._state.shop:
                if not removed and m.card_id == card_id:
                    removed = True
                    continue
                new_shop.append(m)
            self._state.shop = new_shop
        # Track triple progress.
        self._state.triple_progress.add(card_id)

    def _handle_card_to_hand(self, event: LogEvent) -> None:
        card_id = event.data.get("card_id", "")
        entity_id = event.data.get("entity_id", 0)
        # Add to hand if not already present.
        for m in self._state.hand:
            if m.card_id == card_id:
                return
        minion = Minion(
            card_id=card_id,
            name=card_id,
            attack=0,
            health=0,
            tavern_tier=TavernTier(self._state.resources.tavern_tier),
            position=len(self._state.hand),
        )
        self._state.hand.append(minion)

    def _handle_minion_to_board(self, event: LogEvent) -> None:
        card_id = event.data.get("card_id", "")
        # Remove from hand if present.
        self._state.hand = [m for m in self._state.hand if m.card_id != card_id]
        # Add to board.
        if len(self._state.board) < 7:
            minion = Minion(
                card_id=card_id,
                name=card_id,
                attack=0,
                health=0,
                tavern_tier=TavernTier(self._state.resources.tavern_tier),
                position=len(self._state.board),
            )
            self._state.board.append(minion)

    def _handle_minion_left_board(self, event: LogEvent) -> None:
        card_id = event.data.get("card_id", "")
        new_zone = event.data.get("new_zone", "")
        self._state.board = [m for m in self._state.board if m.card_id != card_id]
        # If sold, remove from triple tracking.
        if new_zone in ("SETASIDE", "GRAVEYARD", "REMOVEDFROMGAME"):
            self._state.triple_progress.remove(card_id)

    def _handle_stat_change(self, event: LogEvent) -> None:
        card_id = event.data.get("card_id", "")
        stat = event.data.get("stat", "")
        value = event.data.get("value", 0)
        for minion in self._state.board + self._state.hand:
            if minion.card_id == card_id:
                if stat == "atk":
                    minion.attack = value
                elif stat == "health":
                    minion.health = value
                break

    def _handle_hero_discovered(self, event: LogEvent) -> None:
        hero_id = event.data.get("hero_id", "")
        hero = Hero(hero_id=hero_id, name=hero_id, health=40)
        if self._state.hero is None:
            self._state.hero = hero

    def _handle_hero_choice(self, event: LogEvent) -> None:
        hero_id = event.data.get("hero_id", "")
        hero = Hero(hero_id=hero_id, name=hero_id, health=40)
        self._state.hero_choices.append(hero)
        self._state.turn.phase = Phase.HERO_SELECT

    def _handle_hero_health(self, event: LogEvent) -> None:
        hero_id = event.data.get("hero_id", "")
        tag = event.data.get("tag", "")
        value = event.data.get("value", 0)
        if self._state.hero and self._state.hero.hero_id == hero_id:
            if tag == "health":
                self._state.hero.health = value
            elif tag == "armor":
                self._state.hero.armor = value
            elif tag == "damage":
                # Effective health = base_health - damage.
                pass  # We store health directly; damage tracked separately if needed.

    def _handle_hero_power_used(self, event: LogEvent) -> None:
        if self._state.hero and self._state.hero.hero_power:
            exhausted = event.data.get("exhausted", True)
            self._state.hero.hero_power.is_available = not exhausted

    def _handle_next_opponent(self, event: LogEvent) -> None:
        opp_id = str(event.data.get("opponent_id", ""))
        self._state.next_opponent_id = opp_id

    def _handle_player_placement(self, event: LogEvent) -> None:
        name = event.data.get("player_name", "")
        placement = event.data.get("placement", 0)
        if name in self._state.opponents:
            self._state.opponents[name].is_dead = True
        else:
            self._state.opponents[name] = OpponentInfo(
                player_id=name, hero_name=name, is_dead=True
            )

    # ── Handler dispatch table ────────────────────────────────────

    _HANDLERS: dict[str, Any] = {
        "turn_change": _handle_turn_change,
        "phase_change": _handle_phase_change,
        "next_phase": _handle_phase_change,
        "gold_change": _handle_gold_change,
        "gold_spent": _handle_gold_spent,
        "temp_gold": _handle_temp_gold,
        "tavern_tier_change": _handle_tavern_tier,
        "upgrade_cost_change": _handle_upgrade_cost,
        "shop_offer": _handle_shop_offer,
        "shop_refresh": _handle_shop_refresh,
        "shop_frozen": _handle_shop_frozen,
        "minion_bought": _handle_minion_bought,
        "card_to_hand": _handle_card_to_hand,
        "minion_to_board": _handle_minion_to_board,
        "minion_left_board": _handle_minion_left_board,
        "stat_change": _handle_stat_change,
        "hero_discovered": _handle_hero_discovered,
        "hero_choice": _handle_hero_choice,
        "hero_health_change": _handle_hero_health,
        "hero_power_used": _handle_hero_power_used,
        "next_opponent": _handle_next_opponent,
        "player_placement": _handle_player_placement,
    }
