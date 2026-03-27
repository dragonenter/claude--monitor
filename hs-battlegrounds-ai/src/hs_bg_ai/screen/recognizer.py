"""ScreenRecognizer: Protocol-based interface and stub implementation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ScreenRecognizer(Protocol):
    """Protocol that all screen recognizers must satisfy.

    Implementations should analyse a raw screenshot (as produced by mss or
    any compatible library) and return a dict of extracted game state data.
    """

    def recognize(self, screenshot: Any) -> dict[str, Any]:
        """Analyse *screenshot* and return extracted game state fields.

        Parameters
        ----------
        screenshot:
            A raw screenshot object (e.g. mss ScreenShot, PIL Image, numpy
            array, or ``None``).

        Returns
        -------
        dict
            Arbitrary key/value pairs representing recognised game elements.
            An empty dict means nothing was recognised.
        """
        ...  # pragma: no cover


class StubScreenRecognizer:
    """Stub implementation of ScreenRecognizer that always returns an empty dict.

    Useful for testing and as a placeholder until a real CV model is integrated.
    """

    def recognize(self, screenshot: Any) -> dict[str, Any]:  # noqa: ARG002
        """Return an empty dict (nothing recognised)."""
        return {}
