"""Async event bus (pub-sub) for inter-module communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from enum import Enum, auto
from typing import Any, Callable, Coroutine


class EventType(Enum):
    """All event types flowing through the system."""

    LOG_LINE = auto()
    STATE_UPDATED = auto()
    TURN_START = auto()
    TURN_END = auto()
    GAME_START = auto()
    GAME_OVER = auto()
    PHASE_CHANGE = auto()
    ACTION_COMPLETED = auto()
    ACTION_FAILED = auto()
    ERROR = auto()
    PAUSE_REQUESTED = auto()
    RESUME_REQUESTED = auto()


# Callback signature: async def handler(data: Any) -> None
EventCallback = Callable[[Any], Coroutine[Any, Any, None]]


class EventBus:
    """Lightweight async pub-sub event bus.

    Create a fresh instance per test / per application run
    (intentionally *not* a singleton).
    """

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventCallback]] = defaultdict(list)

    def subscribe(self, event_type: EventType, callback: EventCallback) -> None:
        """Register *callback* to be invoked when *event_type* is published."""
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: EventCallback) -> None:
        """Remove a previously registered callback."""
        try:
            self._subscribers[event_type].remove(callback)
        except ValueError:
            pass

    async def publish(self, event_type: EventType, data: Any = None) -> None:
        """Publish an event, invoking all subscribers concurrently."""
        callbacks = list(self._subscribers.get(event_type, []))
        if not callbacks:
            return
        await asyncio.gather(*(cb(data) for cb in callbacks), return_exceptions=True)

    def clear(self) -> None:
        """Remove all subscriptions — useful for test isolation."""
        self._subscribers.clear()
