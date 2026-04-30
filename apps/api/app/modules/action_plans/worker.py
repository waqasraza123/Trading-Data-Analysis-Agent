import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.modules.action_plans.runner import ReasoningActionRunner


class ReasoningActionWorkerRuntime:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        worker_id: str | None = None,
        logger: logging.Logger | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.worker_id = worker_id or f"reasoning-action-worker-{uuid4()}"
        self.logger = logger or logging.getLogger(__name__)
        self.sleep = sleep
        self.stopping = asyncio.Event()

    async def run_forever(self) -> None:
        if not self.settings.reasoning_action_worker_enabled:
            self.logger.info(
                "reasoning_action_worker_disabled",
                extra={"worker_id": self.worker_id},
            )
            return
        self.logger.info(
            "reasoning_action_worker_started",
            extra={"worker_id": self.worker_id},
        )
        try:
            while not self.stopping.is_set():
                claimed_count = 0
                try:
                    claimed_count = await self.poll_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.logger.exception(
                        "reasoning_action_worker_poll_failed",
                        extra={"worker_id": self.worker_id},
                    )
                await self.sleep(self.next_sleep_seconds(claimed_count))
        finally:
            self.logger.info(
                "reasoning_action_worker_stopped",
                extra={"worker_id": self.worker_id},
            )

    async def poll_once(self) -> int:
        self.logger.info(
            "reasoning_action_worker_poll_started",
            extra={
                "worker_id": self.worker_id,
                "batch_size": self.settings.reasoning_action_worker_batch_size,
                "max_concurrency": self.settings.reasoning_action_worker_max_concurrency,
            },
        )
        runner = ReasoningActionRunner(
            settings=self.settings,
            logger=self.logger,
            session_factory=self.session_factory,
            worker_id=self.worker_id,
        )
        result = await runner.execute_due_actions(
            limit=self.settings.reasoning_action_worker_batch_size
        )
        return result.claimed_count

    def next_sleep_seconds(self, claimed_count: int) -> float:
        base_seconds = self.settings.reasoning_action_worker_poll_seconds
        if claimed_count:
            return base_seconds
        jitter = self.settings.reasoning_action_worker_jitter_seconds
        if jitter <= 0:
            return base_seconds
        return base_seconds + random.uniform(0, jitter)

    async def stop(self) -> None:
        self.stopping.set()
