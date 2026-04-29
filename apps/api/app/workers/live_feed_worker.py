import asyncio
import logging

from app.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_async_session_factory
from app.modules.live.supervisor import LiveFeedSupervisor


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is required to run the live feed worker"
        raise RuntimeError(msg)
    logger = logging.getLogger(settings.service_name)
    supervisor = LiveFeedSupervisor(
        session_factory=session_factory,
        settings=settings,
        logger=logger,
    )
    await supervisor.run_forever()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
