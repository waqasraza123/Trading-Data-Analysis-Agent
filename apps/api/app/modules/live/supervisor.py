import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.modules.live.runtime import LiveFeedRuntime, LiveStaleMonitor


class LiveFeedSupervisor:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        worker_id: str | None = None,
        logger: logging.Logger | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        kwargs = {}
        if sleep is not None:
            kwargs["sleep"] = sleep
        self.runtime = LiveFeedRuntime(
            session_factory=session_factory,
            settings=settings,
            worker_id=worker_id,
            logger=logger,
            **kwargs,
        )

    async def run_forever(self) -> None:
        await self.runtime.run_forever()

    async def stop(self) -> None:
        await self.runtime.stop()


class LiveStaleSupervisor:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        worker_id: str | None = None,
        logger: logging.Logger | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        kwargs = {}
        if sleep is not None:
            kwargs["sleep"] = sleep
        self.monitor = LiveStaleMonitor(
            session_factory=session_factory,
            settings=settings,
            worker_id=worker_id,
            logger=logger,
            **kwargs,
        )

    async def run_forever(self) -> None:
        await self.monitor.run_forever()

    async def stop(self) -> None:
        await self.monitor.stop()
