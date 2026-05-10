from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.intelligence_catalog.models import IntelligenceCatalogItem
from app.modules.intelligence_catalog.schemas import (
    IntelligenceCatalogSearchQuery,
    IntelligenceCatalogUpsert,
)


class IntelligenceCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_catalog_item(self, item_id: UUID) -> IntelligenceCatalogItem | None:
        return await self.session.get(IntelligenceCatalogItem, item_id)

    async def get_by_artifact(
        self,
        workspace_id: UUID,
        artifact_type: str,
        artifact_id: UUID,
    ) -> IntelligenceCatalogItem | None:
        statement: Select[tuple[IntelligenceCatalogItem]] = select(IntelligenceCatalogItem).where(
            IntelligenceCatalogItem.workspace_id == workspace_id,
            IntelligenceCatalogItem.artifact_type == artifact_type,
            IntelligenceCatalogItem.artifact_id == artifact_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_catalog_item(
        self,
        payload: IntelligenceCatalogUpsert,
    ) -> IntelligenceCatalogItem:
        existing = await self.get_by_artifact(
            workspace_id=payload.workspace_id,
            artifact_type=payload.artifact_type.value,
            artifact_id=payload.artifact_id,
        )
        indexed_at = datetime.now(UTC)
        if existing is None:
            item = IntelligenceCatalogItem(
                workspace_id=payload.workspace_id,
                artifact_type=payload.artifact_type.value,
                artifact_id=payload.artifact_id,
                title=payload.title,
                summary=payload.summary,
                status=payload.status,
                symbol_id=payload.symbol_id,
                timeframe=payload.timeframe,
                strategy_profile_key=payload.strategy_profile_key,
                pattern_type=payload.pattern_type,
                bias=payload.bias,
                classification_status=payload.classification_status,
                quality_label=payload.quality_label,
                readiness_label=payload.readiness_label,
                outcome_label=payload.outcome_label,
                source_type=payload.source_type,
                tags_json=payload.tags_json,
                searchable_text=payload.searchable_text,
                metadata_json=payload.metadata_json,
                artifact_created_at=payload.artifact_created_at,
                indexed_at=indexed_at,
            )
            self.session.add(item)
            await self.session.flush()
            await self.session.refresh(item)
            return item
        existing.title = payload.title
        existing.summary = payload.summary
        existing.status = payload.status
        existing.symbol_id = payload.symbol_id
        existing.timeframe = payload.timeframe
        existing.strategy_profile_key = payload.strategy_profile_key
        existing.pattern_type = payload.pattern_type
        existing.bias = payload.bias
        existing.classification_status = payload.classification_status
        existing.quality_label = payload.quality_label
        existing.readiness_label = payload.readiness_label
        existing.outcome_label = payload.outcome_label
        existing.source_type = payload.source_type
        existing.tags_json = payload.tags_json
        existing.searchable_text = payload.searchable_text
        existing.metadata_json = payload.metadata_json
        existing.artifact_created_at = payload.artifact_created_at
        existing.indexed_at = indexed_at
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def remove_catalog_item(
        self,
        workspace_id: UUID,
        artifact_type: str,
        artifact_id: UUID,
    ) -> bool:
        result = await self.session.execute(
            delete(IntelligenceCatalogItem).where(
                IntelligenceCatalogItem.workspace_id == workspace_id,
                IntelligenceCatalogItem.artifact_type == artifact_type,
                IntelligenceCatalogItem.artifact_id == artifact_id,
            )
        )
        await self.session.flush()
        return bool(result.rowcount)

    async def search_catalog(
        self,
        query: IntelligenceCatalogSearchQuery,
    ) -> list[IntelligenceCatalogItem]:
        statement = self.apply_search_filters(
            select(IntelligenceCatalogItem).where(
                IntelligenceCatalogItem.workspace_id == query.workspace_id
            ),
            query,
        )
        statement = (
            statement.order_by(
                IntelligenceCatalogItem.artifact_created_at.desc().nullslast(),
                IntelligenceCatalogItem.indexed_at.desc(),
            )
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_artifact_ids(
        self,
        model: type,
        workspace_id: UUID,
        limit: int,
        artifact_type: str | None = None,
    ) -> list[UUID]:
        statement = select(model.id).where(model.workspace_id == workspace_id).limit(limit)
        if artifact_type == "scheduled_scan_run":
            statement = statement.where(model.analysis_mode == "scheduled_scan")
        if artifact_type == "provider_polling_request":
            statement = statement.where(model.source_type == "api_polling")
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    def apply_search_filters(
        self,
        statement: Select[tuple[IntelligenceCatalogItem]],
        query: IntelligenceCatalogSearchQuery,
    ) -> Select[tuple[IntelligenceCatalogItem]]:
        if query.artifact_types:
            statement = statement.where(
                IntelligenceCatalogItem.artifact_type.in_(
                    [artifact_type.value for artifact_type in query.artifact_types]
                )
            )
        if query.status is not None:
            statement = statement.where(IntelligenceCatalogItem.status == query.status)
        if query.symbol_id is not None:
            statement = statement.where(IntelligenceCatalogItem.symbol_id == query.symbol_id)
        if query.timeframe is not None:
            statement = statement.where(IntelligenceCatalogItem.timeframe == query.timeframe)
        if query.strategy_profile_key is not None:
            statement = statement.where(
                IntelligenceCatalogItem.strategy_profile_key == query.strategy_profile_key
            )
        if query.pattern_type is not None:
            statement = statement.where(IntelligenceCatalogItem.pattern_type == query.pattern_type)
        if query.bias is not None:
            statement = statement.where(IntelligenceCatalogItem.bias == query.bias)
        if query.outcome_label is not None:
            statement = statement.where(
                IntelligenceCatalogItem.outcome_label == query.outcome_label
            )
        if query.source_type is not None:
            statement = statement.where(IntelligenceCatalogItem.source_type == query.source_type)
        if query.start_time is not None:
            statement = statement.where(
                or_(
                    IntelligenceCatalogItem.artifact_created_at >= query.start_time,
                    IntelligenceCatalogItem.indexed_at >= query.start_time,
                )
            )
        if query.end_time is not None:
            statement = statement.where(
                or_(
                    IntelligenceCatalogItem.artifact_created_at <= query.end_time,
                    IntelligenceCatalogItem.indexed_at <= query.end_time,
                )
            )
        if query.tags:
            for tag in query.tags:
                statement = statement.where(IntelligenceCatalogItem.tags_json.contains([tag]))
        if query.query is not None:
            like_query = f"%{query.query.lower()}%"
            statement = statement.where(
                func.lower(IntelligenceCatalogItem.searchable_text).ilike(like_query)
            )
        return statement
