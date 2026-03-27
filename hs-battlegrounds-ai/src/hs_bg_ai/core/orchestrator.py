"""Core Orchestrator — main game loop coordinating all modules."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from hs_bg_ai.core.events import EventBus, EventType
from hs_bg_ai.models.enums import Phase
from hs_bg_ai.models.game_state import GameState
from hs_bg_ai.models.actions import ActionPlan

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main game loop controller.

    Lifecycle:
        start() -> runs the main loop
        stop()  -> gracefully shuts down
        pause() -> pauses AI decisions (log watching continues)
        resume()-> resumes AI decisions

    Coordinates:
        LogWatcher -> LogDispatcher -> StateManager -> AIEngine -> (Executor)
    """

    def __init__(
        self,
        event_bus: EventBus,
        log_watcher: Any = None,
        log_dispatcher: Any = None,
        state_manager: Any = None,
        ai_engine: Any = None,
        executor: Any = None,
    ) -> None:
        self._event_bus = event_bus
        self._log_watcher = log_watcher
        self._log_dispatcher = log_dispatcher
        self._state_manager = state_manager
        self._ai_engine = ai_engine
        self._executor = executor

        self._running = False
        self._paused = False
        self._current_plan: ActionPlan | None = None
        self._watcher_task: asyncio.Task | None = None

        # Subscribe to events.
        self._event_bus.subscribe(EventType.PHASE_CHANGE, self._on_phase_change)
        self._event_bus.subscribe(EventType.STATE_UPDATED, self._on_state_updated)
        self._event_bus.subscribe(EventType.PAUSE_REQUESTED, self._on_pause)
        self._event_bus.subscribe(EventType.RESUME_REQUESTED, self._on_resume)

    # ── Public API ────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the orchestrator main loop."""
        if self._running:
            logger.warning("Orchestrator already running.")
            return

        self._running = True
        self._paused = False
        logger.info("Orchestrator starting.")

        await self._event_bus.publish(EventType.GAME_START)

        # Start log watcher in background.
        if self._log_watcher is not None:
            self._watcher_task = asyncio.create_task(self._watch_logs())

    async def stop(self) -> None:
        """Stop the orchestrator gracefully."""
        logger.info("Orchestrator stopping.")
        self._running = False

        if self._log_watcher is not None:
            self._log_watcher.stop()

        if self._watcher_task is not None:
            self._watcher_task.cancel()
            try:
                await self._watcher_task
            except asyncio.CancelledError:
                pass

        await self._event_bus.publish(EventType.GAME_OVER)

    def pause(self) -> None:
        """Pause AI decisions (log watching continues)."""
        self._paused = True
        logger.info("Orchestrator paused.")

    def resume(self) -> None:
        """Resume AI decisions."""
        self._paused = False
        logger.info("Orchestrator resumed.")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    # ── Internal: log watching ────────────────────────────────────

    async def _watch_logs(self) -> None:
        """Continuously read log lines and dispatch them."""
        try:
            async for line in self._log_watcher.watch():
                if not self._running:
                    break
                if self._log_dispatcher is not None:
                    await self._log_dispatcher.dispatch(line)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Log watcher encountered an error.")
            await self._event_bus.publish(EventType.ERROR, {"source": "log_watcher"})

    # ── Event handlers ────────────────────────────────────────────

    async def _on_phase_change(self, data: Any) -> None:
        """React to phase changes."""
        if not isinstance(data, GameState):
            return

        phase = data.turn.phase
        if phase == Phase.RECRUIT and not self._paused:
            await self._run_turn(data)
        elif phase == Phase.GAME_OVER:
            logger.info("Game over detected.")

    async def _on_state_updated(self, data: Any) -> None:
        """Track state updates for turn detection."""
        if not isinstance(data, GameState):
            return
        # Could trigger additional logic (e.g. mid-turn re-evaluation).

    async def _on_pause(self, data: Any) -> None:
        self.pause()

    async def _on_resume(self, data: Any) -> None:
        self.resume()

    # ── Turn execution ────────────────────────────────────────────

    async def _run_turn(self, state: GameState) -> None:
        """Execute one full turn: AI decides, then executor runs the plan."""
        if self._ai_engine is None:
            return

        try:
            plan = self._ai_engine.decide(state)
            self._current_plan = plan

            await self._event_bus.publish(EventType.TURN_START, {
                "turn": state.turn.turn_number,
                "actions": len(plan.actions),
            })

            if self._executor is not None:
                for action in plan.actions:
                    if not self._running or self._paused:
                        break
                    try:
                        result = await self._executor.execute(action)
                        if result.success:
                            await self._event_bus.publish(EventType.ACTION_COMPLETED, result)
                        else:
                            await self._event_bus.publish(EventType.ACTION_FAILED, result)
                    except Exception as exc:
                        logger.error("Action execution failed: %s", exc)
                        await self._event_bus.publish(EventType.ACTION_FAILED, {
                            "action": action,
                            "error": str(exc),
                        })

            await self._event_bus.publish(EventType.TURN_END, {
                "turn": state.turn.turn_number,
            })

        except Exception:
            logger.exception("Turn execution error.")
            await self._event_bus.publish(EventType.ERROR, {"source": "turn_execution"})
