import asyncio
from typing import Any, cast

import pytest

from app.config import AppEnvironment, Settings, WorkerSupervisorComponent
from app.workers.supervisor import SupervisedWorker, WorkerSupervisorRuntime


class FakeWorker:
    def __init__(self, mode: str = "wait") -> None:
        self.mode = mode
        self.started = asyncio.Event()
        self.stop_event = asyncio.Event()
        self.stop_count = 0

    async def run_forever(self) -> None:
        self.started.set()
        if self.mode == "complete":
            return
        if self.mode == "fail":
            raise RuntimeError("worker failed")
        await self.stop_event.wait()

    async def stop(self) -> None:
        self.stop_count += 1
        self.stop_event.set()


def make_runtime(settings: Settings | None = None) -> WorkerSupervisorRuntime:
    return WorkerSupervisorRuntime(
        session_factory=cast(Any, object()),
        settings=settings or Settings(_env_file=None, app_env=AppEnvironment.TEST),
    )


@pytest.mark.asyncio
async def test_supervisor_returns_when_no_workers_are_configured() -> None:
    runtime = make_runtime()

    await runtime.run_forever()

    assert runtime.workers == []


@pytest.mark.asyncio
async def test_supervisor_stops_all_workers_on_stop_event() -> None:
    runtime = make_runtime()
    first = FakeWorker()
    second = FakeWorker()
    runtime.workers = [
        SupervisedWorker("first", "first-1", first.run_forever, first.stop),
        SupervisedWorker("second", "second-1", second.run_forever, second.stop),
    ]

    supervisor_task = asyncio.create_task(runtime.run_forever())
    await first.started.wait()
    await second.started.wait()
    await runtime.stop()
    await supervisor_task

    assert first.stop_count == 1
    assert second.stop_count == 1


@pytest.mark.asyncio
async def test_supervisor_fails_when_worker_completes_unexpectedly() -> None:
    runtime = make_runtime()
    completed = FakeWorker(mode="complete")
    waiting = FakeWorker()
    runtime.workers = [
        SupervisedWorker("completed", "completed-1", completed.run_forever, completed.stop),
        SupervisedWorker("waiting", "waiting-1", waiting.run_forever, waiting.stop),
    ]

    with pytest.raises(RuntimeError, match="stopped unexpectedly"):
        await runtime.run_forever()

    assert completed.stop_count == 1
    assert waiting.stop_count == 1


@pytest.mark.asyncio
async def test_supervisor_fails_when_worker_raises() -> None:
    runtime = make_runtime()
    failed = FakeWorker(mode="fail")
    waiting = FakeWorker()
    runtime.workers = [
        SupervisedWorker("failed", "failed-1", failed.run_forever, failed.stop),
        SupervisedWorker("waiting", "waiting-1", waiting.run_forever, waiting.stop),
    ]

    with pytest.raises(RuntimeError, match="Supervised worker failed"):
        await runtime.run_forever()

    assert failed.stop_count == 1
    assert waiting.stop_count == 1


def test_supervisor_skips_disabled_optional_workers() -> None:
    runtime = make_runtime(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            worker_supervisor_components=[
                WorkerSupervisorComponent.REASONING_ACTIONS,
                WorkerSupervisorComponent.NOTIFICATIONS,
            ],
        )
    )

    assert runtime.workers == []


def test_settings_parse_worker_supervisor_components() -> None:
    settings = Settings(
        _env_file=None,
        worker_supervisor_components="live_feed, stale_monitor, notifications",
    )

    assert settings.worker_supervisor_components == [
        WorkerSupervisorComponent.LIVE_FEED,
        WorkerSupervisorComponent.STALE_MONITOR,
        WorkerSupervisorComponent.NOTIFICATIONS,
    ]
