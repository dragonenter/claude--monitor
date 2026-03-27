"""Central game state model — single source of truth."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .cards import Minion, ShopMinion
from .enums import Phase
from .heroes import Hero


@dataclass
class ResourceState:
    """Current economy resources."""

    gold: int = 0
    max_gold: int = 0
    tavern_tier: int = 1
    upgrade_cost: int = 5


@dataclass
class OpponentInfo:
    """Known information about an opponent."""

    player_id: str
    hero_name: str
    health: int = 40
    tavern_tier: int = 1
    last_board_known: list[Minion] = field(default_factory=list)
    is_dead: bool = False


@dataclass
class TurnInfo:
    """Metadata about the current turn."""

    turn_number: int = 0
    phase: Phase = Phase.UNKNOWN
    recruit_start_time: float = field(default_factory=time.time)


@dataclass
class TripleProgress:
    """Tracks how many copies of each card the player has seen / owns."""

    _counts: dict[str, int] = field(default_factory=dict)

    def add(self, card_id: str, amount: int = 1) -> None:
        self._counts[card_id] = self._counts.get(card_id, 0) + amount

    def remove(self, card_id: str, amount: int = 1) -> None:
        current = self._counts.get(card_id, 0)
        new_val = max(0, current - amount)
        if new_val == 0:
            self._counts.pop(card_id, None)
        else:
            self._counts[card_id] = new_val

    def get_count(self, card_id: str) -> int:
        return self._counts.get(card_id, 0)

    def get_candidates(self) -> list[str]:
        """Return card_ids that have count >= 2 (close to triple)."""
        return [cid for cid, count in self._counts.items() if count >= 2]


@dataclass
class GameState:
    """Complete snapshot of the current game."""

    # Player state
    hero: Hero | None = None
    resources: ResourceState = field(default_factory=ResourceState)

    # Board / hand / shop
    board: list[Minion] = field(default_factory=list)
    hand: list[Minion] = field(default_factory=list)
    shop: list[ShopMinion] = field(default_factory=list)
    is_shop_frozen: bool = False

    # Turn tracking
    turn: TurnInfo = field(default_factory=TurnInfo)

    # Opponents
    opponents: dict[str, OpponentInfo] = field(default_factory=dict)
    next_opponent_id: str | None = None

    # Game metadata
    game_id: str = ""
    is_game_active: bool = False

    # Selection choices (populated during specific phases)
    hero_choices: list[Hero] = field(default_factory=list)
    quest_choices: list[Any] = field(default_factory=list)
    discover_choices: list[Any] = field(default_factory=list)

    # Triple tracking (triple_candidates 通过 TripleProgress 管理, 供 F-11 面板使用)
    triple_progress: TripleProgress = field(default_factory=TripleProgress)

    @property
    def triple_candidates(self) -> dict[str, int]:
        """Expose raw triple counts as dict for F-11 triple tracking."""
        return dict(self.triple_progress._counts)

    # ── Convenience helpers ──────────────────────────────────────────

    def board_count(self) -> int:
        return len(self.board)

    def hand_count(self) -> int:
        return len(self.hand)

    def available_gold(self) -> int:
        return self.resources.gold

    def board_space(self) -> int:
        """Number of open board slots (max 7)."""
        return 7 - len(self.board)
