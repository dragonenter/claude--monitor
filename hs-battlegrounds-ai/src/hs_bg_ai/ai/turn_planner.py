"""TurnPlanner — coordinates all strategies for a single recruit turn."""

from __future__ import annotations

import logging

from hs_bg_ai.models.actions import ActionPlan, GameAction
from hs_bg_ai.models.enums import ActionType, Phase
from hs_bg_ai.models.game_state import GameState

from .evaluator import BoardEvaluator
from .strategies.buy import BuyStrategy
from .strategies.comp_plan import CompPlanStrategy
from .strategies.hero_power import HeroPowerStrategy
from .strategies.hero_select import HeroSelectStrategy
from .strategies.position import PositionStrategy
from .strategies.quest_select import QuestSelectStrategy
from .strategies.refresh import RefreshStrategy
from .strategies.sell import SellStrategy
from .strategies.triple import TripleStrategy
from .strategies.upgrade import UpgradeStrategy

logger = logging.getLogger(__name__)


class TurnPlanner:
    """Orchestrate all strategies for one recruit turn.

    Order of operations:
    1. Hero select / quest select (if applicable).
    2. Evaluate composition direction.
    3. Hero power (if cheap / free).
    4. Upgrade tavern (if curve turn).
    5. Buy strongest minion(s).
    6. Sell if needed for space/gold.
    7. Refresh + buy cycle (if gold remains and shop is weak).
    8. Position the board.
    9. End turn.
    """

    def __init__(self, evaluator: BoardEvaluator, max_refreshes: int = 3) -> None:
        self._evaluator = evaluator
        self._buy = BuyStrategy(evaluator)
        self._sell = SellStrategy(evaluator)
        self._refresh = RefreshStrategy(evaluator, max_refreshes)
        self._upgrade = UpgradeStrategy()
        self._position = PositionStrategy()
        self._hero_power = HeroPowerStrategy()
        self._comp_plan = CompPlanStrategy(evaluator)
        self._triple = TripleStrategy()
        self._hero_select = HeroSelectStrategy()
        self._quest_select = QuestSelectStrategy()

    def plan(self, state: GameState) -> ActionPlan:
        """Create a full turn action plan."""
        actions: list[GameAction] = []

        # Hero select phase.
        if state.turn.phase == Phase.HERO_SELECT and state.hero_choices:
            actions.extend(self._hero_select.plan(state))
            return ActionPlan(
                actions=actions,
                turn_number=state.turn.turn_number,
                confidence=0.8,
            )

        # Quest select.
        if state.quest_choices:
            actions.extend(self._quest_select.plan(state))
            return ActionPlan(
                actions=actions,
                turn_number=state.turn.turn_number,
                confidence=0.7,
            )

        # Triple discover.
        if state.discover_choices:
            actions.extend(self._triple.plan_discover(state))
            return ActionPlan(
                actions=actions,
                turn_number=state.turn.turn_number,
                confidence=0.6,
            )

        # Only plan actions during recruit phase.
        if state.turn.phase != Phase.RECRUIT:
            return ActionPlan(turn_number=state.turn.turn_number)

        # Evaluate comp direction.
        comp = self._comp_plan.evaluate(state)
        logger.info(
            "Turn %d: comp=%s (conf=%.2f), gold=%d, tier=%d, board=%d",
            state.turn.turn_number,
            comp.direction,
            comp.confidence,
            state.resources.gold,
            state.resources.tavern_tier,
            len(state.board),
        )

        # 1. Hero power (use early if available and cheap).
        hp_actions = self._hero_power.plan(state)
        actions.extend(hp_actions)

        # 2. Consider upgrade.
        upgrade_actions = self._upgrade.plan(state)

        # 3. Buy phase.
        buy_actions = self._buy.plan(state)

        # 4. Sell if board is full and we want to buy something better.
        if buy_actions and state.board_space() == 0:
            sell_actions = self._sell.plan(state, need_space=True)
            actions.extend(sell_actions)

        # If upgrading, do it before buying (to get higher tier shop on refresh).
        if upgrade_actions:
            actions.extend(upgrade_actions)

        actions.extend(buy_actions)

        # 5. Refresh + buy cycle.
        # Track gold locally to avoid stale state (GameState is immutable snapshot).
        remaining_gold = state.resources.gold
        # Deduct gold already spent on actions above.
        for a in actions:
            if a.action_type == ActionType.BUY:
                remaining_gold -= 3  # Standard buy cost.
            elif a.action_type == ActionType.UPGRADE:
                remaining_gold -= state.resources.upgrade_cost
            elif a.action_type == ActionType.HERO_POWER:
                remaining_gold -= 1  # Approximation; varies by hero.
        refreshes = 0
        while remaining_gold >= 2 and refreshes < self._refresh._max_refreshes:
            refresh_actions = self._refresh.plan(state, refreshes)
            if not refresh_actions:
                break
            actions.extend(refresh_actions)
            remaining_gold -= 1  # Refresh costs 1 gold.
            refreshes += 1
            # After refresh, plan more buys.
            new_buys = self._buy.plan(state)
            for buy_action in new_buys:
                if remaining_gold >= 3:
                    actions.append(buy_action)
                    remaining_gold -= 3

        # 6. Position the board.
        pos_actions = self._position.plan(state)
        actions.extend(pos_actions)

        # 7. End turn.
        actions.append(
            GameAction(
                action_type=ActionType.END_TURN,
                priority=0,
                reason="End turn",
            )
        )

        # Sort by priority (highest first), but keep END_TURN last.
        end_turn = [a for a in actions if a.action_type == ActionType.END_TURN]
        non_end = [a for a in actions if a.action_type != ActionType.END_TURN]
        non_end.sort(key=lambda a: a.priority, reverse=True)
        actions = non_end + end_turn

        confidence = min(0.9, 0.5 + comp.confidence * 0.3 + len(buy_actions) * 0.05)

        return ActionPlan(
            actions=actions,
            turn_number=state.turn.turn_number,
            confidence=confidence,
            estimated_time_seconds=len(actions) * 1.5,
        )
