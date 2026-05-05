from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.time import utc_now
from app.modules.daily_briefs.models import DailyBriefRun
from app.modules.data_quality.models import DataQualityRun
from app.modules.provider_health.models import ProviderHealthSnapshot
from app.modules.read_models.models import (
    CommandCenterReadModel,
    DashboardSymbolReadModel,
    SignalCardReadModel,
)
from app.modules.read_models.repository import (
    CommandCenterArtifacts,
    SignalCardArtifacts,
    SymbolReadModelArtifacts,
)


class ReadModelBuilder:
    def build_symbol_model(
        self,
        artifacts: SymbolReadModelArtifacts,
        read_model_version: str,
    ) -> DashboardSymbolReadModel:
        memory = artifacts.market_memory
        signal = artifacts.latest_signal
        priority = artifacts.priority
        setup_context = artifacts.setup_context
        data_quality_label = (
            memory.data_quality_label
            if memory is not None
            else artifacts.data_quality.quality_label
            if artifacts.data_quality is not None
            else None
        )
        freshness_label = (
            memory.freshness_label
            if memory is not None
            else artifacts.provider_health.freshness_label
            if artifacts.provider_health is not None
            else None
        )
        warning_entries = self.symbol_warnings(artifacts)
        market_regime_label = (
            memory.market_regime_label
            if memory is not None and memory.market_regime_label is not None
            else artifacts.market_regime.trend_regime
            if artifacts.market_regime is not None
            else None
        )
        market_session_label = (
            memory.market_session_label
            if memory is not None and memory.market_session_label is not None
            else artifacts.market_session.session_label
            if artifacts.market_session is not None
            else None
        )
        summary_json = json_safe(
            {
                "sourceArtifacts": {
                    "marketMemoryId": memory.id if memory is not None else None,
                    "priorityScoreId": priority.id if priority is not None else None,
                    "setupContextId": setup_context.id if setup_context is not None else None,
                    "dataQualityRunId": artifacts.data_quality.id
                    if artifacts.data_quality is not None
                    else None,
                    "providerHealthSnapshotId": artifacts.provider_health.id
                    if artifacts.provider_health is not None
                    else None,
                    "marketRegimeId": artifacts.market_regime.id
                    if artifacts.market_regime is not None
                    else None,
                    "marketSessionId": artifacts.market_session.id
                    if artifacts.market_session is not None
                    else None,
                },
                "latestSignal": {
                    "id": signal.id if signal is not None else None,
                    "classificationStatus": signal.classification_status
                    if signal is not None
                    else None,
                    "summary": signal.summary if signal is not None else None,
                    "createdAt": signal.created_at if signal is not None else None,
                },
                "providerHealth": provider_health_summary(artifacts.provider_health),
                "dataQuality": data_quality_summary(artifacts.data_quality),
                "warnings": warning_entries,
            }
        )
        return DashboardSymbolReadModel(
            workspace_id=artifacts.workspace_id,
            symbol_id=artifacts.symbol_id,
            source_id=artifacts.source_id,
            timeframe=artifacts.timeframe,
            read_model_version=read_model_version,
            latest_final_candle_time=memory.latest_final_candle_time
            if memory is not None
            else None,
            freshness_label=freshness_label,
            data_quality_label=data_quality_label,
            latest_signal_id=signal.id if signal is not None else None,
            latest_bias=signal.bias
            if signal is not None
            else memory.latest_signal_bias
            if memory is not None
            else None,
            latest_pattern_type=signal.pattern_type
            if signal is not None
            else memory.latest_signal_pattern_type
            if memory is not None
            else None,
            latest_confidence_label=signal.confidence_label
            if signal is not None
            else memory.latest_signal_confidence_label
            if memory is not None
            else None,
            latest_priority_score=priority.priority_score if priority is not None else None,
            latest_priority_label=priority.priority_label if priority is not None else None,
            setup_quality_label=setup_context.setup_quality_label
            if setup_context is not None
            else None,
            market_regime_label=market_regime_label,
            market_session_label=market_session_label,
            pending_action_count=len(artifacts.action_items),
            warning_count=len(warning_entries),
            summary_json=summary_json,
        )

    def build_signal_card(
        self,
        artifacts: SignalCardArtifacts,
        read_model_version: str,
    ) -> SignalCardReadModel:
        signal = artifacts.signal
        memory = artifacts.market_memory
        priority = artifacts.priority
        setup_context = artifacts.setup_context
        readiness = artifacts.readiness
        data_quality_label = (
            memory.data_quality_label
            if memory is not None
            else artifacts.data_quality.quality_label
            if artifacts.data_quality is not None
            else None
        )
        freshness_label = (
            memory.freshness_label
            if memory is not None
            else artifacts.provider_health.freshness_label
            if artifacts.provider_health is not None
            else None
        )
        warning_entries = self.signal_warnings(artifacts)
        outcome_summary = json_safe(
            {
                "count": len(artifacts.outcomes),
                "latestByHorizon": [
                    {
                        "id": outcome.id,
                        "horizonMinutes": outcome.horizon_minutes,
                        "evaluationStatus": outcome.evaluation_status,
                        "outcomeLabel": outcome.outcome_label,
                        "movementQuality": outcome.movement_quality,
                        "updatedAt": outcome.updated_at,
                    }
                    for outcome in artifacts.outcomes[:8]
                ],
            }
        )
        evidence_summary = json_safe(
            {
                "count": len(artifacts.evidence),
                "items": [
                    {
                        "id": item.id,
                        "type": item.evidence_type,
                        "direction": item.direction,
                        "message": item.message,
                        "weight": item.weight,
                    }
                    for item in artifacts.evidence[:8]
                ],
            }
        )
        risk_summary = json_safe(
            {
                "count": len(artifacts.risk_notes),
                "items": [
                    {
                        "id": note.id,
                        "code": note.code,
                        "severity": note.severity,
                        "message": note.message,
                    }
                    for note in artifacts.risk_notes[:8]
                ],
            }
        )
        action_summary = json_safe(
            {
                "pendingCount": len(artifacts.action_items),
                "items": [
                    {
                        "id": item.id,
                        "actionType": item.action_type,
                        "status": item.status,
                        "priority": item.priority,
                        "dueAt": item.due_at,
                        "horizonMinutes": item.horizon_minutes,
                    }
                    for item in artifacts.action_items[:8]
                ],
            }
        )
        warning_summary = json_safe(
            {
                "count": len(warning_entries),
                "items": warning_entries,
                "sourceArtifacts": {
                    "marketMemoryId": memory.id if memory is not None else None,
                    "priorityScoreId": priority.id if priority is not None else None,
                    "setupContextId": setup_context.id if setup_context is not None else None,
                    "readinessId": readiness.id if readiness is not None else None,
                    "dataQualityRunId": artifacts.data_quality.id
                    if artifacts.data_quality is not None
                    else None,
                    "providerHealthSnapshotId": artifacts.provider_health.id
                    if artifacts.provider_health is not None
                    else None,
                    "marketRegimeId": artifacts.market_regime.id
                    if artifacts.market_regime is not None
                    else None,
                    "marketSessionId": artifacts.market_session.id
                    if artifacts.market_session is not None
                    else None,
                },
                "marketContext": {
                    "regimeLabel": artifacts.market_regime.trend_regime
                    if artifacts.market_regime is not None
                    else memory.market_regime_label
                    if memory is not None
                    else None,
                    "sessionLabel": artifacts.market_session.session_label
                    if artifacts.market_session is not None
                    else memory.market_session_label
                    if memory is not None
                    else None,
                },
            }
        )
        searchable_text = build_searchable_text(
            [
                signal.classification_status,
                signal.bias,
                signal.pattern_type,
                signal.confidence_label,
                signal.summary,
                priority.priority_label if priority is not None else None,
                priority.review_bucket if priority is not None else None,
                setup_context.setup_quality_label if setup_context is not None else None,
                freshness_label,
                data_quality_label,
                readiness.readiness_label if readiness is not None else None,
            ]
        )
        return SignalCardReadModel(
            workspace_id=signal.workspace_id,
            signal_id=signal.id,
            analysis_run_id=signal.analysis_run_id,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            read_model_version=read_model_version,
            classification_status=signal.classification_status,
            bias=signal.bias,
            pattern_type=signal.pattern_type,
            confidence_score=signal.confidence_score,
            confidence_label=signal.confidence_label,
            priority_score=priority.priority_score if priority is not None else None,
            priority_label=priority.priority_label if priority is not None else None,
            review_bucket=priority.review_bucket if priority is not None else None,
            setup_quality_label=setup_context.setup_quality_label
            if setup_context is not None
            else None,
            freshness_label=freshness_label,
            data_quality_label=data_quality_label,
            readiness_label=readiness.readiness_label if readiness is not None else None,
            outcome_summary_json=outcome_summary,
            evidence_summary_json=evidence_summary,
            risk_summary_json=risk_summary,
            action_summary_json=action_summary,
            warning_summary_json=warning_summary,
            searchable_text=searchable_text,
        )

    def build_command_center_model(
        self,
        artifacts: CommandCenterArtifacts,
        read_model_version: str,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> CommandCenterReadModel:
        stale_symbols = [
            item
            for item in artifacts.symbol_models
            if item.freshness_label in {"stale", "delayed", "no_data"}
        ]
        review_cards = [
            item
            for item in artifacts.signal_cards
            if item.review_bucket in {"review_required", "stale_or_data_issue", "conflicted"}
            or item.priority_label in {"urgent_review", "high", "stale"}
        ]
        warning_count = sum(item.warning_count for item in artifacts.symbol_models) + sum(
            int(item.warning_summary_json.get("count", 0)) for item in artifacts.signal_cards
        )
        summary_json = json_safe(
            {
                "signalCardCount": len(artifacts.signal_cards),
                "symbolStateCount": len(artifacts.symbol_models),
                "reviewRequiredCount": len(review_cards),
                "staleSymbolCount": len(stale_symbols),
                "warningCount": warning_count,
                "latestBriefId": artifacts.latest_brief.id
                if artifacts.latest_brief is not None
                else None,
                "latestBriefStatus": artifacts.latest_brief.status
                if artifacts.latest_brief is not None
                else None,
                "latestBriefGeneratedAt": artifacts.latest_brief.generated_at
                if artifacts.latest_brief is not None
                else None,
            }
        )
        sections_json = json_safe(
            {
                "brief": brief_summary(artifacts.latest_brief),
                "reviewFirst": [signal_card_summary(item) for item in review_cards[:20]],
                "symbols": [symbol_model_summary(item) for item in artifacts.symbol_models[:50]],
                "dataQuality": {
                    "staleOrDelayed": [symbol_model_summary(item) for item in stale_symbols[:20]],
                    "labels": count_labels(
                        item.data_quality_label
                        for item in artifacts.symbol_models
                        if item.data_quality_label
                    ),
                    "freshness": count_labels(
                        item.freshness_label
                        for item in artifacts.symbol_models
                        if item.freshness_label
                    ),
                },
                "priorityLabels": count_labels(
                    item.priority_label for item in artifacts.signal_cards if item.priority_label
                ),
                "reviewBuckets": count_labels(
                    item.review_bucket for item in artifacts.signal_cards if item.review_bucket
                ),
            }
        )
        return CommandCenterReadModel(
            workspace_id=artifacts.workspace_id,
            read_model_version=read_model_version,
            period_start=period_start,
            period_end=period_end,
            status="completed",
            summary_json=summary_json,
            sections_json=sections_json,
            warning_count=warning_count,
            generated_at=utc_now(),
        )

    def symbol_warnings(self, artifacts: SymbolReadModelArtifacts) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        memory = artifacts.market_memory
        if memory is None:
            warnings.append({"source": "market_memory", "label": "missing"})
        else:
            warnings.extend(memory.warnings_json[:20])
            if memory.freshness_label in {"stale", "delayed", "no_data"}:
                warnings.append({"source": "market_memory", "label": memory.freshness_label})
            if memory.data_quality_label in {"degraded", "poor", "insufficient", "unknown"}:
                warnings.append({"source": "market_memory", "label": memory.data_quality_label})
        if artifacts.provider_health is not None and artifacts.provider_health.status != "healthy":
            warnings.append(
                {
                    "source": "provider_health",
                    "label": artifacts.provider_health.status,
                    "summary": artifacts.provider_health.summary,
                }
            )
        if artifacts.data_quality is not None and artifacts.data_quality.quality_label not in {
            "strong",
            "acceptable",
        }:
            warnings.append(
                {
                    "source": "data_quality",
                    "label": artifacts.data_quality.quality_label,
                    "findingCount": artifacts.data_quality.finding_count,
                }
            )
        return json_safe(warnings)

    def signal_warnings(self, artifacts: SignalCardArtifacts) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        memory = artifacts.market_memory
        setup_context = artifacts.setup_context
        if memory is not None:
            warnings.extend(memory.warnings_json[:10])
        else:
            warnings.append({"source": "market_memory", "label": "missing"})
        if setup_context is not None:
            warnings.extend(setup_context.data_quality_warnings_json[:10])
            warnings.extend(setup_context.avoid_reasons_json[:10])
        if artifacts.readiness is not None:
            warnings.extend(artifacts.readiness.warnings_json[:10])
            warnings.extend(artifacts.readiness.blockers_json[:10])
        if artifacts.provider_health is not None and artifacts.provider_health.status != "healthy":
            warnings.append(
                {
                    "source": "provider_health",
                    "label": artifacts.provider_health.status,
                    "summary": artifacts.provider_health.summary,
                }
            )
        if artifacts.data_quality is not None and artifacts.data_quality.quality_label not in {
            "strong",
            "acceptable",
        }:
            warnings.append(
                {
                    "source": "data_quality",
                    "label": artifacts.data_quality.quality_label,
                    "findingCount": artifacts.data_quality.finding_count,
                }
            )
        return json_safe(warnings)


def provider_health_summary(snapshot: ProviderHealthSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return json_safe(
        {
            "id": snapshot.id,
            "status": snapshot.status,
            "freshnessLabel": snapshot.freshness_label,
            "latestFinalCandleTime": snapshot.latest_final_candle_time,
            "missingCandleCount": snapshot.missing_candle_count,
            "staleSeconds": snapshot.stale_seconds,
            "summary": snapshot.summary,
        }
    )


def data_quality_summary(run: DataQualityRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return json_safe(
        {
            "id": run.id,
            "status": run.status,
            "qualityLabel": run.quality_label,
            "qualityScore": run.quality_score,
            "findingCount": run.finding_count,
            "summary": run.summary_json,
        }
    )


def signal_card_summary(card: SignalCardReadModel) -> dict[str, Any]:
    return json_safe(
        {
            "signalId": card.signal_id,
            "analysisRunId": card.analysis_run_id,
            "symbolId": card.symbol_id,
            "timeframe": card.timeframe,
            "classificationStatus": card.classification_status,
            "bias": card.bias,
            "patternType": card.pattern_type,
            "confidenceLabel": card.confidence_label,
            "priorityScore": card.priority_score,
            "priorityLabel": card.priority_label,
            "reviewBucket": card.review_bucket,
            "setupQualityLabel": card.setup_quality_label,
            "freshnessLabel": card.freshness_label,
            "dataQualityLabel": card.data_quality_label,
            "readinessLabel": card.readiness_label,
            "updatedAt": card.updated_at,
        }
    )


def symbol_model_summary(model: DashboardSymbolReadModel) -> dict[str, Any]:
    return json_safe(
        {
            "symbolId": model.symbol_id,
            "sourceId": model.source_id,
            "timeframe": model.timeframe,
            "latestFinalCandleTime": model.latest_final_candle_time,
            "freshnessLabel": model.freshness_label,
            "dataQualityLabel": model.data_quality_label,
            "latestSignalId": model.latest_signal_id,
            "latestBias": model.latest_bias,
            "latestPatternType": model.latest_pattern_type,
            "latestConfidenceLabel": model.latest_confidence_label,
            "latestPriorityLabel": model.latest_priority_label,
            "setupQualityLabel": model.setup_quality_label,
            "marketRegimeLabel": model.market_regime_label,
            "marketSessionLabel": model.market_session_label,
            "pendingActionCount": model.pending_action_count,
            "warningCount": model.warning_count,
            "updatedAt": model.updated_at,
        }
    )


def brief_summary(brief: DailyBriefRun | None) -> dict[str, Any] | None:
    if brief is None:
        return None
    return json_safe(
        {
            "id": brief.id,
            "status": brief.status,
            "briefType": brief.brief_type,
            "periodStart": brief.period_start,
            "periodEnd": brief.period_end,
            "summary": brief.summary_json,
            "sections": brief.sections_json,
            "warningCount": len(brief.warnings_json),
            "generatedAt": brief.generated_at,
        }
    )


def count_labels(values: Iterable[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if value is None:
            continue
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_searchable_text(values: list[Any]) -> str:
    return " ".join(str(value) for value in values if value not in {None, ""})[:4000]


def json_safe(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return value
