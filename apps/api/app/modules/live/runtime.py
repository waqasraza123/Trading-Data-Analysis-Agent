import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.time import utc_now
from app.modules.live.heartbeat import LiveStalePolicy
from app.modules.live.models import LiveFeedEvent, LiveFeedSubscriptionStatus
from app.modules.live.providers.base import LiveProviderDisconnectedError
from app.modules.live.providers.registry import get_live_provider
from app.modules.live.repository import LiveRepository
from app.modules.live.schemas import LiveProviderMessage
from app.modules.live.service import LiveService
from app.modules.runtime_supervisor.heartbeats import RuntimeWorkerHeartbeatClient
from app.modules.symbols.models import Symbol


@dataclass(frozen=True)
class ReconnectPolicy:
    initial_seconds: float
    max_seconds: float
    multiplier: float


@dataclass(frozen=True)
class SubscriptionRuntimeState:
    subscription_id: UUID
    symbol: str
    timeframe: str
    provider: str
    config_json: dict[str, object]


def reconnect_delay(attempt: int, policy: ReconnectPolicy) -> float:
    return min(policy.initial_seconds * (policy.multiplier**attempt), policy.max_seconds)


class LiveFeedRuntime:
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
        self.worker_id = worker_id or f"live-worker-{uuid4()}"
        self.logger = logger or logging.getLogger(__name__)
        self.sleep = sleep
        self.subscription_tasks: dict[UUID, asyncio.Task[int]] = {}
        self.stopping = asyncio.Event()
        self.heartbeat = RuntimeWorkerHeartbeatClient(
            session_factory=session_factory,
            settings=settings,
            worker_definition_key="live_feed_worker",
            worker_id=self.worker_id,
        )

    @property
    def reconnect_policy(self) -> ReconnectPolicy:
        return ReconnectPolicy(
            initial_seconds=self.settings.live_feed_reconnect_initial_seconds,
            max_seconds=self.settings.live_feed_reconnect_max_seconds,
            multiplier=self.settings.live_feed_reconnect_multiplier,
        )

    @property
    def lease_seconds(self) -> float:
        return max(self.settings.live_feed_worker_poll_seconds * 3, 30)

    async def run_forever(self) -> None:
        self.logger.info("live_worker_started", extra={"worker_id": self.worker_id})
        await self.heartbeat.starting({"activeSubscriptionTasks": len(self.subscription_tasks)})
        try:
            while not self.stopping.is_set():
                try:
                    await self.poll_once()
                    await self.heartbeat.running(
                        {"activeSubscriptionTasks": len(self.subscription_tasks)}
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.logger.exception(
                        "live_worker_poll_failed",
                        extra={"worker_id": self.worker_id},
                    )
                await self.sleep(self.settings.live_feed_worker_poll_seconds)
        finally:
            await self.stop()
            await self.heartbeat.stopped({"activeSubscriptionTasks": 0})
            self.logger.info("live_worker_stopped", extra={"worker_id": self.worker_id})

    async def stop(self) -> None:
        self.stopping.set()
        tasks = list(self.subscription_tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.subscription_tasks.clear()

    async def poll_once(self) -> None:
        self.cleanup_finished_tasks()
        async with self.session_factory() as session:
            service = LiveService(session)
            subscriptions = await service.list_runtime_candidates()
        for subscription in subscriptions:
            if subscription.id in self.subscription_tasks:
                continue
            task = asyncio.create_task(self.run_subscription(subscription.id))
            self.subscription_tasks[subscription.id] = task

    def cleanup_finished_tasks(self) -> None:
        finished_ids = [
            subscription_id
            for subscription_id, task in self.subscription_tasks.items()
            if task.done()
        ]
        for subscription_id in finished_ids:
            self.subscription_tasks.pop(subscription_id, None)

    async def run_subscription(
        self,
        subscription_id: UUID,
        max_messages: int | None = None,
        max_reconnects: int | None = None,
    ) -> int:
        acquired = await self.acquire_lease(subscription_id)
        if not acquired:
            return 0
        processed_count = 0
        lease_task = asyncio.create_task(self.refresh_lease_loop(subscription_id))
        try:
            state = await self.load_runtime_state(subscription_id)
            processed_count = await self.process_subscription_stream(
                state=state,
                max_messages=max_messages,
                max_reconnects=max_reconnects,
            )
        finally:
            lease_task.cancel()
            await asyncio.gather(lease_task, return_exceptions=True)
            await self.release_lease(subscription_id)
        return processed_count

    async def process_subscription_stream(
        self,
        state: SubscriptionRuntimeState,
        max_messages: int | None,
        max_reconnects: int | None,
    ) -> int:
        provider = get_live_provider(state.provider)
        processed_count = 0
        reconnect_attempt = 0
        while not self.stopping.is_set():
            try:
                await provider.connect()
                await provider.subscribe(state.symbol, state.timeframe)
                self.log_subscription_started(state, reconnect_attempt)
                async for message in provider.stream_messages(
                    state.symbol,
                    state.timeframe,
                    state.config_json,
                ):
                    event = await self.process_provider_message(state.subscription_id, message)
                    processed_count += 1
                    await self.refresh_lease(state.subscription_id)
                    if await self.should_stop_after_event(state.subscription_id, event):
                        return processed_count
                    if max_messages is not None and processed_count >= max_messages:
                        return processed_count
                return processed_count
            except LiveProviderDisconnectedError as error:
                await provider.disconnect()
                if max_reconnects is not None and reconnect_attempt >= max_reconnects:
                    await self.mark_failed(state.subscription_id, str(error))
                    return processed_count
                delay_seconds = reconnect_delay(reconnect_attempt, self.reconnect_policy)
                self.logger.warning(
                    "live_reconnect_scheduled",
                    extra={
                        "worker_id": self.worker_id,
                        "subscription_id": str(state.subscription_id),
                        "provider": state.provider,
                        "delay_seconds": delay_seconds,
                    },
                )
                await self.sleep(delay_seconds)
                reconnect_attempt += 1
                continue
            except asyncio.CancelledError:
                raise
            except Exception:
                await self.mark_failed(state.subscription_id, "Live subscription runtime failed")
                self.logger.exception(
                    "live_subscription_failed",
                    extra={
                        "worker_id": self.worker_id,
                        "subscription_id": str(state.subscription_id),
                        "provider": state.provider,
                    },
                )
                return processed_count
            finally:
                await provider.unsubscribe(state.symbol, state.timeframe)
                await provider.disconnect()
        return processed_count

    def log_subscription_started(
        self,
        state: SubscriptionRuntimeState,
        reconnect_attempt: int,
    ) -> None:
        event_name = (
            "live_reconnect_succeeded" if reconnect_attempt else "live_subscription_started"
        )
        self.logger.info(
            event_name,
            extra={
                "worker_id": self.worker_id,
                "subscription_id": str(state.subscription_id),
                "provider": state.provider,
            },
        )

    async def process_provider_message(
        self,
        subscription_id: UUID,
        message: LiveProviderMessage,
    ) -> LiveFeedEvent:
        async with self.session_factory() as session:
            event = await LiveService(session).ingest_provider_message(subscription_id, message)
            return event

    async def should_stop_after_event(self, subscription_id: UUID, event: LiveFeedEvent) -> bool:
        async with self.session_factory() as session:
            subscription = await LiveRepository(session).get_subscription(subscription_id)
            if subscription is None:
                return True
            return subscription.status in {
                LiveFeedSubscriptionStatus.PAUSED,
                LiveFeedSubscriptionStatus.FAILED,
                LiveFeedSubscriptionStatus.STOPPED,
            }

    async def acquire_lease(self, subscription_id: UUID) -> bool:
        async with self.session_factory() as session:
            subscription = await LiveService(session).acquire_subscription_lease(
                subscription_id=subscription_id,
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
            )
            return subscription is not None

    async def refresh_lease(self, subscription_id: UUID) -> bool:
        async with self.session_factory() as session:
            return await LiveService(session).refresh_subscription_lease(
                subscription_id=subscription_id,
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
            )

    async def refresh_lease_loop(self, subscription_id: UUID) -> None:
        interval_seconds = max(self.lease_seconds / 3, 1)
        while not self.stopping.is_set():
            await self.sleep(interval_seconds)
            refreshed = await self.refresh_lease(subscription_id)
            if not refreshed:
                return

    async def release_lease(self, subscription_id: UUID) -> None:
        async with self.session_factory() as session:
            await LiveService(session).release_subscription_lease(
                subscription_id=subscription_id,
                worker_id=self.worker_id,
            )

    async def mark_failed(self, subscription_id: UUID, error_message: str) -> None:
        async with self.session_factory() as session:
            await LiveService(session).mark_failed(subscription_id, error_message)

    async def load_runtime_state(self, subscription_id: UUID) -> SubscriptionRuntimeState:
        async with self.session_factory() as session:
            subscription = await LiveRepository(session).get_subscription(subscription_id)
            if subscription is None:
                msg = "Live subscription not found"
                raise RuntimeError(msg)
            symbol = await session.get(Symbol, subscription.symbol_id)
            if symbol is None:
                msg = "Live subscription symbol not found"
                raise RuntimeError(msg)
            return SubscriptionRuntimeState(
                subscription_id=subscription.id,
                symbol=symbol.symbol,
                timeframe=subscription.timeframe,
                provider=subscription.provider,
                config_json=subscription.config_json,
            )


class LiveStaleMonitor:
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
        self.worker_id = worker_id or f"stale-monitor-{uuid4()}"
        self.logger = logger or logging.getLogger(__name__)
        self.sleep = sleep
        self.stopping = asyncio.Event()
        self.heartbeat = RuntimeWorkerHeartbeatClient(
            session_factory=session_factory,
            settings=settings,
            worker_definition_key="live_stale_monitor",
            worker_id=self.worker_id,
        )

    @property
    def stale_policy(self) -> LiveStalePolicy:
        return LiveStalePolicy(
            message_stale_after_seconds=self.settings.live_feed_stale_message_seconds,
            final_candle_stale_after_seconds=self.settings.live_feed_stale_final_candle_seconds,
        )

    async def run_forever(self) -> None:
        self.logger.info("stale_monitor_started", extra={"worker_id": self.worker_id})
        await self.heartbeat.starting()
        try:
            while not self.stopping.is_set():
                stale_count = await self.run_once()
                await self.heartbeat.running({"staleCount": stale_count})
                await self.sleep(self.settings.live_feed_worker_poll_seconds)
        except asyncio.CancelledError:
            raise
        except Exception:
            await self.heartbeat.failed()
            self.logger.exception("stale_monitor_failed")
            raise
        finally:
            await self.heartbeat.stopped()
            self.logger.info("stale_monitor_stopped", extra={"worker_id": self.worker_id})

    async def run_once(self) -> int:
        async with self.session_factory() as session:
            stale_count = await LiveService(session).refresh_stale_statuses(
                workspace_id=None,
                policy=self.stale_policy,
            )
        if stale_count:
            self.logger.warning(
                "live_subscription_stale",
                extra={"stale_count": stale_count, "checked_at": utc_now().isoformat()},
            )
        return stale_count

    async def stop(self) -> None:
        self.stopping.set()
