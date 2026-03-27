"""Main entry point — assemble all modules and run the bot."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

from hs_bg_ai.ai.engine import AIEngine
from hs_bg_ai.config import AppConfig, load_config
from hs_bg_ai.core.events import EventBus
from hs_bg_ai.core.orchestrator import Orchestrator
from hs_bg_ai.log_engine.dispatcher import LogDispatcher
from hs_bg_ai.log_engine.watcher import LogWatcher
from hs_bg_ai.log_parsers.board_parser import BoardParser
from hs_bg_ai.log_parsers.hand_parser import HandParser
from hs_bg_ai.log_parsers.hero_parser import HeroParser
from hs_bg_ai.log_parsers.opponent_parser import OpponentParser
from hs_bg_ai.log_parsers.resource_parser import ResourceParser
from hs_bg_ai.log_parsers.shop_parser import ShopParser
from hs_bg_ai.log_parsers.turn_parser import TurnParser
from hs_bg_ai.state.manager import StateManager

logger = logging.getLogger("hs_bg_ai")


def _setup_logging(config: AppConfig) -> None:
    """Configure basic logging."""
    level = getattr(logging, config.log.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    if config.log.log_file:
        file_handler = logging.FileHandler(config.log.log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(file_handler)


def build_app(config: AppConfig) -> Orchestrator:
    """Assemble all modules with dependency injection."""
    event_bus = EventBus()

    # Log engine.
    log_path = config.log.log_path
    if not log_path:
        # Default Hearthstone log path (Windows).
        log_path = str(
            Path.home()
            / "AppData"
            / "Local"
            / "Blizzard"
            / "Hearthstone"
            / "Logs"
            / "Power.log"
        )
    watcher = LogWatcher(log_path)

    dispatcher = LogDispatcher(event_bus)
    dispatcher.register_parsers([
        TurnParser(),
        ShopParser(),
        HandParser(),
        BoardParser(),
        ResourceParser(),
        HeroParser(),
        OpponentParser(),
    ])

    # State.
    state_manager = StateManager(event_bus)

    # AI.
    ai_engine = AIEngine(config)

    # Orchestrator (executor=None — to be wired by executor module later).
    orchestrator = Orchestrator(
        event_bus=event_bus,
        log_watcher=watcher,
        log_dispatcher=dispatcher,
        state_manager=state_manager,
        ai_engine=ai_engine,
        executor=None,
    )

    return orchestrator


async def async_main(config_path: str | None = None) -> None:
    """Async entry point."""
    config = load_config(config_path)
    _setup_logging(config)

    logger.info("HS Battlegrounds AI starting...")
    orchestrator = build_app(config)

    # Handle shutdown signals.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(orchestrator.stop()))
        except NotImplementedError:
            # Windows doesn't support add_signal_handler.
            pass

    try:
        await orchestrator.start()
        # Keep running until stopped.
        while orchestrator.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await orchestrator.stop()
        logger.info("HS Battlegrounds AI stopped.")


def main() -> None:
    """CLI entry point."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(async_main(config_path))


if __name__ == "__main__":
    main()
