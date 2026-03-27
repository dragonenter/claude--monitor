"""LogDispatcher — routes log lines to registered parsers, collects LogEvents."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from hs_bg_ai.core.events import EventBus, EventType
from hs_bg_ai.log_parsers.base import BaseLogParser, LogEvent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LogDispatcher:
    """Register parsers and dispatch each incoming line to the first matching parser.

    Publishes resulting ``LogEvent`` objects to the ``EventBus``.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._parsers: list[BaseLogParser] = []

    # ── Public API ────────────────────────────────────────────────

    def register_parser(self, parser: BaseLogParser) -> None:
        """Add a parser to the dispatch chain."""
        self._parsers.append(parser)
        logger.debug("Registered parser: %s", parser.PARSER_NAME)

    def register_parsers(self, parsers: list[BaseLogParser]) -> None:
        for p in parsers:
            self.register_parser(p)

    async def dispatch(self, line: str) -> LogEvent | None:
        """Find the first parser that matches *line*, parse, and publish.

        Returns the LogEvent if one was produced, else None.
        """
        for parser in self._parsers:
            if parser.can_parse(line):
                try:
                    event = parser.parse(line)
                except Exception:
                    logger.exception("Parser %s failed on line: %s", parser.PARSER_NAME, line[:120])
                    continue

                if event is not None:
                    event.raw_line = line
                    await self._event_bus.publish(EventType.LOG_LINE, event)
                    return event
                return None  # Parser matched but produced nothing meaningful.
        return None

    @property
    def parser_count(self) -> int:
        return len(self._parsers)
