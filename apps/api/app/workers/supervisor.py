import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, WorkerSupervisorComponent, get_settings
from app.core.logging import configure_logging
from app.db.session import get_async_session_factory
from app.modules.action_plans.worker import ReasoningActionWorkerRuntime
from app.modules.live.supervisor import LiveFeedSupervisor, LiveStaleSupervisor
from app.modules.market_scans.scheduler import MarketScanWorkerRuntime
from app.modules.notifications.worker import NotificationWorkerRuntime
from app.workers.runtime import register_signal_handlers, to_coroutine


@dataclass(frozen=True)
class SupervisedWorker:
    name: str
    worker_id: str
    run_forever: Callable[[], Awaitable[None]]
    stop: Callable[[], Awaitable[None]]


class WorkerSupervisorRuntime:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        logger: logging.Logger | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.logger = logger or logging.getLogger(settings.service_name)
        self.stop_event = asyncio.Event()
        self.workers = self.build_workers()

    def build_workers(self) -> list[SupervisedWorker]:
        workers: list[SupervisedWorker] = []
        for component in self.settings.worker_supervisor_components:
            worker = self.build_worker(component)
            if worker is not None:
                workers.append(worker)
        return workers

    def build_worker(self, component: WorkerSupervisorComponent) -> SupervisedWorker | None:
        if component == WorkerSupervisorComponent.LIVE_FEED:
            worker_id = f"live-worker-{uuid4()}"
            live_runtime = LiveFeedSupervisor(
                session_factory=self.session_factory,
                settings=self.settings,
                worker_id=worker_id,
                logger=self.logger,
            )
            return SupervisedWorker(
                "live_feed_worker",
                worker_id,
                live_runtime.run_forever,
                live_runtime.stop,
            )
        if component == WorkerSupervisorComponent.STALE_MONITOR:
            worker_id = f"stale-monitor-{uuid4()}"
            stale_runtime = LiveStaleSupervisor(
                session_factory=self.session_factory,
                settings=self.settings,
                logger=self.logger,
            )
            return SupervisedWorker(
                "stale_monitor",
                worker_id,
                stale_runtime.run_forever,
                stale_runtime.stop,
            )
        if component == WorkerSupervisorComponent.REASONING_ACTIONS:
            if not self.settings.reasoning_action_worker_enabled:
                self.logger.info(
                    "supervised_worker_disabled",
                    extra={"worker_name": component.value},
                )
                return None
            worker_id = f"reasoning-action-worker-{uuid4()}"
            reasoning_runtime = ReasoningActionWorkerRuntime(
                session_factory=self.session_factory,
                settings=self.settings,
                worker_id=worker_id,
                logger=self.logger,
            )
            return SupervisedWorker(
                "reasoning_action_worker",
                worker_id,
                reasoning_runtime.run_forever,
                reasoning_runtime.stop,
            )
        if component == WorkerSupervisorComponent.NOTIFICATIONS:
            if not self.settings.notification_worker_enabled:
                self.logger.info(
                    "supervised_worker_disabled",
                    extra={"worker_name": component.value},
                )
                return None
            worker_id = f"notification-worker-{uuid4()}"
            notification_runtime = NotificationWorkerRuntime(
                session_factory=self.session_factory,
                settings=self.settings,
                worker_id=worker_id,
                logger=self.logger,
            )
            return SupervisedWorker(
                "notification_worker",
                worker_id,
                notification_runtime.run_forever,
                notification_runtime.stop,
            )
        if component == WorkerSupervisorComponent.MARKET_SCANS:
            if not self.settings.market_scan_worker_enabled:
                self.logger.info(
                    "supervised_worker_disabled",
                    extra={"worker_name": component.value},
                )
                return None
            worker_id = f"market-scan-worker-{uuid4()}"
            market_scan_runtime = MarketScanWorkerRuntime(
                session_factory=self.session_factory,
                settings=self.settings,
                worker_id=worker_id,
                logger=self.logger,
            )
            return SupervisedWorker(
                "market_scan_worker",
                worker_id,
                market_scan_runtime.run_forever,
                market_scan_runtime.stop,
            )

    async def run_forever(self) -> None:
        if not self.workers:
            self.logger.warning("worker_supervisor_no_workers_configured")
            return
        register_signal_handlers(self.stop_event)
        tasks: dict[asyncio.Task[None], SupervisedWorker] = {
            asyncio.create_task(to_coroutine(worker.run_forever())): worker
            for worker in self.workers
        }
        self.log_started()
        stop_task = asyncio.create_task(self.stop_event.wait())
        pending: set[asyncio.Task[Any]] = set()
        try:
            done, pending = await asyncio.wait(
                {*tasks.keys(), stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if stop_task not in done:
                worker_done = cast(set[asyncio.Task[None]], done - {stop_task})
                failed_workers = self.finished_failed_workers(worker_done, tasks)
                if failed_workers:
                    raise RuntimeError(f"Supervised worker failed: {', '.join(failed_workers)}")
                completed_workers = self.finished_worker_names(worker_done, tasks)
                if completed_workers:
                    raise RuntimeError(
                        f"Supervised worker stopped unexpectedly: {', '.join(completed_workers)}"
                    )
            for task in pending:
                task.cancel()
        finally:
            for task in pending:
                task.cancel()
            await self.stop_all(tasks)
            await asyncio.gather(*tasks.keys(), stop_task, return_exceptions=True)
            self.log_stopped()

    async def stop_all(self, tasks: dict[asyncio.Task[None], SupervisedWorker]) -> None:
        await asyncio.gather(
            *(worker.stop() for worker in tasks.values()),
            return_exceptions=True,
        )
        timeout = self.settings.worker_supervisor_shutdown_timeout_seconds
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks.keys(), return_exceptions=True),
                timeout=timeout,
            )
        except TimeoutError:
            self.logger.error(
                "worker_supervisor_shutdown_timeout",
                extra={"timeout_seconds": timeout},
            )
            for task in tasks:
                task.cancel()

    async def stop(self) -> None:
        self.stop_event.set()

    def finished_failed_workers(
        self,
        done: set[asyncio.Task[None]],
        tasks: dict[asyncio.Task[None], SupervisedWorker],
    ) -> list[str]:
        failed: list[str] = []
        for task in done:
            worker = tasks.get(task)
            if worker is None:
                continue
            if task.cancelled():
                continue
            if task.exception() is not None:
                failed.append(worker.name)
        return failed

    def finished_worker_names(
        self,
        done: set[asyncio.Task[None]],
        tasks: dict[asyncio.Task[None], SupervisedWorker],
    ) -> list[str]:
        return [worker.name for task, worker in tasks.items() if task in done]

    def log_started(self) -> None:
        self.logger.info(
            "worker_supervisor_started",
            extra={
                "workers": [
                    {"worker_name": worker.name, "worker_id": worker.worker_id}
                    for worker in self.workers
                ]
            },
        )

    def log_stopped(self) -> None:
        self.logger.info(
            "worker_supervisor_stopped",
            extra={"worker_count": len(self.workers)},
        )


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is required to run the worker supervisor"
        raise RuntimeError(msg)
    logger = logging.getLogger(settings.service_name)
    runtime = WorkerSupervisorRuntime(
        session_factory=session_factory,
        settings=settings,
        logger=logger,
    )
    await runtime.run_forever()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
