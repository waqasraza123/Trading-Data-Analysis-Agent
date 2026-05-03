from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.capabilities.models import IntelligenceCapability


class CapabilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, capability: IntelligenceCapability) -> IntelligenceCapability:
        self.session.add(capability)
        await self.session.flush()
        await self.session.refresh(capability)
        return capability

    async def get_by_key_version(
        self,
        key: str,
        version: str,
    ) -> IntelligenceCapability | None:
        statement: Select[tuple[IntelligenceCapability]] = select(IntelligenceCapability).where(
            IntelligenceCapability.key == key,
            IntelligenceCapability.version == version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_by_key(self, key: str) -> IntelligenceCapability | None:
        statement: Select[tuple[IntelligenceCapability]] = (
            select(IntelligenceCapability)
            .where(IntelligenceCapability.key == key)
            .order_by(IntelligenceCapability.version.desc())
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_capabilities(
        self,
        category: str | None = None,
        status: str | None = None,
        execution_type: str | None = None,
        safety_level: str | None = None,
        requires_external_credentials: bool | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[IntelligenceCapability]:
        statement: Select[tuple[IntelligenceCapability]] = select(IntelligenceCapability)
        if category is not None:
            statement = statement.where(IntelligenceCapability.category == category)
        if status is not None:
            statement = statement.where(IntelligenceCapability.status == status)
        if execution_type is not None:
            statement = statement.where(IntelligenceCapability.execution_type == execution_type)
        if safety_level is not None:
            statement = statement.where(IntelligenceCapability.safety_level == safety_level)
        if requires_external_credentials is not None:
            statement = statement.where(
                IntelligenceCapability.requires_external_credentials.is_(
                    requires_external_credentials
                )
            )
        statement = (
            statement.order_by(IntelligenceCapability.category.asc(), IntelligenceCapability.key.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def upsert_defaults(
        self,
        capabilities: Sequence[IntelligenceCapability],
    ) -> list[IntelligenceCapability]:
        stored_capabilities: list[IntelligenceCapability] = []
        for capability in capabilities:
            existing = await self.get_by_key_version(capability.key, capability.version)
            if existing is None:
                stored_capabilities.append(await self.create(capability))
                continue
            existing.name = capability.name
            existing.category = capability.category
            existing.execution_type = capability.execution_type
            existing.safety_level = capability.safety_level
            existing.requires_external_credentials = capability.requires_external_credentials
            existing.requires_database = capability.requires_database
            existing.input_contracts_json = capability.input_contracts_json
            existing.output_contracts_json = capability.output_contracts_json
            existing.produced_artifacts_json = capability.produced_artifacts_json
            existing.route_refs_json = capability.route_refs_json
            existing.dependencies_json = capability.dependencies_json
            existing.metadata_json = capability.metadata_json
            if existing.status not in {"disabled", "deprecated"}:
                existing.status = capability.status
            stored_capabilities.append(existing)
        await self.session.flush()
        for capability in stored_capabilities:
            await self.session.refresh(capability)
        return stored_capabilities

    async def update_status(
        self,
        capability: IntelligenceCapability,
        status: str,
    ) -> IntelligenceCapability:
        capability.status = status
        await self.session.flush()
        await self.session.refresh(capability)
        return capability

    async def count_by_field(self, field_name: str) -> dict[str, int]:
        column = getattr(IntelligenceCapability, field_name)
        statement = select(column, func.count(IntelligenceCapability.id)).group_by(column)
        result = await self.session.execute(statement)
        return {str(key): int(count) for key, count in result.all()}

    async def count_total(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(IntelligenceCapability)
        )
        return int(result.scalar_one())
