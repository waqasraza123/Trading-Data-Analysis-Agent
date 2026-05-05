import os
import socket
from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.modules.runtime_supervisor.models import RuntimeWorkerInstanceStatus
from app.modules.runtime_supervisor.schemas import RuntimeWorkerInstanceHeartbeat
from app.modules.runtime_supervisor.service import RuntimeSupervisorService


class RuntimeWorkerHeartbeatClient:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        worker_definition_key: str,
        worker_id: str,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.worker_definition_key = worker_definition_key
        self.worker_id = worker_id
        self.host_name = socket.gethostname()
        self.process_id = os.getpid()

    async def starting(self, payload: Mapping[str, object] | None = None) -> None:
        await self.send(RuntimeWorkerInstanceStatus.STARTING, payload)

    async def running(self, payload: Mapping[str, object] | None = None) -> None:
        await self.send(RuntimeWorkerInstanceStatus.RUNNING, payload)

    async def stopped(self, payload: Mapping[str, object] | None = None) -> None:
        await self.send(RuntimeWorkerInstanceStatus.STOPPED, payload)

    async def failed(self, payload: Mapping[str, object] | None = None) -> None:
        await self.send(RuntimeWorkerInstanceStatus.FAILED, payload)

    async def send(
        self,
        status: RuntimeWorkerInstanceStatus,
        payload: Mapping[str, object] | None = None,
    ) -> None:
        if not self.settings.runtime_worker_heartbeat_enabled:
            return
        try:
            async with self.session_factory() as session:
                await RuntimeSupervisorService(session, settings=self.settings).heartbeat(
                    RuntimeWorkerInstanceHeartbeat(
                        worker_definition_key=self.worker_definition_key,
                        worker_id=self.worker_id,
                        status=status,
                        host_name=self.host_name,
                        process_id=self.process_id,
                        payload=dict(payload or {}),
                        metadata={
                            "runtimeSupervisorVersion": self.settings.runtime_supervisor_version
                        },
                    )
                )
        except Exception:
            return
