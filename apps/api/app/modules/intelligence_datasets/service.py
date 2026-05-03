import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.intelligence_datasets.models import (
    IntelligenceDatasetExport,
    IntelligenceDatasetExportFormat,
    IntelligenceDatasetExportItem,
    IntelligenceDatasetExportStatus,
)
from app.modules.intelligence_datasets.repository import IntelligenceDatasetRepository
from app.modules.intelligence_datasets.schemas import IntelligenceDatasetExportCreate


class IntelligenceDatasetService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = IntelligenceDatasetRepository(session)

    async def create_export(self, request: IntelligenceDatasetExportCreate) -> IntelligenceDatasetExport:
        limit = request.limit or self.settings.intelligence_dataset_default_limit
        limit = min(limit, self.settings.intelligence_dataset_max_limit)
        signals = await self.repository.list_signals(
            workspace_id=request.workspace_id,
            limit=limit,
            symbol_id=request.filters.symbol_id,
            timeframe=request.filters.timeframe,
            strategy_profile_key=request.filters.strategy_profile_key,
            start_time=request.filters.start_time,
            end_time=request.filters.end_time,
        )
        items = [
            IntelligenceDatasetExportItem(
                workspace_id=request.workspace_id,
                export_id=request.workspace_id,
                sequence_number=index + 1,
                signal_id=signal.id,
                analysis_run_id=signal.analysis_run_id,
                item_json=redacted_signal_item(signal, self.settings),
                redaction_json={"rawImagesIncluded": False, "fullCandleSeriesIncluded": False},
            )
            for index, signal in enumerate(signals)
        ]
        export = await self.repository.create_export(
            IntelligenceDatasetExport(
                workspace_id=request.workspace_id,
                status=IntelligenceDatasetExportStatus.COMPLETED.value,
                export_format=IntelligenceDatasetExportFormat.JSONL.value,
                schema_version=self.settings.intelligence_dataset_schema_version,
                filters_json=request.filters.model_dump(mode="json", exclude_none=True),
                redaction_policy_json={
                    "secretsIncluded": False,
                    "rawImagesIncluded": False,
                    "fullCandleSeriesIncluded": False,
                    "maxTextLength": self.settings.intelligence_dataset_max_text_length,
                },
                requested_limit=limit,
                item_count=len(items),
                summary_json={"itemCount": len(items)},
            ),
            items,
        )
        await self.session.commit()
        return export

    async def list_exports(self, workspace_id: UUID, limit: int, offset: int) -> list[IntelligenceDatasetExport]:
        return await self.repository.list_exports(workspace_id, limit, offset)

    async def get_export(self, export_id: UUID) -> IntelligenceDatasetExport:
        export = await self.repository.get_export(export_id)
        if export is None:
            raise AppError(404, "intelligence_dataset_export_not_found", "Dataset export not found")
        return export

    async def list_items(self, export_id: UUID, limit: int, offset: int) -> list[IntelligenceDatasetExportItem]:
        await self.get_export(export_id)
        return await self.repository.list_items(export_id, limit, offset)

    async def export_jsonl(self, export_id: UUID) -> str:
        items = await self.list_items(export_id, self.settings.intelligence_dataset_max_limit, 0)
        return "\n".join(json.dumps(item.item_json, sort_keys=True, default=str) for item in items)


def redacted_signal_item(signal: Any, settings: Settings) -> dict[str, object]:
    summary = str(signal.summary)
    if len(summary) > settings.intelligence_dataset_max_text_length:
        summary = f"{summary[: settings.intelligence_dataset_max_text_length]}..."
    return {
        "schemaVersion": settings.intelligence_dataset_schema_version,
        "signalId": str(signal.id),
        "analysisRunId": str(signal.analysis_run_id),
        "symbolId": str(signal.symbol_id),
        "timeframe": signal.timeframe,
        "classificationStatus": signal.classification_status,
        "bias": signal.bias,
        "patternType": signal.pattern_type,
        "confidenceScore": str(signal.confidence_score),
        "strategyProfileKey": signal.strategy_profile_key,
        "summary": summary,
        "dataQualityLabel": None,
        "marketSessionLabel": None,
    }
