from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.outcomes.models import SignalOutcome
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendation,
    PatternOutcomeDiagnostic,
    StrategyProfileDiagnostic,
)
from app.modules.reasoning.models import ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.symbols.models import Symbol
from app.modules.webhook_outbox.models import WebhookEventType
from app.modules.webhook_outbox.redaction import sanitize_payload
from app.modules.webhook_outbox.repository import WebhookOutboxRepository

ALLOWED_SOURCE_TYPES_BY_EVENT = {
    WebhookEventType.SIGNAL_CLASSIFIED: {"signal"},
    WebhookEventType.OUTCOME_EVALUATED: {"outcome"},
    WebhookEventType.REASONING_SCENARIOS_GENERATED: {"reasoning_run"},
    WebhookEventType.ACTION_PLAN_CREATED: {"action_plan"},
    WebhookEventType.ACTION_ITEM_COMPLETED: {"action_item"},
    WebhookEventType.ACTION_ITEM_FAILED: {"action_item"},
    WebhookEventType.QUALITY_FINDING_CREATED: {
        "strategy_profile_diagnostic",
        "pattern_outcome_diagnostic",
        "calibration_recommendation",
    },
    WebhookEventType.READINESS_BLOCKED: {"analysis_run", "screenshot_decision", "action_item"},
    WebhookEventType.OPERATOR_REVIEW_OPENED: {"action_item", "screenshot_decision"},
}


class WebhookPayloadBuilder:
    def __init__(self, repository: WebhookOutboxRepository) -> None:
        self.repository = repository

    async def build_payload(
        self,
        workspace_id: UUID,
        event_type: WebhookEventType,
        source_type: str,
        source_id: UUID,
    ) -> tuple[dict[str, object], list[str]]:
        self.validate_source_type(event_type, source_type)
        payload = await self.build_raw_payload(workspace_id, event_type, source_type, source_id)
        sanitized_payload, warnings = sanitize_payload(payload)
        return sanitized_payload, warnings

    def validate_source_type(self, event_type: WebhookEventType, source_type: str) -> None:
        allowed_source_types = ALLOWED_SOURCE_TYPES_BY_EVENT[event_type]
        if source_type not in allowed_source_types:
            raise AppError(
                422,
                "webhook_source_type_not_allowed",
                "Source type is not allowed for this webhook event type",
            )

    async def build_raw_payload(
        self,
        workspace_id: UUID,
        event_type: WebhookEventType,
        source_type: str,
        source_id: UUID,
    ) -> dict[str, object]:
        base = self.base_payload(workspace_id, event_type, source_type, source_id)
        if event_type == WebhookEventType.SIGNAL_CLASSIFIED:
            return base | {"artifact": await self.signal_artifact(workspace_id, source_id)}
        if event_type == WebhookEventType.OUTCOME_EVALUATED:
            return base | {"artifact": await self.outcome_artifact(workspace_id, source_id)}
        if event_type == WebhookEventType.REASONING_SCENARIOS_GENERATED:
            return base | {"artifact": await self.reasoning_artifact(workspace_id, source_id)}
        if event_type == WebhookEventType.ACTION_PLAN_CREATED:
            return base | {"artifact": await self.action_plan_artifact(workspace_id, source_id)}
        if event_type in {
            WebhookEventType.ACTION_ITEM_COMPLETED,
            WebhookEventType.ACTION_ITEM_FAILED,
        }:
            return base | {"artifact": await self.action_item_artifact(workspace_id, source_id)}
        if event_type == WebhookEventType.QUALITY_FINDING_CREATED:
            return base | {
                "artifact": await self.quality_finding_artifact(
                    workspace_id,
                    source_type,
                    source_id,
                )
            }
        if event_type == WebhookEventType.READINESS_BLOCKED:
            return base | {
                "artifact": await self.readiness_artifact(workspace_id, source_type, source_id)
            }
        if event_type == WebhookEventType.OPERATOR_REVIEW_OPENED:
            return base | {
                "artifact": await self.operator_review_artifact(
                    workspace_id,
                    source_type,
                    source_id,
                )
            }
        raise AppError(422, "unsupported_webhook_event_type", "Unsupported webhook event type")

    def base_payload(
        self,
        workspace_id: UUID,
        event_type: WebhookEventType,
        source_type: str,
        source_id: UUID,
    ) -> dict[str, object]:
        return {
            "eventType": event_type.value,
            "workspaceId": workspace_id,
            "generatedAt": utc_now(),
            "source": {"type": source_type, "id": source_id},
            "delivery": {"networkTransmissionIncluded": False},
            "safety": {
                "containsTradeInstructions": False,
                "containsSecrets": False,
                "rawImagesIncluded": False,
                "rawCandleSeriesIncluded": False,
            },
        }

    async def signal_artifact(self, workspace_id: UUID, signal_id: UUID) -> dict[str, object]:
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        self.ensure_workspace(workspace_id, signal.workspace_id)
        symbol = await self.repository.get_symbol(signal.symbol_id)
        evidence = await self.repository.list_signal_evidence(signal.id)
        components = await self.repository.list_signal_confidence_components(signal.id)
        risk_notes = await self.repository.list_signal_risk_notes(signal.id)
        return {
            "signal": self.signal_row(signal, symbol),
            "confidenceComponents": [
                self.confidence_component_row(component) for component in components[:20]
            ],
            "evidence": [self.evidence_row(item) for item in evidence[:20]],
            "riskNotes": [self.risk_note_row(item) for item in risk_notes[:20]],
            "links": {"signalReport": f"/intelligence-reports/signals/{signal.id}"},
        }

    async def outcome_artifact(self, workspace_id: UUID, outcome_id: UUID) -> dict[str, object]:
        outcome = await self.repository.get_outcome(outcome_id)
        if outcome is None:
            raise AppError(404, "outcome_not_found", "Outcome not found")
        self.ensure_workspace(workspace_id, outcome.workspace_id)
        return {
            "outcome": self.outcome_row(outcome),
            "links": {
                "outcomeReport": f"/intelligence-reports/outcomes/{outcome.id}",
                "signalOutcomeReport": (
                    f"/intelligence-reports/signals/{outcome.signal_id}/outcomes"
                ),
            },
        }

    async def reasoning_artifact(
        self,
        workspace_id: UUID,
        reasoning_run_id: UUID,
    ) -> dict[str, object]:
        reasoning_run = await self.repository.get_reasoning_run(reasoning_run_id)
        if reasoning_run is None:
            raise AppError(404, "reasoning_run_not_found", "Reasoning run not found")
        self.ensure_workspace(workspace_id, reasoning_run.workspace_id)
        scenarios = await self.repository.list_scenarios(reasoning_run.id)
        safe_summary = None
        if reasoning_run.safety_status in {"passed", "fallback_used"} and isinstance(
            reasoning_run.output_json,
            dict,
        ):
            safe_summary = reasoning_run.output_json.get("summary")
        return {
            "reasoningRun": {
                "id": reasoning_run.id,
                "analysisRunId": reasoning_run.analysis_run_id,
                "signalId": reasoning_run.signal_id,
                "outcomeId": reasoning_run.outcome_id,
                "sourceType": reasoning_run.source_type,
                "reasoningType": reasoning_run.reasoning_type,
                "status": reasoning_run.status,
                "safetyStatus": reasoning_run.safety_status,
                "groundingStatus": reasoning_run.grounding_status,
                "outputSummary": safe_summary,
                "unsafeOutputIncluded": False,
                "createdAt": reasoning_run.created_at,
                "updatedAt": reasoning_run.updated_at,
            },
            "scenarios": [self.scenario_row(scenario) for scenario in scenarios[:20]],
            "links": {
                "reasoningReport": f"/intelligence-reports/reasoning-runs/{reasoning_run.id}"
            },
        }

    async def action_plan_artifact(
        self,
        workspace_id: UUID,
        action_plan_id: UUID,
    ) -> dict[str, object]:
        action_plan = await self.repository.get_action_plan(action_plan_id)
        if action_plan is None:
            raise AppError(404, "action_plan_not_found", "Action plan not found")
        self.ensure_workspace(workspace_id, action_plan.workspace_id)
        items = await self.repository.list_action_items(action_plan.id)
        return {
            "actionPlan": self.action_plan_row(action_plan),
            "actionItems": [self.action_item_row(item) for item in items[:50]],
            "links": {"actionPlan": f"/action-plans/{action_plan.id}"},
        }

    async def action_item_artifact(
        self,
        workspace_id: UUID,
        action_item_id: UUID,
    ) -> dict[str, object]:
        item = await self.repository.get_action_item(action_item_id)
        if item is None:
            raise AppError(404, "action_item_not_found", "Action item not found")
        self.ensure_workspace(workspace_id, item.workspace_id)
        return {
            "actionItem": self.action_item_row(item),
            "links": {
                "actionPlan": f"/action-plans/{item.action_plan_id}",
                "actionItems": f"/action-plans/{item.action_plan_id}/items",
            },
        }

    async def quality_finding_artifact(
        self,
        workspace_id: UUID,
        source_type: str,
        source_id: UUID,
    ) -> dict[str, object]:
        if source_type == "strategy_profile_diagnostic":
            diagnostic = await self.repository.get_strategy_profile_diagnostic(source_id)
            if diagnostic is None:
                raise AppError(404, "quality_finding_not_found", "Quality finding not found")
            self.ensure_workspace(workspace_id, diagnostic.workspace_id)
            return {"qualityFinding": self.strategy_profile_diagnostic_row(diagnostic)}
        if source_type == "pattern_outcome_diagnostic":
            diagnostic = await self.repository.get_pattern_outcome_diagnostic(source_id)
            if diagnostic is None:
                raise AppError(404, "quality_finding_not_found", "Quality finding not found")
            self.ensure_workspace(workspace_id, diagnostic.workspace_id)
            return {"qualityFinding": self.pattern_outcome_diagnostic_row(diagnostic)}
        recommendation = await self.repository.get_calibration_recommendation(source_id)
        if recommendation is None:
            raise AppError(404, "quality_finding_not_found", "Quality finding not found")
        self.ensure_workspace(workspace_id, recommendation.workspace_id)
        return {"qualityFinding": self.calibration_recommendation_row(recommendation)}

    async def readiness_artifact(
        self,
        workspace_id: UUID,
        source_type: str,
        source_id: UUID,
    ) -> dict[str, object]:
        if source_type == "analysis_run":
            run = await self.repository.get_analysis_run(source_id)
            if run is None:
                raise AppError(404, "readiness_source_not_found", "Readiness source not found")
            self.ensure_workspace(workspace_id, run.workspace_id)
            return {"readiness": self.analysis_run_readiness_row(run)}
        if source_type == "screenshot_decision":
            run = await self.repository.get_chart_screenshot_run(source_id)
            if run is None:
                raise AppError(404, "readiness_source_not_found", "Readiness source not found")
            self.ensure_workspace(workspace_id, run.workspace_id)
            return {"readiness": self.screenshot_readiness_row(run)}
        return {"readiness": await self.action_item_artifact(workspace_id, source_id)}

    async def operator_review_artifact(
        self,
        workspace_id: UUID,
        source_type: str,
        source_id: UUID,
    ) -> dict[str, object]:
        if source_type == "screenshot_decision":
            run = await self.repository.get_chart_screenshot_run(source_id)
            if run is None:
                raise AppError(404, "operator_review_source_not_found", "Review source not found")
            self.ensure_workspace(workspace_id, run.workspace_id)
            return {"operatorReview": self.screenshot_review_row(run)}
        return {"operatorReview": await self.action_item_artifact(workspace_id, source_id)}

    def ensure_workspace(self, requested_workspace_id: UUID, artifact_workspace_id: UUID) -> None:
        if requested_workspace_id != artifact_workspace_id:
            raise AppError(
                422,
                "webhook_source_workspace_mismatch",
                "Source artifact does not belong to the requested workspace",
            )

    def signal_row(self, signal: Signal, symbol: Symbol | None) -> dict[str, object]:
        return {
            "id": signal.id,
            "analysisRunId": signal.analysis_run_id,
            "symbolId": signal.symbol_id,
            "symbol": symbol.symbol if symbol is not None else None,
            "timeframe": signal.timeframe,
            "classificationStatus": signal.classification_status,
            "bias": signal.bias,
            "patternType": signal.pattern_type,
            "strategyProfileKey": signal.strategy_profile_key,
            "strategyProfileVersion": signal.strategy_profile_version,
            "confidenceScore": signal.confidence_score,
            "confidenceLabel": signal.confidence_label,
            "candidateStrength": signal.candidate_strength,
            "movementQuality": signal.movement_quality,
            "volatilityState": signal.volatility_state,
            "trendState": signal.trend_state,
            "rangeState": signal.range_state,
            "summary": signal.summary,
            "noSignalReason": signal.no_signal_reason,
            "createdAt": signal.created_at,
        }

    def evidence_row(self, item: SignalEvidence) -> dict[str, object]:
        return {
            "id": item.id,
            "type": item.evidence_type,
            "supportDirection": item.direction,
            "message": item.message,
            "numericValue": item.numeric_value,
            "weight": item.weight,
            "metadata": item.metadata_json,
            "createdAt": item.created_at,
        }

    def confidence_component_row(self, item: SignalConfidenceComponent) -> dict[str, object]:
        return {
            "id": item.id,
            "componentName": item.component_name,
            "componentScore": item.component_score,
            "componentWeight": item.component_weight,
            "weightedScore": item.weighted_score,
            "reason": item.reason,
            "createdAt": item.created_at,
        }

    def risk_note_row(self, item: SignalRiskNote) -> dict[str, object]:
        return {
            "id": item.id,
            "code": item.code,
            "severity": item.severity,
            "message": item.message,
            "metadata": item.metadata_json,
            "createdAt": item.created_at,
        }

    def outcome_row(self, outcome: SignalOutcome) -> dict[str, object]:
        return {
            "id": outcome.id,
            "analysisRunId": outcome.analysis_run_id,
            "signalId": outcome.signal_id,
            "symbolId": outcome.symbol_id,
            "timeframe": outcome.timeframe,
            "strategyProfileKey": outcome.strategy_profile_key,
            "patternType": outcome.pattern_type,
            "bias": outcome.bias,
            "classificationStatus": outcome.classification_status,
            "horizonMinutes": outcome.horizon_minutes,
            "evaluationStatus": outcome.evaluation_status,
            "outcomeLabel": outcome.outcome_label,
            "futureCandleCount": outcome.future_candle_count,
            "directionFollowed": outcome.direction_followed,
            "reversalDetected": outcome.reversal_detected,
            "movementQuality": outcome.movement_quality,
            "safeMetrics": {
                "maxFavorableMove": outcome.max_favorable_move,
                "maxAdverseMove": outcome.max_adverse_move,
                "netMove": outcome.net_move,
                "maxFavorablePips": outcome.max_favorable_pips,
                "maxAdversePips": outcome.max_adverse_pips,
                "netPips": outcome.net_pips,
                "maxFavorableTicks": outcome.max_favorable_ticks,
                "maxAdverseTicks": outcome.max_adverse_ticks,
                "netTicks": outcome.net_ticks,
            },
            "createdAt": outcome.created_at,
            "updatedAt": outcome.updated_at,
        }

    def scenario_row(self, scenario: ScenarioHypothesis) -> dict[str, object]:
        return {
            "id": scenario.id,
            "scenarioType": scenario.scenario_type,
            "scenarioLabel": scenario.scenario_label,
            "possibilityLabel": scenario.possibility_label,
            "supportingEvidence": scenario.supporting_evidence_json,
            "conflictingEvidence": scenario.conflicting_evidence_json,
            "outcomeHistory": scenario.outcome_history_json,
            "nextObservations": scenario.next_observations_json,
            "suggestedBackendActions": scenario.suggested_backend_actions_json,
            "riskNotes": scenario.risk_notes_json,
            "sortOrder": scenario.sort_order,
            "createdAt": scenario.created_at,
        }

    def action_plan_row(self, plan: ReasoningActionPlan) -> dict[str, object]:
        return {
            "id": plan.id,
            "sourceType": plan.source_type,
            "sourceId": plan.source_id,
            "signalId": plan.signal_id,
            "analysisRunId": plan.analysis_run_id,
            "reasoningRunId": plan.reasoning_run_id,
            "status": plan.status,
            "planVersion": plan.plan_version,
            "createdFrom": plan.created_from,
            "summary": plan.summary,
            "metadata": plan.metadata_json,
            "createdAt": plan.created_at,
            "updatedAt": plan.updated_at,
        }

    def action_item_row(self, item: ReasoningActionItem) -> dict[str, object]:
        return {
            "id": item.id,
            "actionPlanId": item.action_plan_id,
            "sourceType": item.source_type,
            "sourceId": item.source_id,
            "signalId": item.signal_id,
            "analysisRunId": item.analysis_run_id,
            "reasoningRunId": item.reasoning_run_id,
            "actionType": item.action_type,
            "status": item.status,
            "priority": item.priority,
            "dueAt": item.due_at,
            "horizonMinutes": item.horizon_minutes,
            "result": self.summarize_mapping(item.result_json),
            "errorCode": item.error_code,
            "errorMessage": item.error_message,
            "attempts": item.attempts,
            "maxAttempts": item.max_attempts,
            "completedAt": item.completed_at,
            "createdAt": item.created_at,
            "updatedAt": item.updated_at,
        }

    def strategy_profile_diagnostic_row(
        self,
        item: StrategyProfileDiagnostic,
    ) -> dict[str, object]:
        return {
            "id": item.id,
            "diagnosticRunId": item.diagnostic_run_id,
            "strategyProfileKey": item.strategy_profile_key,
            "strategyProfileVersion": item.strategy_profile_version,
            "symbolId": item.symbol_id,
            "timeframe": item.timeframe,
            "horizonMinutes": item.horizon_minutes,
            "sampleSize": item.sample_size,
            "evaluatedCount": item.evaluated_count,
            "diagnosticLabel": item.diagnostic_label,
            "diagnosticSummary": item.diagnostic_summary,
            "metadata": self.summarize_mapping(item.metadata_json),
            "createdAt": item.created_at,
        }

    def pattern_outcome_diagnostic_row(
        self,
        item: PatternOutcomeDiagnostic,
    ) -> dict[str, object]:
        return {
            "id": item.id,
            "diagnosticRunId": item.diagnostic_run_id,
            "patternType": item.pattern_type,
            "strategyProfileKey": item.strategy_profile_key,
            "symbolId": item.symbol_id,
            "timeframe": item.timeframe,
            "horizonMinutes": item.horizon_minutes,
            "sampleSize": item.sample_size,
            "evaluatedCount": item.evaluated_count,
            "diagnosticLabel": item.diagnostic_label,
            "diagnosticSummary": item.diagnostic_summary,
            "metadata": self.summarize_mapping(item.metadata_json),
            "createdAt": item.created_at,
        }

    def calibration_recommendation_row(
        self,
        item: CalibrationRecommendation,
    ) -> dict[str, object]:
        return {
            "id": item.id,
            "diagnosticRunId": item.diagnostic_run_id,
            "recommendationType": item.recommendation_type,
            "strategyProfileKey": item.strategy_profile_key,
            "patternType": item.pattern_type,
            "symbolId": item.symbol_id,
            "timeframe": item.timeframe,
            "horizonMinutes": item.horizon_minutes,
            "severity": item.severity,
            "status": item.status,
            "title": item.title,
            "rationale": item.rationale,
            "evidence": self.summarize_mapping(item.evidence_json),
            "createdAt": item.created_at,
            "updatedAt": item.updated_at,
        }

    def analysis_run_readiness_row(self, run: AnalysisRun) -> dict[str, object]:
        return {
            "id": run.id,
            "symbolId": run.symbol_id,
            "sourceId": run.source_id,
            "timeframe": run.timeframe,
            "analysisMode": run.analysis_mode,
            "status": run.status,
            "errorCode": run.error_code,
            "errorMessage": run.error_message,
            "engineVersion": run.engine_version,
            "ruleSetVersion": run.rule_set_version,
            "createdAt": run.created_at,
            "updatedAt": run.updated_at,
            "completedAt": run.completed_at,
        }

    def screenshot_readiness_row(self, run: ChartScreenshotRun) -> dict[str, object]:
        return {
            "id": run.id,
            "sourceId": run.source_id,
            "symbolId": run.symbol_id,
            "analysisRunId": run.analysis_run_id,
            "timeframe": run.timeframe,
            "fileName": run.file_name,
            "status": run.status,
            "chartType": run.chart_type,
            "supportedForAnalysis": run.supported_for_analysis,
            "analysisBlockedReason": run.analysis_blocked_reason,
            "extractionConfidence": run.extraction_confidence,
            "ocrStatus": run.ocr_status,
            "ocrConfidence": run.ocr_confidence,
            "warnings": run.extraction_warnings_json.get("warnings", []),
            "createdAt": run.created_at,
            "updatedAt": run.updated_at,
        }

    def screenshot_review_row(self, run: ChartScreenshotRun) -> dict[str, object]:
        human_review = run.parser_metadata_json.get("humanReview")
        return {
            "id": run.id,
            "analysisRunId": run.analysis_run_id,
            "status": run.status,
            "review": human_review if isinstance(human_review, dict) else None,
            "correctedFromRunId": run.parser_metadata_json.get("correctedFromChartScreenshotRunId"),
            "parserName": run.parser_name,
            "parserVersion": run.parser_version,
            "createdAt": run.created_at,
            "updatedAt": run.updated_at,
        }

    def summarize_mapping(self, value: dict[str, Any] | None) -> dict[str, object] | None:
        if value is None:
            return None
        summary: dict[str, object] = {}
        for key, item in list(value.items())[:30]:
            if isinstance(item, list):
                summary[key] = {"itemCount": len(item)}
            elif isinstance(item, dict):
                summary[key] = {"keys": sorted(str(nested_key) for nested_key in item)[:30]}
            else:
                summary[key] = item
        return summary
