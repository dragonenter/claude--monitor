"""Enumerations for game concepts."""

from enum import Enum, IntEnum, auto


class Phase(Enum):
    """Current game phase."""
    HERO_SELECT = auto()
    RECRUIT = auto()
    COMBAT = auto()
    COMBAT_RESULT = auto()
    GAME_OVER = auto()
    LOADING = auto()
    DISCONNECTED = auto()
    UNKNOWN = auto()


class MinionType(Enum):
    """Minion tribe types."""
    BEAST = auto()
    DEMON = auto()
    DRAGON = auto()
    ELEMENTAL = auto()
    MECH = auto()
    MURLOC = auto()
    NAGA = auto()
    PIRATE = auto()
    QUILBOAR = auto()
    UNDEAD = auto()
    ALL = auto()
    NONE = auto()


class TavernTier(IntEnum):
    """Tavern upgrade tiers (1-6)."""
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4
    TIER_5 = 5
    TIER_6 = 6


class ActionType(Enum):
    """Types of actions the bot can perform."""
    BUY = auto()
    SELL = auto()
    REFRESH = auto()
    UPGRADE = auto()
    PLAY = auto()
    MOVE = auto()
    HERO_POWER = auto()
    FREEZE = auto()
    END_TURN = auto()
    SELECT_HERO = auto()
    SELECT_QUEST = auto()
    TRIPLE_DISCOVER = auto()


class Keyword(Enum):
    """Minion keyword abilities."""
    TAUNT = auto()
    DIVINE_SHIELD = auto()
    POISONOUS = auto()
    WINDFURY = auto()
    REBORN = auto()
    DEATHRATTLE = auto()
    AVENGE = auto()
    START_OF_COMBAT = auto()
