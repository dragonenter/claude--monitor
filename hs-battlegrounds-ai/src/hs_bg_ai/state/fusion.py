"""DataFusion — merge log-derived state with screen-capture data.

Log data takes priority; screen data fills gaps (e.g. minion stats
that aren't emitted in the log, or visual-only information).
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any

from hs_bg_ai.models.cards import Minion, ShopMinion
from hs_bg_ai.models.game_state import GameState

logger = logging.getLogger(__name__)


@dataclass
class ScreenData:
    """Raw data extracted from a screen capture.

    Populated by the screen-reading module (not implemented here).
    """

    board_minions: list[dict[str, Any]] = field(default_factory=list)
    hand_minions: list[dict[str, Any]] = field(default_factory=list)
    shop_minions: list[dict[str, Any]] = field(default_factory=list)
    gold: int | None = None
    health: int | None = None
    tavern_tier: int | None = None
    turn_timer: float | None = None


class DataFusion:
    """Merge log state with screen data.

    Principle: log data is authoritative. Screen data is used only to
    fill in fields that the log doesn't provide or to correct obviously
    stale log data.
    """

    def fuse(self, log_state: GameState, screen: ScreenData) -> GameState:
        """Return a new GameState merging *log_state* with *screen*.

        Does NOT modify the input objects.
        """
        merged = copy.deepcopy(log_state)

        # Fill gold if log hasn't provided it yet.
        if screen.gold is not None and merged.resources.gold == 0:
            merged.resources.gold = screen.gold

        # Fill tavern tier from screen if log is behind.
        if screen.tavern_tier is not None and screen.tavern_tier > merged.resources.tavern_tier:
            merged.resources.tavern_tier = screen.tavern_tier

        # Fill hero health if log hasn't updated.
        if screen.health is not None and merged.hero is not None:
            if merged.hero.health <= 0:
                merged.hero.health = screen.health

        # Fill shop stats from screen data if log minions have 0/0 stats.
        self._fill_shop_stats(merged, screen)

        # Fill board stats from screen.
        self._fill_board_stats(merged, screen)

        return merged

    def _fill_shop_stats(self, state: GameState, screen: ScreenData) -> None:
        """Update shop minion stats from screen data if log data is missing."""
        for i, screen_minion in enumerate(screen.shop_minions):
            if i < len(state.shop):
                shop_m = state.shop[i]
                if shop_m.attack == 0 and "attack" in screen_minion:
                    shop_m.attack = screen_minion["attack"]
                if shop_m.health == 0 and "health" in screen_minion:
                    shop_m.health = screen_minion["health"]

    def _fill_board_stats(self, state: GameState, screen: ScreenData) -> None:
        """Update board minion stats from screen data if log data is missing."""
        for i, screen_minion in enumerate(screen.board_minions):
            if i < len(state.board):
                board_m = state.board[i]
                if board_m.attack == 0 and "attack" in screen_minion:
                    board_m.attack = screen_minion["attack"]
                if board_m.health == 0 and "health" in screen_minion:
                    board_m.health = screen_minion["health"]
