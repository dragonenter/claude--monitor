"""Hero and hero-power data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HeroPower:
    """A hero power."""

    power_id: str
    name: str
    cost: int
    is_passive: bool = False
    is_available: bool = True


@dataclass
class Hero:
    """A player's hero."""

    hero_id: str
    name: str
    health: int
    armor: int = 0
    hero_power: HeroPower | None = None
    is_dead: bool = False
