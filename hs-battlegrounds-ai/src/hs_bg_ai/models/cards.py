"""Card / minion data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import Keyword, MinionType, TavernTier


@dataclass
class Minion:
    """A minion on the player's board or in hand."""

    card_id: str
    name: str
    attack: int
    health: int
    tavern_tier: TavernTier
    minion_type: MinionType = MinionType.NONE
    is_golden: bool = False
    keywords: set[Keyword] = field(default_factory=set)
    enchantments: list[str] = field(default_factory=list)
    position: int = 0


@dataclass
class ShopMinion:
    """A minion available for purchase in Bob's Tavern."""

    card_id: str
    name: str
    attack: int
    health: int
    tavern_tier: TavernTier
    minion_type: MinionType = MinionType.NONE
    is_golden: bool = False
    slot_index: int = 0
    cost: int = 3
