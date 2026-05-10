from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, SelectLabelStyle, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.runtime_supervisor.models import (
    RuntimeRunRequestStatus,
    RuntimeWorkerDefinition,
    RuntimeWorkerInstance,
    RuntimeWorkerInstanceStatus,
    RuntimeWorkerRunRequest,
)


class RuntimeSupervisorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_worker_definition(
        self,
        definition: RuntimeWorkerDefinition,
    ) -> tuple[RuntimeWorkerDefinition, bool]:
        existing = await self.get_worker_definition(definition.key)
        if existing is None:
            self.session.add(definition)
            await self.session.flush()
            await self.session.refresh(definition)
            return definition, True
        existing.name = definition.name
        existing.description = definition.description
        existing.worker_type = definition.worker_type
        existing.status = definition.status
        existing.command = definition.command
        existing.required_settings_json = definition.required_settings_json
        existing.optional_settings_json = definition.optional_settings_json
        existing.safety_notes_json = definition.safety_notes_json
        existing.metadata_json = definition.metadata_json
        await self.session.flush()
        await self.session.refresh(existing)
        return existing, False

    async def list_worker_definitions(
        self,
        status: str | None = None,
        worker_type: str | None = None,
    ) -> list[RuntimeWorkerDefinition]:
        statement: Select[tuple[RuntimeWorkerDefinition]] = select(
            RuntimeWorkerDefinition
        ).order_by(RuntimeWorkerDefinition.key.asc())
        if status is not None:
            statement = statement.where(RuntimeWorkerDefinition.status == status)
        if worker_type is not None:
            statement = statement.where(RuntimeWorkerDefinition.worker_type == worker_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_worker_definition(self, key: str) -> RuntimeWorkerDefinition | None:
        statement: Select[tuple[RuntimeWorkerDefinition]] = select(RuntimeWorkerDefinition).where(
            RuntimeWorkerDefinition.key == key
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_worker_instance_by_worker_id(
        self,
        worker_id: str,
    ) -> RuntimeWorkerInstance | None:
        statement: Select[tuple[RuntimeWorkerInstance]] = select(RuntimeWorkerInstance).where(
            RuntimeWorkerInstance.worker_id == worker_id
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_worker_instance(
        self,
        instance: RuntimeWorkerInstance,
    ) -> RuntimeWorkerInstance:
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update_worker_instance(
        self,
        instance: RuntimeWorkerInstance,
    ) -> RuntimeWorkerInstance:
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def list_worker_instances(
        self,
        limit: int,
        offset: int,
        worker_definition_key: str | None = None,
        workspace_id: UUID | None = None,
        status: str | None = None,
    ) -> list[RuntimeWorkerInstance]:
        statement: Select[tuple[RuntimeWorkerInstance]] = (
            select(RuntimeWorkerInstance)
            .order_by(RuntimeWorkerInstance.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if worker_definition_key is not None:
            statement = statement.where(
                RuntimeWorkerInstance.worker_definition_key == worker_definition_key
            )
        if workspace_id is not None:
            statement = statement.where(RuntimeWorkerInstance.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(RuntimeWorkerInstance.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def mark_stale_workers(self, stale_before: datetime) -> list[RuntimeWorkerInstance]:
        statement: Select[tuple[RuntimeWorkerInstance]] = select(RuntimeWorkerInstance).where(
            RuntimeWorkerInstance.status.in_(
                [
                    RuntimeWorkerInstanceStatus.STARTING.value,
                    RuntimeWorkerInstanceStatus.RUNNING.value,
                    RuntimeWorkerInstanceStatus.UNKNOWN.value,
                ]
            ),
            RuntimeWorkerInstance.last_heartbeat_at.is_not(None),
            RuntimeWorkerInstance.last_heartbeat_at < stale_before,
        )
        result = await self.session.execute(statement)
        instances = list(result.scalars().all())
        for instance in instances:
            instance.status = RuntimeWorkerInstanceStatus.STALE.value
        await self.session.flush()
        return instances

    async def create_run_request(
        self,
        run_request: RuntimeWorkerRunRequest,
    ) -> RuntimeWorkerRunRequest:
        self.session.add(run_request)
        await self.session.flush()
        await self.session.refresh(run_request)
        return run_request

    async def get_run_request(self, request_id: UUID) -> RuntimeWorkerRunRequest | None:
        return await self.session.get(RuntimeWorkerRunRequest, request_id)

    async def update_run_request(
        self,
        run_request: RuntimeWorkerRunRequest,
    ) -> RuntimeWorkerRunRequest:
        await self.session.flush()
        await self.session.refresh(run_request)
        return run_request

    async def count_instances_by_status(self) -> dict[str, int]:
        statement = (
            select(RuntimeWorkerInstance.status, func.count())
            .group_by(RuntimeWorkerInstance.status)
            .set_label_style(SelectLabelStyle.LABEL_STYLE_NONE)
        )
        result = await self.session.execute(statement)
        return {str(status): int(count) for status, count in result.all()}

    async def count_run_requests_by_status(
        self,
        workspace_id: UUID | None = None,
    ) -> dict[str, int]:
        statement = select(RuntimeWorkerRunRequest.status, func.count()).group_by(
            RuntimeWorkerRunRequest.status
        )
        if workspace_id is not None:
            statement = statement.where(RuntimeWorkerRunRequest.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return {str(status): int(count) for status, count in result.all()}

    async def count_run_requests_by_worker(
        self,
        workspace_id: UUID | None = None,
    ) -> dict[str, dict[str, int]]:
        statement = select(
            RuntimeWorkerRunRequest.worker_definition_key,
            RuntimeWorkerRunRequest.status,
            func.count(),
        ).group_by(
            RuntimeWorkerRunRequest.worker_definition_key,
            RuntimeWorkerRunRequest.status,
        )
        if workspace_id is not None:
            statement = statement.where(RuntimeWorkerRunRequest.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        counts: dict[str, dict[str, int]] = {}
        for worker_key, status, count in result.all():
            worker_counts = counts.setdefault(str(worker_key), {})
            worker_counts[str(status)] = int(count)
        return counts


def request_is_active(status: str) -> bool:
    return status in {
        RuntimeRunRequestStatus.PENDING.value,
        RuntimeRunRequestStatus.RUNNING.value,
    }
