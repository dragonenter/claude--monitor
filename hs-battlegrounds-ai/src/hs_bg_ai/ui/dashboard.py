"""Dashboard: terminal UI using rich to display bot status and game state."""

from __future__ import annotations

from typing import Any

try:
    from rich.columns import Columns
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False


class Dashboard:
    """Terminal UI dashboard for the Hearthstone Battlegrounds bot.

    Uses *rich* for coloured, structured output.  Falls back to plain
    ``print`` when *rich* is not installed.

    Parameters
    ----------
    refresh_rate:
        Display refresh rate in seconds.
    """

    def __init__(self, refresh_rate: float = 1.0) -> None:
        self._refresh_rate = refresh_rate
        self._visible = False
        self._console: Any = Console() if _RICH_AVAILABLE else None
        self._live: Any = None

        # State snapshots for rendering
        self._bot_status: str = "STOPPED"
        self._turn_number: int = 0
        self._gold: int = 0
        self._tavern_tier: int = 1
        self._board_count: int = 0
        self._last_decisions: list[str] = []
        self._health: int = 40

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def show(self) -> None:
        """Make the dashboard visible."""
        self._visible = True
        if _RICH_AVAILABLE and self._live is None:
            self._live = Live(
                self._build_layout(),
                console=self._console,
                refresh_per_second=int(1 / max(self._refresh_rate, 0.1)),
                screen=False,
            )
            self._live.start()

    def hide(self) -> None:
        """Hide the dashboard."""
        self._visible = False
        if self._live is not None:
            try:
                self._live.stop()
            except Exception:  # noqa: BLE001
                pass
            self._live = None

    def toggle(self) -> bool:
        """Toggle visibility. Returns new visible state."""
        if self._visible:
            self.hide()
        else:
            self.show()
        return self._visible

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------

    def update_bot_status(self, status: str) -> None:
        self._bot_status = status
        self._refresh()

    def update_game_state(
        self,
        turn_number: int = 0,
        gold: int = 0,
        tavern_tier: int = 1,
        board_count: int = 0,
        health: int = 40,
    ) -> None:
        self._turn_number = turn_number
        self._gold = gold
        self._tavern_tier = tavern_tier
        self._board_count = board_count
        self._health = health
        self._refresh()

    def update_decisions(self, decisions: list[str]) -> None:
        """Record the latest AI decisions for display."""
        self._last_decisions = list(decisions)[-10:]  # keep last 10
        self._refresh()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _build_layout(self) -> Any:
        if not _RICH_AVAILABLE:
            return None

        # Status panel
        status_color = {
            "RUNNING": "green",
            "PAUSED": "yellow",
            "STOPPED": "red",
        }.get(self._bot_status, "white")

        status_text = Text(f"Bot: {self._bot_status}", style=f"bold {status_color}")

        # Game state table
        state_table = Table(show_header=False, box=None, padding=(0, 1))
        state_table.add_column(style="dim")
        state_table.add_column(style="bold")
        state_table.add_row("Turn", str(self._turn_number))
        state_table.add_row("Gold", str(self._gold))
        state_table.add_row("Tier", str(self._tavern_tier))
        state_table.add_row("Board", str(self._board_count))
        state_table.add_row("HP", str(self._health))

        # Decision log
        decisions_text = "\n".join(self._last_decisions) if self._last_decisions else "(none)"

        layout = Columns(
            [
                Panel(status_text, title="Status", border_style="blue"),
                Panel(state_table, title="Game State", border_style="green"),
                Panel(decisions_text, title="Decisions", border_style="yellow"),
            ]
        )
        return layout

    def _refresh(self) -> None:
        if self._live is not None:
            try:
                self._live.update(self._build_layout())
            except Exception:  # noqa: BLE001
                pass
        elif self._visible and not _RICH_AVAILABLE:
            print(
                f"[{self._bot_status}] Turn={self._turn_number} "
                f"Gold={self._gold} Tier={self._tavern_tier} "
                f"Board={self._board_count} HP={self._health}"
            )

    def print_summary(self) -> None:
        """Print a one-time snapshot to the terminal (no live mode required)."""
        if _RICH_AVAILABLE:
            assert self._console is not None
            self._console.print(self._build_layout())
        else:
            self._refresh()
