from dataclasses import dataclass
from uuid import UUID

from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.intelligence_datasets.models import (
    IntelligenceDatasetSourceType,
    IntelligenceDatasetType,
)
from app.modules.intelligence_datasets.repository import IntelligenceDatasetRepository
from app.modules.intelligence_datasets.schemas import IntelligenceDatasetFilters
from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import Signal, SignalConfidenceComponent, SignalEvidence

DATASET_SCHEMA_VERSION = "v1"


@dataclass(frozen=True)
class DatasetBuildRecord:
    source_type: IntelligenceDatasetSourceType
    source_id: UUID
    record_key: str
    record_json: dict[str, object]


class IntelligenceDatasetBuilder:
    def __init__(self, repository: IntelligenceDatasetRepository) -> None:
        self.repository = repository

    async def build_records(
        self,
        workspace_id: UUID,
        dataset_type: IntelligenceDatasetType,
        filters: IntelligenceDatasetFilters,
    ) -> list[DatasetBuildRecord]:
        if dataset_type == IntelligenceDatasetType.SIGNAL_SUPERVISION:
            return await self.build_signal_supervision(workspace_id, filters)
        if dataset_type == IntelligenceDatasetType.OUTCOME_EVALUATION:
            return await self.build_outcome_evaluation(workspace_id, filters)
        if dataset_type == IntelligenceDatasetType.REASONING_GROUNDING:
            return await self.build_reasoning_grounding(workspace_id, filters)
        if dataset_type == IntelligenceDatasetType.QUALITY_REVIEW:
            return await self.build_quality_review(workspace_id, filters)
        if dataset_type == IntelligenceDatasetType.SCREENSHOT_REVIEW:
            return await self.build_screenshot_review(workspace_id, filters)
        return await self.build_mixed_intelligence(workspace_id, filters)

    async def build_signal_supervision(
        self,
        workspace_id: UUID,
        filters: IntelligenceDatasetFilters,
    ) -> list[DatasetBuildRecord]:
        signals = await self.repository.list_signals(
            workspace_id=workspace_id,
            limit=filters.limit,
            symbol_id=filters.symbol_id,
            timeframe=filters.timeframe,
            strategy_profile_key=filters.strategy_profile_key,
            pattern_type=filters.pattern_type,
            start_time=filters.start_time,
            end_time=filters.end_time,
        )
        records: list[DatasetBuildRecord] = []
        for signal in signals:
            records.append(
                DatasetBuildRecord(
                    source_type=IntelligenceDatasetSourceType.SIGNAL,
                    source_id=signal.id,
                    record_key=f"signal:{signal.id}",
                    record_json=await self.signal_supervision_record(signal),
                )
            )
        return records

    async def build_outcome_evaluation(
        self,
        workspace_id: UUID,
        filters: IntelligenceDatasetFilters,
    ) -> list[DatasetBuildRecord]:
        outcomes = await self.repository.list_outcomes(
            workspace_id=workspace_id,
            limit=filters.limit,
            symbol_id=filters.symbol_id,
            timeframe=filters.timeframe,
            strategy_profile_key=filters.strategy_profile_key,
            pattern_type=filters.pattern_type,
            start_time=filters.start_time,
            end_time=filters.end_time,
        )
        records: list[DatasetBuildRecord] = []
        for outcome in outcomes:
            records.append(
                DatasetBuildRecord(
                    source_type=IntelligenceDatasetSourceType.OUTCOME,
                    source_id=outcome.id,
                    record_key=f"outcome:{outcome.id}",
                    record_json=await self.outcome_evaluation_record(outcome),
                )
            )
        return records

    async def build_reasoning_grounding(
        self,
        workspace_id: UUID,
        filters: IntelligenceDatasetFilters,
    ) -> list[DatasetBuildRecord]:
        runs = await self.repository.list_reasoning_runs(
            workspace_id=workspace_id,
            limit=filters.limit,
            start_time=filters.start_time,
            end_time=filters.end_time,
        )
        records: list[DatasetBuildRecord] = []
        for run in runs:
            records.append(
                DatasetBuildRecord(
                    source_type=IntelligenceDatasetSourceType.REASONING_RUN,
                    source_id=run.id,
                    record_key=f"reasoning_run:{run.id}",
                    record_json=await self.reasoning_grounding_record(run),
                )
            )
        return records

    async def build_quality_review(
        self,
        workspace_id: UUID,
        filters: IntelligenceDatasetFilters,
    ) -> list[DatasetBuildRecord]:
        signals = await self.repository.list_signals(
            workspace_id=workspace_id,
            limit=filters.limit,
            symbol_id=filters.symbol_id,
            timeframe=filters.timeframe,
            strategy_profile_key=filters.strategy_profile_key,
            pattern_type=filters.pattern_type,
            start_time=filters.start_time,
            end_time=filters.end_time,
        )
        records: list[DatasetBuildRecord] = []
        for signal in signals:
            run = await self.repository.get_analysis_run(signal.analysis_run_id)
            if run is None:
                continue
            records.append(
                DatasetBuildRecord(
                    source_type=IntelligenceDatasetSourceType.QUALITY_RUN,
                    source_id=run.id,
                    record_key=f"quality_run:{run.id}",
                    record_json=await self.quality_review_record(run, signal),
                )
            )
        return records

    async def build_screenshot_review(
        self,
        workspace_id: UUID,
        filters: IntelligenceDatasetFilters,
    ) -> list[DatasetBuildRecord]:
        runs = await self.repository.list_chart_screenshot_runs(
            workspace_id=workspace_id,
            limit=filters.limit,
            symbol_id=filters.symbol_id,
            timeframe=filters.timeframe,
            start_time=filters.start_time,
            end_time=filters.end_time,
        )
        return [
            DatasetBuildRecord(
                source_type=IntelligenceDatasetSourceType.SCREENSHOT_DECISION,
                source_id=run.id,
                record_key=f"screenshot_decision:{run.id}",
                record_json=self.screenshot_review_record(run),
            )
            for run in runs
        ]

    async def build_mixed_intelligence(
        self,
        workspace_id: UUID,
        filters: IntelligenceDatasetFilters,
    ) -> list[DatasetBuildRecord]:
        per_type_limit = max(filters.limit // 5, 1)
        mixed_filters = filters.model_copy(update={"limit": per_type_limit})
        records: list[DatasetBuildRecord] = []
        records.extend(await self.build_signal_supervision(workspace_id, mixed_filters))
        records.extend(await self.build_outcome_evaluation(workspace_id, mixed_filters))
        records.extend(await self.build_reasoning_grounding(workspace_id, mixed_filters))
        records.extend(await self.build_quality_review(workspace_id, mixed_filters))
        records.extend(await self.build_screenshot_review(workspace_id, mixed_filters))
        return records[: filters.limit]

    async def signal_supervision_record(self, signal: Signal) -> dict[str, object]:
        evidence = await self.repository.list_signal_evidence(signal.id)
        components = await self.repository.list_confidence_components(signal.id)
        explanation = await self.repository.get_deterministic_explanation(signal.id)
        outcomes = await self.repository.list_signal_outcomes(signal.id)
        correlations = await self.repository.list_news_correlations(signal.id)
        llm_explanation = await self.repository.get_llm_explanation(signal.id)
        return {
            "recordType": IntelligenceDatasetType.SIGNAL_SUPERVISION.value,
            "signal": signal_summary(signal),
            "selectedProfile": {
                "strategyProfileKey": signal.strategy_profile_key,
                "strategyProfileVersion": signal.strategy_profile_version,
            },
            "patternType": signal.pattern_type,
            "evidence": [evidence_summary(item) for item in evidence],
            "confidenceComponents": [confidence_component_summary(item) for item in components],
            "deterministicExplanation": (
                {
                    "shortSummary": explanation.short_summary,
                    "evidenceSummary": explanation.evidence_summary,
                    "confidenceSummary": explanation.confidence_summary,
                    "riskSummary": explanation.risk_summary,
                    "safetyStatus": explanation.safety_status,
                }
                if explanation is not None
                else None
            ),
            "llmExplanationStatus": (
                {
                    "safetyStatus": llm_explanation.safety_status,
                    "groundingStatus": llm_explanation.grounding_status,
                    "blockedTerms": llm_explanation.blocked_terms_json,
                    "groundingIssues": llm_explanation.grounding_issues_json,
                }
                if llm_explanation is not None
                else None
            ),
            "outcomeLabels": [outcome_label_summary(item) for item in outcomes],
            "newsCorrelationSummary": [news_correlation_summary(item) for item in correlations],
            "rawCandlesIncluded": False,
        }

    async def outcome_evaluation_record(self, outcome: SignalOutcome) -> dict[str, object]:
        signal = await self.repository.get_signal(outcome.signal_id)
        return {
            "recordType": IntelligenceDatasetType.OUTCOME_EVALUATION.value,
            "signal": signal_summary(signal) if signal is not None else None,
            "outcome": outcome_summary(outcome),
            "symbolId": outcome.symbol_id,
            "timeframe": outcome.timeframe,
            "strategyProfileKey": outcome.strategy_profile_key,
            "strategyProfileVersion": outcome.strategy_profile_version,
            "patternType": outcome.pattern_type,
        }

    async def reasoning_grounding_record(self, run: LlmReasoningRun) -> dict[str, object]:
        scenarios = await self.repository.list_scenarios(run.id)
        return {
            "recordType": IntelligenceDatasetType.REASONING_GROUNDING.value,
            "reasoningRun": {
                "id": run.id,
                "workspaceId": run.workspace_id,
                "analysisRunId": run.analysis_run_id,
                "signalId": run.signal_id,
                "outcomeId": run.outcome_id,
                "sourceType": run.source_type,
                "provider": run.provider,
                "model": run.model,
                "promptVersion": run.prompt_version,
                "reasoningType": run.reasoning_type,
                "status": run.status,
                "safetyStatus": run.safety_status,
                "groundingStatus": run.grounding_status,
                "blockedTerms": run.blocked_terms_json,
                "groundingIssues": run.grounding_issues_json,
                "createdAt": run.created_at,
            },
            "inputSnapshotSummary": summarize_snapshot(run.input_snapshot_json),
            "scenarioHypotheses": [scenario_summary(item) for item in scenarios],
            "rawProviderPayloadIncluded": False,
            "outputTextIncluded": False,
        }

    async def quality_review_record(self, run: AnalysisRun, signal: Signal) -> dict[str, object]:
        feature_snapshot = await self.repository.get_feature_snapshot(run.id)
        indicator_snapshot = await self.repository.get_indicator_snapshot(run.id)
        audit_logs = await self.repository.list_audit_logs(run.id, 50)
        return {
            "recordType": IntelligenceDatasetType.QUALITY_REVIEW.value,
            "analysisRun": {
                "id": run.id,
                "workspaceId": run.workspace_id,
                "symbolId": run.symbol_id,
                "timeframe": run.timeframe,
                "status": run.status,
                "analysisMode": run.analysis_mode,
                "startTime": run.start_time,
                "endTime": run.end_time,
                "engineVersion": run.engine_version,
                "ruleSetVersion": run.rule_set_version,
            },
            "qualityFindings": quality_findings(
                feature_snapshot.features_json if feature_snapshot else None
            ),
            "indicatorReadiness": summarize_snapshot(
                indicator_snapshot.indicators_json if indicator_snapshot else None
            ),
            "shadowClassificationResult": signal_summary(signal),
            "auditEvents": [audit_log_summary(item) for item in audit_logs],
            "rawCandlesIncluded": False,
        }

    def screenshot_review_record(self, run: ChartScreenshotRun) -> dict[str, object]:
        return {
            "recordType": IntelligenceDatasetType.SCREENSHOT_REVIEW.value,
            "screenshotRun": {
                "id": run.id,
                "workspaceId": run.workspace_id,
                "sourceId": run.source_id,
                "symbolId": run.symbol_id,
                "analysisRunId": run.analysis_run_id,
                "timeframe": run.timeframe,
                "fileName": run.file_name,
                "parserName": run.parser_name,
                "parserVersion": run.parser_version,
                "status": run.status,
                "extractionConfidence": run.extraction_confidence,
                "rawCandleCount": run.raw_candle_count,
                "storedCandleCount": run.stored_candle_count,
                "analysisHypothesis": run.analysis_hypothesis,
                "analysisHypothesisConfidence": run.analysis_hypothesis_confidence,
                "createdAt": run.created_at,
            },
            "extractionWarnings": run.extraction_warnings_json,
            "parserMetadataSummary": summarize_snapshot(run.parser_metadata_json),
            "humanCorrectionLineage": {
                "correctedFromRunId": run.parser_metadata_json.get(
                    "correctedFromChartScreenshotRunId"
                ),
                "humanReview": run.parser_metadata_json.get("humanReview"),
            },
            "rawImageBytesIncluded": False,
            "rawCandleSeriesIncluded": False,
        }


def signal_summary(signal: Signal) -> dict[str, object]:
    return {
        "signalId": signal.id,
        "analysisRunId": signal.analysis_run_id,
        "workspaceId": signal.workspace_id,
        "symbolId": signal.symbol_id,
        "timeframe": signal.timeframe,
        "strategyProfileKey": signal.strategy_profile_key,
        "strategyProfileVersion": signal.strategy_profile_version,
        "patternType": signal.pattern_type,
        "bias": signal.bias,
        "classificationStatus": signal.classification_status,
        "confidenceScore": signal.confidence_score,
        "confidenceLabel": signal.confidence_label,
        "summary": signal.summary,
        "noSignalReason": signal.no_signal_reason,
    }


def evidence_summary(item: SignalEvidence) -> dict[str, object]:
    return {
        "evidenceType": item.evidence_type,
        "direction": item.direction,
        "message": item.message,
        "numericValue": item.numeric_value,
        "weight": item.weight,
        "metadata": item.metadata_json,
    }


def confidence_component_summary(item: SignalConfidenceComponent) -> dict[str, object]:
    return {
        "componentName": item.component_name,
        "componentScore": item.component_score,
        "componentWeight": item.component_weight,
        "weightedScore": item.weighted_score,
        "reason": item.reason,
    }


def outcome_label_summary(item: SignalOutcome) -> dict[str, object]:
    return {
        "horizonMinutes": item.horizon_minutes,
        "evaluationStatus": item.evaluation_status,
        "outcomeLabel": item.outcome_label,
        "directionFollowed": item.direction_followed,
        "reversalDetected": item.reversal_detected,
        "movementQuality": item.movement_quality,
    }


def outcome_summary(item: SignalOutcome) -> dict[str, object]:
    return {
        "outcomeId": item.id,
        "signalId": item.signal_id,
        "analysisRunId": item.analysis_run_id,
        "horizonMinutes": item.horizon_minutes,
        "evaluationStatus": item.evaluation_status,
        "referenceTime": item.reference_time,
        "futureWindowStart": item.future_window_start,
        "futureWindowEnd": item.future_window_end,
        "futureCandleCount": item.future_candle_count,
        "maxFavorableMove": item.max_favorable_move,
        "maxAdverseMove": item.max_adverse_move,
        "netMove": item.net_move,
        "maxFavorablePips": item.max_favorable_pips,
        "maxAdversePips": item.max_adverse_pips,
        "netPips": item.net_pips,
        "maxFavorableTicks": item.max_favorable_ticks,
        "maxAdverseTicks": item.max_adverse_ticks,
        "netTicks": item.net_ticks,
        "directionFollowed": item.direction_followed,
        "reversalDetected": item.reversal_detected,
        "outcomeLabel": item.outcome_label,
        "movementQuality": item.movement_quality,
        "evaluationVersion": item.evaluation_version,
    }


def news_correlation_summary(item: SignalNewsCorrelation) -> dict[str, object]:
    return {
        "correlationLabel": item.correlation_label,
        "correlationScore": item.correlation_score,
        "directionAlignment": item.direction_alignment,
        "volatilityReaction": item.volatility_reaction,
        "timeDeltaMinutes": item.time_delta_minutes,
        "reason": item.reason,
    }


def scenario_summary(item: ScenarioHypothesis) -> dict[str, object]:
    return {
        "scenarioType": item.scenario_type,
        "scenarioLabel": item.scenario_label,
        "possibilityLabel": item.possibility_label,
        "supportingEvidence": item.supporting_evidence_json,
        "conflictingEvidence": item.conflicting_evidence_json,
        "outcomeHistory": item.outcome_history_json,
        "nextObservations": item.next_observations_json,
        "suggestedBackendActions": item.suggested_backend_actions_json,
        "riskNotes": item.risk_notes_json,
        "sortOrder": item.sort_order,
    }


def audit_log_summary(item: AnalysisAuditLog) -> dict[str, object]:
    return {
        "eventType": item.event_type,
        "message": item.message,
        "metadata": item.metadata_json,
        "createdAt": item.created_at,
    }


def quality_findings(features: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(features, dict):
        return {"present": False}
    return {
        "present": True,
        "dataQuality": features.get("dataQuality"),
        "volatility": summarize_snapshot(features.get("volatility")),
        "range": summarize_snapshot(features.get("range")),
        "trend": summarize_snapshot(features.get("trend")),
    }


def summarize_snapshot(value: object) -> object:
    if isinstance(value, dict):
        return {key: summarize_snapshot(child) for key, child in list(value.items())[:20]}
    if isinstance(value, list):
        return [summarize_snapshot(item) for item in value[:20]]
    return value
