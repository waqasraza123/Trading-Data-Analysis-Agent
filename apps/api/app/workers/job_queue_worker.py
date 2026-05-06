import argparse
import asyncio
import logging
import os
from uuid import uuid4

from app.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_async_session_factory
from app.modules.job_queue.workers import JobQueueWorkerRuntime
from app.workers.runtime import run_until_stopped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default=os.environ.get("JOB_QUEUE_WORKER_QUEUE", "default"))
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.environ.get("JOB_QUEUE_WORKER_CONCURRENCY", "4")),
    )
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is required to run the job queue worker"
        raise RuntimeError(msg)
    logger = logging.getLogger(settings.service_name)
    worker_id = f"job-queue-worker-{args.queue}-{uuid4()}"
    runtime = JobQueueWorkerRuntime(
        session_factory=session_factory,
        settings=settings,
        queue_name=args.queue,
        worker_id=worker_id,
        logger=logger,
        max_concurrency=args.concurrency,
    )
    await run_until_stopped(
        worker_name="job_queue_worker",
        logger=logger,
        run_forever=runtime.run_forever,
        stop=runtime.stop,
        extra={"worker_id": worker_id, "queue_name": args.queue},
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
