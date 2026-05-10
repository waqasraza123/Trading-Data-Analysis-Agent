from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.data_sources.models import DataSource
from app.modules.imports.models import ImportBatch
from app.modules.intelligence_catalog.indexer import IntelligenceCatalogIndexer
from app.modules.intelligence_catalog.models import (
    IntelligenceCatalogArtifactType,
    IntelligenceCatalogItem,
)
from app.modules.intelligence_catalog.repository import IntelligenceCatalogRepository
from app.modules.intelligence_catalog.schemas import (
    IntelligenceCatalogReindexRead,
    IntelligenceCatalogReindexRequest,
    IntelligenceCatalogRemoveRequest,
    IntelligenceCatalogSearchQuery,
    IntelligenceCatalogUpsert,
)
from app.modules.news.models import NewsEvent
from app.modules.outcomes.models import SignalOutcome
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendation,
    StrategyProfileDiagnosticRun,
)
from app.modules.reasoning.models import LlmReasoningRun
from app.modules.signals.models import Signal
from app.modules.strategy_profiles.models import StrategyProfile


class IntelligenceCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = IntelligenceCatalogRepository(session)
        self.indexer = IntelligenceCatalogIndexer(session)

    async def index_artifact(
        self,
        artifact_type: IntelligenceCatalogArtifactType,
        artifact_id: UUID,
    ) -> IntelligenceCatalogItem:
        payload = await self.indexer.build(artifact_type, artifact_id)
        if payload is None:
            raise AppError(404, "catalog_artifact_not_found", "Catalog artifact not found")
        item = await self.repository.upsert_catalog_item(payload)
        await self.session.commit()
        return item

    async def upsert_catalog_item(
        self,
        payload: IntelligenceCatalogUpsert,
    ) -> IntelligenceCatalogItem:
        item = await self.repository.upsert_catalog_item(payload)
        await self.session.commit()
        return item

    async def remove_catalog_item(self, payload: IntelligenceCatalogRemoveRequest) -> bool:
        removed = await self.repository.remove_catalog_item(
            workspace_id=payload.workspace_id,
            artifact_type=payload.artifact_type.value,
            artifact_id=payload.artifact_id,
        )
        await self.session.commit()
        return removed

    async def search_catalog(
        self,
        query: IntelligenceCatalogSearchQuery,
    ) -> list[IntelligenceCatalogItem]:
        return await self.repository.search_catalog(query)

    async def reindex_workspace(
        self,
        payload: IntelligenceCatalogReindexRequest,
    ) -> IntelligenceCatalogReindexRead:
        artifact_types = payload.artifact_types or list(IntelligenceCatalogArtifactType)
        indexed_count = 0
        skipped_count = 0
        for artifact_type in artifact_types:
            ids = await self.list_workspace_artifact_ids(
                workspace_id=payload.workspace_id,
                artifact_type=artifact_type,
                limit=payload.limit,
            )
            for artifact_id in ids:
                catalog_payload = await self.indexer.build(
                    artifact_type,
                    artifact_id,
                    workspace_id=payload.workspace_id,
                )
                if catalog_payload is None:
                    skipped_count += 1
                    continue
                await self.repository.upsert_catalog_item(catalog_payload)
                indexed_count += 1
        await self.session.commit()
        return IntelligenceCatalogReindexRead(
            workspace_id=payload.workspace_id,
            indexed_count=indexed_count,
            skipped_count=skipped_count,
            artifact_types=artifact_types,
        )

    async def get_catalog_item(self, item_id: UUID) -> IntelligenceCatalogItem:
        item = await self.repository.get_catalog_item(item_id)
        if item is None:
            raise AppError(404, "catalog_item_not_found", "Catalog item not found")
        return item

    async def get_by_artifact(
        self,
        workspace_id: UUID,
        artifact_type: IntelligenceCatalogArtifactType,
        artifact_id: UUID,
    ) -> IntelligenceCatalogItem:
        item = await self.repository.get_by_artifact(
            workspace_id=workspace_id,
            artifact_type=artifact_type.value,
            artifact_id=artifact_id,
        )
        if item is None:
            raise AppError(404, "catalog_item_not_found", "Catalog item not found")
        return item

    async def list_workspace_artifact_ids(
        self,
        workspace_id: UUID,
        artifact_type: IntelligenceCatalogArtifactType,
        limit: int,
    ) -> list[UUID]:
        if artifact_type == IntelligenceCatalogArtifactType.REPORT:
            return await self.list_report_subject_ids(workspace_id, limit)
        if artifact_type == IntelligenceCatalogArtifactType.OPERATOR_REVIEW:
            return await self.list_operator_review_ids(workspace_id, limit)
        mapping: dict[IntelligenceCatalogArtifactType, tuple[type, str | None]] = {
            IntelligenceCatalogArtifactType.ANALYSIS_RUN: (AnalysisRun, None),
            IntelligenceCatalogArtifactType.SCHEDULED_SCAN_RUN: (AnalysisRun, "scheduled_scan_run"),
            IntelligenceCatalogArtifactType.SIGNAL: (Signal, None),
            IntelligenceCatalogArtifactType.OUTCOME: (SignalOutcome, None),
            IntelligenceCatalogArtifactType.REASONING_RUN: (LlmReasoningRun, None),
            IntelligenceCatalogArtifactType.ACTION_PLAN: (ReasoningActionPlan, None),
            IntelligenceCatalogArtifactType.ACTION_ITEM: (ReasoningActionItem, None),
            IntelligenceCatalogArtifactType.NEWS_EVENT: (NewsEvent, None),
            IntelligenceCatalogArtifactType.CHART_SCREENSHOT_RUN: (ChartScreenshotRun, None),
            IntelligenceCatalogArtifactType.OPERATOR_REVIEW: (CalibrationRecommendation, None),
            IntelligenceCatalogArtifactType.QUALITY_RUN: (ImportBatch, None),
            IntelligenceCatalogArtifactType.DIAGNOSTIC_RUN: (StrategyProfileDiagnosticRun, None),
            IntelligenceCatalogArtifactType.DATASET_EXPORT: (ImportBatch, None),
            IntelligenceCatalogArtifactType.REPORT: (Signal, None),
            IntelligenceCatalogArtifactType.RULE_MANIFEST: (StrategyProfile, None),
            IntelligenceCatalogArtifactType.PROVIDER_POLLING_REQUEST: (
                DataSource,
                "provider_polling_request",
            ),
        }
        model, selector = mapping[artifact_type]
        if artifact_type == IntelligenceCatalogArtifactType.RULE_MANIFEST:
            result = await self.session.execute(select(StrategyProfile.id).limit(limit))
            return list(result.scalars().all())
        return await self.repository.list_artifact_ids(model, workspace_id, limit, selector)

    async def list_report_subject_ids(self, workspace_id: UUID, limit: int) -> list[UUID]:
        subject_models = [Signal, AnalysisRun, LlmReasoningRun, SignalOutcome, ChartScreenshotRun]
        subject_ids: list[UUID] = []
        remaining = limit
        for model in subject_models:
            if remaining <= 0:
                break
            result = await self.session.execute(
                select(model.id).where(model.workspace_id == workspace_id).limit(remaining)
            )
            ids = list(result.scalars().all())
            subject_ids.extend(ids)
            remaining -= len(ids)
        return subject_ids

    async def list_operator_review_ids(self, workspace_id: UUID, limit: int) -> list[UUID]:
        result = await self.session.execute(
            select(CalibrationRecommendation.id)
            .where(CalibrationRecommendation.workspace_id == workspace_id)
            .limit(limit)
        )
        review_ids = list(result.scalars().all())
        remaining = limit - len(review_ids)
        if remaining <= 0:
            return review_ids
        result = await self.session.execute(
            select(ReasoningActionItem.id)
            .where(
                ReasoningActionItem.workspace_id == workspace_id,
                ReasoningActionItem.action_type == "request_human_review",
            )
            .limit(remaining)
        )
        review_ids.extend(result.scalars().all())
        return review_ids
