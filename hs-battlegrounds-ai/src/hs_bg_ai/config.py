"""Configuration loading with pydantic models."""

from __future__ import annotations

from pathlib import Path
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

import yaml
from pydantic import BaseModel, Field


class MouseConfig(BaseModel):
    speed_factor: float = 1.0
    bezier_deviation: float = 15.0
    click_delay_min: float = 0.05
    click_delay_max: float = 0.15


class TimingConfig(BaseModel):
    action_delay_min: float = 0.2
    action_delay_max: float = 0.6
    think_delay_min: float = 0.3
    think_delay_max: float = 1.0


class TimeConfig(BaseModel):
    turn_duration: float = 75.0
    safety_margin: float = 5.0
    first_turn_duration: float = 45.0


class HotkeyConfig(BaseModel):
    start_stop: str = "f9"
    pause_resume: str = "f10"
    manual_takeover: str = "f11"
    emergency_stop: str = "f12"


class AIConfig(BaseModel):
    aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    upgrade_bias: float = Field(default=0.5, ge=0.0, le=1.0)
    refresh_limit: int = Field(default=3, ge=0)


class LogConfig(BaseModel):
    log_path: str = ""
    log_level: str = "INFO"
    log_file: str = "hs_bg_ai.log"


class AppConfig(BaseModel):
    mouse: MouseConfig = Field(default_factory=MouseConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    time: TimeConfig = Field(default_factory=TimeConfig)
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    game_window_title: str = "炉石传说"

    @classmethod
    def from_yaml(cls, path: str | Path) -> Self:
        """Load config from a YAML file."""
        path = Path(path)
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls.model_validate(raw)


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load configuration from file, falling back to defaults.

    Search order:
    1. Explicit path argument
    2. ./config.yaml
    3. Pure defaults
    """
    if path is not None:
        return AppConfig.from_yaml(path)

    default_path = Path("config.yaml")
    if default_path.exists():
        return AppConfig.from_yaml(default_path)

    return AppConfig()
