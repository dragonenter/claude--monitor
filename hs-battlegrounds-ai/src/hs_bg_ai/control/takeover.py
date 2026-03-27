"""TakeoverManager: switch between bot-controlled and manual modes."""

from __future__ import annotations


class TakeoverManager:
    """Tracks whether the user has taken manual control of the game.

    When manual mode is enabled the bot should refrain from issuing any
    mouse or keyboard actions.
    """

    def __init__(self) -> None:
        self._manual = False

    @property
    def is_manual(self) -> bool:
        """``True`` when the user is in control; ``False`` when the bot drives."""
        return self._manual

    def enable(self) -> None:
        """Switch to manual (human) mode."""
        self._manual = True

    def disable(self) -> None:
        """Switch back to bot-controlled mode."""
        self._manual = False

    def toggle(self) -> bool:
        """Flip the current mode and return the new state."""
        self._manual = not self._manual
        return self._manual
