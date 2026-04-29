import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable


async def run_until_stopped(
    worker_name: str,
    logger: logging.Logger,
    run_forever: Callable[[], Awaitable[None]],
    stop: Callable[[], Awaitable[None]],
    extra: dict[str, object] | None = None,
) -> None:
    log_extra = extra or {}
    logger.info("worker_started", extra={"worker_name": worker_name, **log_extra})
    stop_event = asyncio.Event()
    register_signal_handlers(stop_event)
    worker_task: asyncio.Task[None] = asyncio.create_task(to_coroutine(run_forever()))
    stop_task: asyncio.Task[bool] = asyncio.create_task(stop_event.wait())
    done, pending = await asyncio.wait(
        {worker_task, stop_task},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    try:
        if worker_task in done:
            worker_task.result()
    except Exception:
        logger.exception("worker_failed", extra={"worker_name": worker_name, **log_extra})
        raise
    finally:
        await stop()
        await asyncio.gather(worker_task, stop_task, return_exceptions=True)
        logger.info("worker_stopped", extra={"worker_name": worker_name, **log_extra})


def register_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop_event.set)
        except NotImplementedError:
            continue


async def to_coroutine(awaitable: Awaitable[None]) -> None:
    await awaitable
