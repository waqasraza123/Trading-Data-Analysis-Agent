import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.modules.market_scans.scanner import MarketScanExecutor


class MarketScanWorkerRuntime:
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
        self.worker_id = worker_id or f"market-scan-worker-{uuid4()}"
        self.logger = logger or logging.getLogger(__name__)
        self.sleep = sleep
        self.stopping = asyncio.Event()

    async def run_forever(self) -> None:
        if not self.settings.market_scan_worker_enabled:
            self.logger.info("market_scan_worker_disabled", extra={"worker_id": self.worker_id})
            return
        self.logger.info("market_scan_worker_started", extra={"worker_id": self.worker_id})
        try:
            while not self.stopping.is_set():
                run_count = 0
                try:
                    run_count = await self.poll_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.logger.exception(
                        "market_scan_worker_poll_failed",
                        extra={"worker_id": self.worker_id},
                    )
                await self.sleep(self.next_sleep_seconds(run_count))
        finally:
            self.logger.info("market_scan_worker_stopped", extra={"worker_id": self.worker_id})

    async def poll_once(self) -> int:
        self.logger.info(
            "market_scan_worker_poll_started",
            extra={
                "worker_id": self.worker_id,
                "batch_size": self.settings.market_scan_worker_batch_size,
            },
        )
        async with self.session_factory() as session:
            runs = await MarketScanExecutor(session, settings=self.settings).run_due_scan_configs(
                limit=self.settings.market_scan_worker_batch_size,
            )
            return len(runs)

    def next_sleep_seconds(self, run_count: int) -> float:
        base_seconds = self.settings.market_scan_worker_poll_seconds
        if run_count:
            return base_seconds
        return base_seconds + random.uniform(0, min(base_seconds, 2))

    async def stop(self) -> None:
        self.stopping.set()
