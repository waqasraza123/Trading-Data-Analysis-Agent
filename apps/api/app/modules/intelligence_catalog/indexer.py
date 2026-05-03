from collections.abc import Awaitable, Callable
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisMode, AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.data_sources.models import DataSource
from app.modules.imports.models import ImportBatch
from app.modules.intelligence_catalog.models import IntelligenceCatalogArtifactType
from app.modules.intelligence_catalog.schemas import IntelligenceCatalogUpsert
from app.modules.news.models import NewsEvent
from app.modules.outcomes.models import SignalOutcome
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendation,
    StrategyProfileDiagnosticRun,
)
from app.modules.reasoning.models import LlmReasoningRun
from app.modules.signals.models import Signal
from app.modules.strategy_profiles.models import StrategyProfile


class IntelligenceCatalogIndexer:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.builders: dict[
            IntelligenceCatalogArtifactType,
            Callable[[UUID], Awaitable[IntelligenceCatalogUpsert | None]],
        ] = {
            IntelligenceCatalogArtifactType.ANALYSIS_RUN: self.build_analysis_run,
            IntelligenceCatalogArtifactType.SCHEDULED_SCAN_RUN: self.build_scheduled_scan_run,
            IntelligenceCatalogArtifactType.SIGNAL: self.build_signal,
            IntelligenceCatalogArtifactType.OUTCOME: self.build_outcome,
            IntelligenceCatalogArtifactType.REASONING_RUN: self.build_reasoning_run,
            IntelligenceCatalogArtifactType.ACTION_PLAN: self.build_action_plan,
            IntelligenceCatalogArtifactType.ACTION_ITEM: self.build_action_item,
            IntelligenceCatalogArtifactType.NEWS_EVENT: self.build_news_event,
            IntelligenceCatalogArtifactType.CHART_SCREENSHOT_RUN: self.build_chart_screenshot_run,
            IntelligenceCatalogArtifactType.OPERATOR_REVIEW: self.build_operator_review,
            IntelligenceCatalogArtifactType.QUALITY_RUN: self.build_quality_run,
            IntelligenceCatalogArtifactType.DIAGNOSTIC_RUN: self.build_diagnostic_run,
            IntelligenceCatalogArtifactType.DATASET_EXPORT: self.build_dataset_export,
            IntelligenceCatalogArtifactType.REPORT: self.build_report,
            IntelligenceCatalogArtifactType.RULE_MANIFEST: self.build_rule_manifest,
            IntelligenceCatalogArtifactType.PROVIDER_POLLING_REQUEST: self.build_provider_polling_request,
        }

    async def build(
        self,
        artifact_type: IntelligenceCatalogArtifactType,
        artifact_id: UUID,
        workspace_id: UUID | None = None,
    ) -> IntelligenceCatalogUpsert | None:
        if artifact_type == IntelligenceCatalogArtifactType.RULE_MANIFEST:
            return await self.build_rule_manifest(artifact_id, workspace_id)
        return await self.builders[artifact_type](artifact_id)

    async def build_analysis_run(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        run = await self.session.get(AnalysisRun, artifact_id)
        if run is None:
            return None
        return self.analysis_run_payload(run, IntelligenceCatalogArtifactType.ANALYSIS_RUN)

    async def build_scheduled_scan_run(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        run = await self.session.get(AnalysisRun, artifact_id)
        if run is None or run.analysis_mode != AnalysisMode.SCHEDULED_SCAN:
            return None
        return self.analysis_run_payload(run, IntelligenceCatalogArtifactType.SCHEDULED_SCAN_RUN)

    def analysis_run_payload(
        self,
        run: AnalysisRun,
        artifact_type: IntelligenceCatalogArtifactType,
    ) -> IntelligenceCatalogUpsert:
        title = f"{run.analysis_mode} analysis run {short_id(run.id)}"
        summary = f"{run.status} analysis for {run.timeframe} candles"
        return self.payload(
            artifact_type=artifact_type,
            artifact_id=run.id,
            workspace_id=run.workspace_id,
            title=title,
            summary=summary,
            status=run.status,
            symbol_id=run.symbol_id,
            timeframe=run.timeframe,
            readiness_label=run.status,
            source_type=run.analysis_mode,
            tags=[run.analysis_mode, run.status, "analysis"],
            artifact_created_at=run.created_at,
            metadata={
                "analysisMode": run.analysis_mode,
                "engineVersion": run.engine_version,
                "ruleSetVersion": run.rule_set_version,
                "sourceId": stringify(run.source_id),
                "includePartialLiveCandle": run.include_partial_live_candle,
                "includeNewsCorrelation": run.include_news_correlation,
                "includeAiExplanation": run.include_ai_explanation,
            },
            searchable_values=[title, summary, run.status, run.analysis_mode, run.timeframe],
        )

    async def build_signal(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        signal = await self.session.get(Signal, artifact_id)
        if signal is None:
            return None
        title = f"{signal.bias} {signal.pattern_type or 'market'} signal"
        summary = signal.summary
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.SIGNAL,
            artifact_id=signal.id,
            workspace_id=signal.workspace_id,
            title=title,
            summary=summary,
            status=signal.classification_status,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            strategy_profile_key=signal.strategy_profile_key,
            pattern_type=signal.pattern_type,
            bias=signal.bias,
            classification_status=signal.classification_status,
            quality_label=signal.confidence_label,
            source_type="deterministic_signal_classifier",
            tags=[
                "signal",
                signal.bias,
                signal.classification_status,
                signal.confidence_label,
                optional(signal.pattern_type),
                optional(signal.strategy_profile_key),
            ],
            artifact_created_at=signal.created_at,
            metadata={
                "analysisRunId": str(signal.analysis_run_id),
                "confidenceScore": decimal_to_string(signal.confidence_score),
                "confidenceLabel": signal.confidence_label,
                "noSignalReason": signal.no_signal_reason,
            },
            searchable_values=[
                title,
                summary,
                signal.bias,
                signal.pattern_type,
                signal.classification_status,
                signal.confidence_label,
                signal.strategy_profile_key,
            ],
        )

    async def build_outcome(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        outcome = await self.session.get(SignalOutcome, artifact_id)
        if outcome is None:
            return None
        title = f"{outcome.outcome_label} outcome over {outcome.horizon_minutes}m"
        summary = f"{outcome.evaluation_status} outcome for {outcome.bias} signal"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.OUTCOME,
            artifact_id=outcome.id,
            workspace_id=outcome.workspace_id,
            title=title,
            summary=summary,
            status=outcome.evaluation_status,
            symbol_id=outcome.symbol_id,
            timeframe=outcome.timeframe,
            strategy_profile_key=outcome.strategy_profile_key,
            pattern_type=outcome.pattern_type,
            bias=outcome.bias,
            classification_status=outcome.classification_status,
            outcome_label=outcome.outcome_label,
            source_type="outcome_evaluation",
            tags=[
                "outcome",
                outcome.outcome_label,
                outcome.evaluation_status,
                outcome.bias,
                optional(outcome.pattern_type),
                optional(outcome.strategy_profile_key),
            ],
            artifact_created_at=outcome.created_at,
            metadata={
                "analysisRunId": str(outcome.analysis_run_id),
                "signalId": str(outcome.signal_id),
                "horizonMinutes": outcome.horizon_minutes,
                "evaluationVersion": outcome.evaluation_version,
                "reversalDetected": outcome.reversal_detected,
            },
            searchable_values=[
                title,
                summary,
                outcome.outcome_label,
                outcome.evaluation_status,
                outcome.bias,
                outcome.pattern_type,
                outcome.strategy_profile_key,
            ],
        )

    async def build_reasoning_run(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        run = await self.session.get(LlmReasoningRun, artifact_id)
        if run is None:
            return None
        title = f"{run.reasoning_type} reasoning run"
        summary = f"{run.status} reasoning from {run.source_type}"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.REASONING_RUN,
            artifact_id=run.id,
            workspace_id=run.workspace_id,
            title=title,
            summary=summary,
            status=run.status,
            readiness_label=run.grounding_status,
            source_type=run.source_type,
            tags=[
                "reasoning",
                run.reasoning_type,
                run.status,
                run.safety_status,
                run.grounding_status,
                run.provider,
            ],
            artifact_created_at=run.created_at,
            metadata={
                "analysisRunId": stringify(run.analysis_run_id),
                "signalId": stringify(run.signal_id),
                "outcomeId": stringify(run.outcome_id),
                "provider": run.provider,
                "model": run.model,
                "safetyStatus": run.safety_status,
                "groundingStatus": run.grounding_status,
                "groundingIssueCount": len(run.grounding_issues_json),
            },
            searchable_values=[
                title,
                summary,
                run.reasoning_type,
                run.status,
                run.source_type,
                run.safety_status,
                run.grounding_status,
                run.provider,
                run.model,
            ],
        )

    async def build_action_plan(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        plan = await self.session.get(ReasoningActionPlan, artifact_id)
        if plan is None:
            return None
        title = f"{plan.status} action plan"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.ACTION_PLAN,
            artifact_id=plan.id,
            workspace_id=plan.workspace_id,
            title=title,
            summary=plan.summary,
            status=plan.status,
            source_type=plan.source_type,
            tags=["action_plan", plan.status, plan.source_type, plan.created_from],
            artifact_created_at=plan.created_at,
            metadata={
                "sourceId": str(plan.source_id),
                "signalId": stringify(plan.signal_id),
                "analysisRunId": stringify(plan.analysis_run_id),
                "reasoningRunId": stringify(plan.reasoning_run_id),
                "createdFrom": plan.created_from,
                "planVersion": plan.plan_version,
            },
            searchable_values=[title, plan.summary, plan.status, plan.source_type, plan.created_from],
        )

    async def build_action_item(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        item = await self.session.get(ReasoningActionItem, artifact_id)
        if item is None:
            return None
        title = f"{item.action_type} action item"
        summary = f"{item.status} action item with {item.priority} priority"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.ACTION_ITEM,
            artifact_id=item.id,
            workspace_id=item.workspace_id,
            title=title,
            summary=summary,
            status=item.status,
            readiness_label=item.priority,
            source_type=item.source_type,
            tags=["action_item", item.action_type, item.status, item.priority, item.source_type],
            artifact_created_at=item.created_at,
            metadata={
                "actionPlanId": str(item.action_plan_id),
                "sourceId": str(item.source_id),
                "signalId": stringify(item.signal_id),
                "analysisRunId": stringify(item.analysis_run_id),
                "reasoningRunId": stringify(item.reasoning_run_id),
                "dueAt": item.due_at.isoformat() if item.due_at else None,
                "horizonMinutes": item.horizon_minutes,
            },
            searchable_values=[
                title,
                summary,
                item.action_type,
                item.status,
                item.priority,
                item.source_type,
                item.error_code,
            ],
        )

    async def build_news_event(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        event = await self.session.get(NewsEvent, artifact_id)
        if event is None or event.workspace_id is None:
            return None
        summary = event.description or f"{event.importance} {event.event_type} event"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.NEWS_EVENT,
            artifact_id=event.id,
            workspace_id=event.workspace_id,
            title=event.title,
            summary=summary,
            status=event.importance,
            symbol_id=event.symbol_id,
            bias=event.sentiment,
            source_type=event.event_type,
            tags=[
                "news_event",
                event.event_type,
                event.importance,
                event.sentiment,
                event.source,
                optional(event.currency),
                optional(event.asset),
            ],
            artifact_created_at=event.created_at,
            metadata={
                "source": event.source,
                "eventTime": event.event_time.isoformat(),
                "currency": event.currency,
                "asset": event.asset,
                "url": event.url,
            },
            searchable_values=[
                event.title,
                summary,
                event.event_type,
                event.importance,
                event.sentiment,
                event.currency,
                event.asset,
                event.source,
            ],
        )

    async def build_chart_screenshot_run(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        run = await self.session.get(ChartScreenshotRun, artifact_id)
        if run is None:
            return None
        title = f"{run.analysis_hypothesis} chart screenshot run"
        summary = f"{run.status} screenshot extraction for {run.timeframe}"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.CHART_SCREENSHOT_RUN,
            artifact_id=run.id,
            workspace_id=run.workspace_id,
            title=title,
            summary=summary,
            status=run.status,
            symbol_id=run.symbol_id,
            timeframe=run.timeframe,
            bias=run.analysis_hypothesis,
            quality_label=quality_label(run.extraction_confidence),
            readiness_label=run.analysis_blocked_reason or run.status,
            source_type="chart_screenshot",
            tags=[
                "chart_screenshot",
                "screenshot_derived",
                run.status,
                run.analysis_hypothesis,
                optional(run.chart_type),
            ],
            artifact_created_at=run.created_at,
            metadata={
                "sourceId": str(run.source_id),
                "analysisRunId": stringify(run.analysis_run_id),
                "parserName": run.parser_name,
                "parserVersion": run.parser_version,
                "chartType": run.chart_type,
                "supportedForAnalysis": run.supported_for_analysis,
                "analysisBlockedReason": run.analysis_blocked_reason,
                "extractionConfidence": decimal_to_string(run.extraction_confidence),
                "rawCandleCount": run.raw_candle_count,
                "storedCandleCount": run.stored_candle_count,
            },
            searchable_values=[
                title,
                summary,
                run.status,
                run.analysis_hypothesis,
                run.parser_name,
                run.chart_type,
                run.analysis_blocked_reason,
            ],
        )

    async def build_operator_review(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        recommendation = await self.session.get(CalibrationRecommendation, artifact_id)
        if recommendation is not None:
            return self.payload(
                artifact_type=IntelligenceCatalogArtifactType.OPERATOR_REVIEW,
                artifact_id=recommendation.id,
                workspace_id=recommendation.workspace_id,
                title=recommendation.title,
                summary=recommendation.rationale,
                status=recommendation.status,
                symbol_id=recommendation.symbol_id,
                timeframe=recommendation.timeframe,
                strategy_profile_key=recommendation.strategy_profile_key,
                pattern_type=recommendation.pattern_type,
                readiness_label=recommendation.severity,
                source_type="calibration_recommendation",
                tags=[
                    "operator_review",
                    "calibration_recommendation",
                    recommendation.status,
                    recommendation.severity,
                    recommendation.recommendation_type,
                ],
                artifact_created_at=recommendation.created_at,
                metadata={
                    "diagnosticRunId": str(recommendation.diagnostic_run_id),
                    "recommendationType": recommendation.recommendation_type,
                    "horizonMinutes": recommendation.horizon_minutes,
                },
                searchable_values=[
                    recommendation.title,
                    recommendation.rationale,
                    recommendation.status,
                    recommendation.severity,
                    recommendation.recommendation_type,
                    recommendation.pattern_type,
                    recommendation.strategy_profile_key,
                ],
            )
        action_item = await self.session.get(ReasoningActionItem, artifact_id)
        if action_item is None or action_item.action_type != "request_human_review":
            return None
        title = "Human review action item"
        summary = f"{action_item.status} human review request with {action_item.priority} priority"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.OPERATOR_REVIEW,
            artifact_id=action_item.id,
            workspace_id=action_item.workspace_id,
            title=title,
            summary=summary,
            status=action_item.status,
            readiness_label=action_item.priority,
            source_type="human_review_action_item",
            tags=[
                "operator_review",
                "human_review",
                action_item.status,
                action_item.priority,
                action_item.source_type,
            ],
            artifact_created_at=action_item.created_at,
            metadata={
                "actionPlanId": str(action_item.action_plan_id),
                "sourceId": str(action_item.source_id),
                "signalId": stringify(action_item.signal_id),
                "analysisRunId": stringify(action_item.analysis_run_id),
                "reasoningRunId": stringify(action_item.reasoning_run_id),
                "dueAt": action_item.due_at.isoformat() if action_item.due_at else None,
            },
            searchable_values=[
                title,
                summary,
                action_item.action_type,
                action_item.status,
                action_item.priority,
                action_item.source_type,
            ],
        )

    async def build_quality_run(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        batch = await self.session.get(ImportBatch, artifact_id)
        if batch is None:
            return None
        label = quality_label(batch.data_quality_score)
        title = f"{label} import quality run"
        summary = f"{batch.status} import quality for {batch.timeframe}"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.QUALITY_RUN,
            artifact_id=batch.id,
            workspace_id=batch.workspace_id,
            title=title,
            summary=summary,
            status=batch.status,
            symbol_id=batch.symbol_id,
            timeframe=batch.timeframe,
            quality_label=label,
            source_type="import_batch_quality",
            tags=["quality_run", batch.status, label],
            artifact_created_at=batch.created_at,
            metadata={
                "importBatchId": str(batch.id),
                "sourceId": str(batch.source_id),
                "rowsReceived": batch.rows_received,
                "rowsValid": batch.rows_valid,
                "rowsInvalid": batch.rows_invalid,
                "duplicatesSkipped": batch.duplicates_skipped,
                "missingCandlesDetected": batch.missing_candles_detected,
                "dataQualityScore": decimal_to_string(batch.data_quality_score),
            },
            searchable_values=[title, summary, batch.status, label, batch.file_name],
        )

    async def build_diagnostic_run(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        run = await self.session.get(StrategyProfileDiagnosticRun, artifact_id)
        if run is None:
            return None
        title = f"{run.scope_type} diagnostic run"
        summary = f"{run.status} diagnostic run with {run.diagnostics_created_count} diagnostics"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.DIAGNOSTIC_RUN,
            artifact_id=run.id,
            workspace_id=run.workspace_id,
            title=title,
            summary=summary,
            status=run.status,
            source_type=run.scope_type,
            tags=["diagnostic_run", run.status, run.scope_type],
            artifact_created_at=run.created_at,
            metadata={
                "scopeType": run.scope_type,
                "minimumSampleSize": run.minimum_sample_size,
                "evaluatedSignalCount": run.evaluated_signal_count,
                "evaluatedOutcomeCount": run.evaluated_outcome_count,
                "diagnosticsCreatedCount": run.diagnostics_created_count,
                "recommendationsCreatedCount": run.recommendations_created_count,
            },
            searchable_values=[title, summary, run.status, run.scope_type, run.error_message],
        )

    async def build_dataset_export(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        batch = await self.session.get(ImportBatch, artifact_id)
        if batch is None:
            return None
        title = f"{batch.file_name or short_id(batch.id)} dataset export"
        summary = f"{batch.status} dataset import with {batch.rows_valid} valid rows"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.DATASET_EXPORT,
            artifact_id=batch.id,
            workspace_id=batch.workspace_id,
            title=title,
            summary=summary,
            status=batch.status,
            symbol_id=batch.symbol_id,
            timeframe=batch.timeframe,
            quality_label=quality_label(batch.data_quality_score),
            source_type="import_batch",
            tags=["dataset_export", "import_batch", batch.status],
            artifact_created_at=batch.created_at,
            metadata={
                "sourceId": str(batch.source_id),
                "fileName": batch.file_name,
                "fileUrl": batch.file_url,
                "rowsReceived": batch.rows_received,
                "rowsValid": batch.rows_valid,
                "rowsInvalid": batch.rows_invalid,
            },
            searchable_values=[title, summary, batch.status, batch.file_name, batch.timeframe],
        )

    async def build_report(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        signal = await self.session.get(Signal, artifact_id)
        if signal is not None:
            return self.report_payload(
                workspace_id=signal.workspace_id,
                artifact_id=signal.id,
                title="Signal intelligence report",
                summary=signal.summary,
                status=signal.classification_status,
                symbol_id=signal.symbol_id,
                timeframe=signal.timeframe,
                source_type="signal_report",
                tags=["report", "signal_report", signal.classification_status],
                artifact_created_at=signal.created_at,
            )
        analysis_run = await self.session.get(AnalysisRun, artifact_id)
        if analysis_run is not None:
            return self.report_payload(
                workspace_id=analysis_run.workspace_id,
                artifact_id=analysis_run.id,
                title="Analysis run intelligence report",
                summary=f"{analysis_run.status} analysis report",
                status=analysis_run.status,
                symbol_id=analysis_run.symbol_id,
                timeframe=analysis_run.timeframe,
                source_type="analysis_run_report",
                tags=["report", "analysis_run_report", analysis_run.status],
                artifact_created_at=analysis_run.created_at,
            )
        reasoning_run = await self.session.get(LlmReasoningRun, artifact_id)
        if reasoning_run is not None:
            return self.report_payload(
                workspace_id=reasoning_run.workspace_id,
                artifact_id=reasoning_run.id,
                title="Reasoning run intelligence report",
                summary=f"{reasoning_run.status} reasoning report",
                status=reasoning_run.status,
                source_type="reasoning_run_report",
                tags=["report", "reasoning_run_report", reasoning_run.status],
                artifact_created_at=reasoning_run.created_at,
            )
        outcome = await self.session.get(SignalOutcome, artifact_id)
        if outcome is not None:
            return self.report_payload(
                workspace_id=outcome.workspace_id,
                artifact_id=outcome.id,
                title="Outcome intelligence report",
                summary=f"{outcome.outcome_label} outcome report",
                status=outcome.evaluation_status,
                symbol_id=outcome.symbol_id,
                timeframe=outcome.timeframe,
                source_type="outcome_report",
                tags=["report", "outcome_report", outcome.outcome_label],
                artifact_created_at=outcome.created_at,
            )
        screenshot_run = await self.session.get(ChartScreenshotRun, artifact_id)
        if screenshot_run is None:
            return None
        return self.report_payload(
            workspace_id=screenshot_run.workspace_id,
            artifact_id=screenshot_run.id,
            title="Screenshot decision report",
            summary=f"{screenshot_run.status} screenshot decision report",
            status=screenshot_run.status,
            symbol_id=screenshot_run.symbol_id,
            timeframe=screenshot_run.timeframe,
            source_type="screenshot_decision_report",
            tags=["report", "screenshot_decision_report", screenshot_run.status],
            artifact_created_at=screenshot_run.created_at,
        )

    async def build_rule_manifest(
        self,
        artifact_id: UUID,
        workspace_id: UUID | None = None,
    ) -> IntelligenceCatalogUpsert | None:
        profile = await self.session.get(StrategyProfile, artifact_id)
        if profile is None:
            return None
        title = f"{profile.key} rule manifest"
        summary = profile.description
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.RULE_MANIFEST,
            artifact_id=profile.id,
            workspace_id=workspace_id or await self.resolve_global_workspace_id(),
            title=title,
            summary=summary,
            status="active" if profile.is_active else "inactive",
            strategy_profile_key=profile.key,
            source_type="strategy_profile",
            tags=["rule_manifest", "strategy_profile", profile.key, profile.version],
            artifact_created_at=profile.created_at,
            metadata={
                "strategyProfileKey": profile.key,
                "strategyProfileVersion": profile.version,
                "isActive": profile.is_active,
                "allowedPatterns": profile.allowed_patterns_json,
                "excludedPatterns": profile.excluded_patterns_json,
                "minimumCandidateStrength": decimal_to_string(profile.minimum_candidate_strength),
                "minimumConfidence": decimal_to_string(profile.minimum_confidence),
            },
            searchable_values=[title, summary, profile.key, profile.name, profile.version],
        )

    async def build_provider_polling_request(self, artifact_id: UUID) -> IntelligenceCatalogUpsert | None:
        source = await self.session.get(DataSource, artifact_id)
        if source is None or source.source_type != "api_polling":
            return None
        title = f"{source.provider} provider polling request"
        summary = f"{source.status} API polling data source"
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.PROVIDER_POLLING_REQUEST,
            artifact_id=source.id,
            workspace_id=source.workspace_id,
            title=title,
            summary=summary,
            status=source.status,
            source_type=source.source_type,
            tags=["provider_polling_request", source.source_type, source.status, source.provider],
            artifact_created_at=source.created_at,
            metadata={
                "dataSourceId": str(source.id),
                "provider": source.provider,
                "sourceType": source.source_type,
            },
            searchable_values=[title, summary, source.name, source.provider, source.source_type, source.status],
        )

    def report_payload(
        self,
        workspace_id: UUID,
        artifact_id: UUID,
        title: str,
        summary: str,
        status: str | None,
        source_type: str,
        tags: list[str],
        artifact_created_at,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
    ) -> IntelligenceCatalogUpsert:
        return self.payload(
            artifact_type=IntelligenceCatalogArtifactType.REPORT,
            artifact_id=artifact_id,
            workspace_id=workspace_id,
            title=title,
            summary=summary,
            status=status,
            symbol_id=symbol_id,
            timeframe=timeframe,
            source_type=source_type,
            tags=tags,
            artifact_created_at=artifact_created_at,
            metadata={"reportType": source_type, "subjectId": str(artifact_id)},
            searchable_values=[title, summary, status, source_type, *tags],
        )

    async def resolve_global_workspace_id(self) -> UUID:
        statement = select(AnalysisRun.workspace_id).limit(1)
        result = await self.session.execute(statement)
        workspace_id = result.scalar_one_or_none()
        if workspace_id is None:
            statement = select(ImportBatch.workspace_id).limit(1)
            result = await self.session.execute(statement)
            workspace_id = result.scalar_one_or_none()
        if workspace_id is None:
            msg = "At least one workspace-scoped artifact is required before indexing global manifests"
            raise ValueError(msg)
        return workspace_id

    def payload(
        self,
        artifact_type: IntelligenceCatalogArtifactType,
        artifact_id: UUID,
        workspace_id: UUID,
        title: str,
        summary: str,
        tags: list[str | None],
        searchable_values: list[object],
        metadata: dict[str, object | None],
        status: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        strategy_profile_key: str | None = None,
        pattern_type: str | None = None,
        bias: str | None = None,
        classification_status: str | None = None,
        quality_label: str | None = None,
        readiness_label: str | None = None,
        outcome_label: str | None = None,
        source_type: str | None = None,
        artifact_created_at=None,
    ) -> IntelligenceCatalogUpsert:
        normalized_tags = sorted({tag for tag in tags if tag})
        searchable_text = " ".join(
            str(value) for value in [title, summary, *searchable_values, *normalized_tags] if value
        )
        return IntelligenceCatalogUpsert(
            workspace_id=workspace_id,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            title=trim(title, 300),
            summary=trim(summary, 4000),
            status=status,
            symbol_id=symbol_id,
            timeframe=timeframe,
            strategy_profile_key=strategy_profile_key,
            pattern_type=pattern_type,
            bias=bias,
            classification_status=classification_status,
            quality_label=quality_label,
            readiness_label=readiness_label,
            outcome_label=outcome_label,
            source_type=source_type,
            tags_json=normalized_tags,
            searchable_text=searchable_text,
            metadata_json=metadata,
            artifact_created_at=artifact_created_at,
        )


def quality_label(value: Decimal | None) -> str:
    if value is None:
        return "unknown"
    if value >= Decimal("0.90"):
        return "high"
    if value >= Decimal("0.70"):
        return "medium"
    return "low"


def decimal_to_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def stringify(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def short_id(value: UUID) -> str:
    return str(value).split("-")[0]


def trim(value: str, max_length: int) -> str:
    return value if len(value) <= max_length else value[:max_length]


def optional(value: str | None) -> str | None:
    return value
