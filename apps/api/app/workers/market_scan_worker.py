import asyncio
import logging
from uuid import uuid4

from app.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_async_session_factory
from app.modules.market_scans.scheduler import MarketScanWorkerRuntime
from app.workers.runtime import run_until_stopped


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is required to run the market scan worker"
        raise RuntimeError(msg)
    logger = logging.getLogger(settings.service_name)
    worker_id = f"market-scan-worker-{uuid4()}"
    runtime = MarketScanWorkerRuntime(
        session_factory=session_factory,
        settings=settings,
        worker_id=worker_id,
        logger=logger,
    )
    await run_until_stopped(
        worker_name="market_scan_worker",
        logger=logger,
        run_forever=runtime.run_forever,
        stop=runtime.stop,
        extra={"worker_id": worker_id},
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
