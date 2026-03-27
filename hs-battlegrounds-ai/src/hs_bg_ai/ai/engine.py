"""AIEngine — top-level AI entry point."""

from __future__ import annotations

import logging

from hs_bg_ai.config import AppConfig, AIConfig
from hs_bg_ai.models.actions import ActionPlan
from hs_bg_ai.models.game_state import GameState

from .evaluator import BoardEvaluator
from .turn_planner import TurnPlanner

logger = logging.getLogger(__name__)


class AIEngine:
    """Main AI decision engine.

    Call ``decide(state)`` each recruit phase to get an ``ActionPlan``.
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        ai_cfg = config.ai if config else AIConfig()
        self._evaluator = BoardEvaluator()
        self._planner = TurnPlanner(
            evaluator=self._evaluator,
            max_refreshes=ai_cfg.refresh_limit,
        )

    def decide(self, state: GameState) -> ActionPlan:
        """Produce an ActionPlan for the current game state."""
        logger.info(
            "AI deciding: turn=%d, phase=%s, gold=%d",
            state.turn.turn_number,
            state.turn.phase.name,
            state.resources.gold,
        )
        plan = self._planner.plan(state)
        logger.info(
            "AI plan: %d actions, confidence=%.2f",
            len(plan.actions),
            plan.confidence,
        )
        return plan

    @property
    def evaluator(self) -> BoardEvaluator:
        return self._evaluator

    @property
    def planner(self) -> TurnPlanner:
        return self._planner
