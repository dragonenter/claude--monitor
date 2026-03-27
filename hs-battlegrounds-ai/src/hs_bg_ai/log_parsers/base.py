"""Base class and data model for log parsers."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LogEvent:
    """A single parsed event extracted from a log line."""

    event_type: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    raw_line: str = ""


class BaseLogParser(ABC):
    """Abstract base for all Hearthstone log parsers.

    Subclasses must define:
    - PARSER_NAME: human-readable identifier
    - LINE_PATTERNS: compiled regexes this parser cares about
    - parse(): extract a LogEvent from a matching line
    """

    PARSER_NAME: str = ""
    LINE_PATTERNS: list[re.Pattern[str]] = []

    def can_parse(self, line: str) -> bool:
        """Return True if any of this parser's patterns match *line*."""
        return any(pat.search(line) for pat in self.LINE_PATTERNS)

    @abstractmethod
    def parse(self, line: str) -> LogEvent | None:
        """Attempt to parse *line* into a LogEvent.

        Returns None if the line is recognised but not meaningful.
        """
        ...
