import asyncio
import logging
from uuid import uuid4

from app.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_async_session_factory
from app.modules.live.supervisor import LiveStaleSupervisor
from app.workers.runtime import run_until_stopped


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is required to run the stale monitor"
        raise RuntimeError(msg)
    logger = logging.getLogger(settings.service_name)
    worker_id = f"stale-monitor-{uuid4()}"
    supervisor = LiveStaleSupervisor(
        session_factory=session_factory,
        settings=settings,
        logger=logger,
    )
    await run_until_stopped(
        worker_name="stale_monitor",
        logger=logger,
        run_forever=supervisor.run_forever,
        stop=supervisor.stop,
        extra={"worker_id": worker_id},
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
