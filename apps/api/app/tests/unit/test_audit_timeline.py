from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisMode, AnalysisRun
from app.modules.audit_timeline.collectors import (
    BANNED_TIMELINE_PHRASES,
    bounded_timeline,
    completeness_from_components,
    contains_banned_timeline_phrase,
    safe_metadata,
    timeline_event,
)
from app.modules.audit_timeline.schemas import CompletenessLabel
from app.modules.audit_timeline.service import AuditTimelineService
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.explanations.models import DeterministicExplanation, ExplanationType
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFinding,
    IntelligenceQualityRun,
    ShadowClassificationResult,
)
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.market_scans.models import ScheduledScanRun, ScheduledScanRunItem
from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)

BASE_TIME = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)


class FakeAuditTimelineRepository:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.symbol_id = uuid4()
        self.source_id = uuid4()
        self.analysis_run_id = uuid4()
        self.signal_id = uuid4()
        self.reasoning_run_id = uuid4()
        self.action_plan_id = uuid4()
        self.outcome_id = uuid4()
        self.chart_run_id = uuid4()
        self.run = analysis_run_row(self.analysis_run_id, self.workspace_id, self.symbol_id)
        self.signal = signal_row(self.signal_id, self.workspace_id, self.symbol_id, self.run.id)
        self.feature_snapshot: FeatureSnapshot | None = feature_snapshot_row(self.run)
        self.indicator_snapshot: IndicatorSnapshot | None = indicator_snapshot_row(self.run)
        self.patterns = [pattern_candidate_row(self.run, self.signal.selected_pattern_candidate_id)]
        self.evidence = [evidence_row(self.signal.id, "Breakout evidence persisted.")]
        self.components = [confidence_component_row(self.signal.id)]
        self.risk_notes = [risk_note_row(self.signal.id)]
        self.explanation: DeterministicExplanation | None = explanation_row(
            self.signal.id,
            self.run.id,
            self.workspace_id,
        )
        self.llm_explanations = [
            llm_explanation_row(self.signal.id, self.run.id, self.workspace_id)
        ]
        self.news_correlations = [
            news_correlation_row(self.signal.id, self.run.id, self.workspace_id)
        ]
        self.outcomes = [outcome_row(self.outcome_id, self.signal)]
        self.reasoning_runs = [
            reasoning_run_row(
                self.reasoning_run_id,
                self.workspace_id,
                self.run.id,
                self.signal.id,
                self.outcome_id,
            )
        ]
        self.scenarios = [scenario_row(self.reasoning_run_id, self.signal.id)]
        self.action_plans = [
            action_plan_row(
                self.action_plan_id,
                self.workspace_id,
                self.reasoning_run_id,
                self.signal.id,
                self.run.id,
            )
        ]
        self.action_items = [
            action_item_row(self.action_plan_id, self.workspace_id, self.signal.id)
        ]
        self.replay_runs = [replay_run_row(uuid4(), self.run)]
        self.chart_runs = [
            chart_run_row(
                self.chart_run_id,
                self.workspace_id,
                self.source_id,
                self.symbol_id,
                self.run.id,
            )
        ]
        self.chart_corrections = [
            chart_correction_row(uuid4(), self.chart_runs[0], self.workspace_id)
        ]
        self.scan_run = scheduled_scan_run_row(
            uuid4(),
            self.workspace_id,
            self.run.id,
            self.signal.id,
        )
        self.scan_items = [
            scheduled_scan_item_row(
                uuid4(),
                self.workspace_id,
                self.scan_run.id,
                self.scan_run.scan_config_id,
                self.run,
                self.signal,
            )
        ]
        self.quality_run = quality_run_row(
            uuid4(),
            self.workspace_id,
            self.run.id,
            self.signal.id,
        )
        self.quality_findings = [quality_finding_row(uuid4(), self.quality_run)]
        self.shadow_results = [shadow_result_row(uuid4(), self.quality_run, self.run, self.signal)]
        self.audit_logs = [audit_log_row(self.run.id)]
        self.profile_diagnostics = [{"id": uuid4(), "diagnostic_label": "neutral"}]
        self.pattern_diagnostics = [{"id": uuid4(), "diagnostic_label": "neutral"}]
        self.recommendations = [{"id": uuid4(), "title": "Review threshold"}]
        self.worker_runs = [{"id": uuid4(), "status": "completed", "created_at": BASE_TIME}]

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        if analysis_run_id == self.run.id:
            return self.run
        for run in self.replay_runs:
            if analysis_run_id == run.id:
                return run
        return None

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return self.signal if signal_id == self.signal.id else None

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        return self.signal if analysis_run_id == self.run.id else None

    async def get_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun | None:
        return self.reasoning_runs[0] if reasoning_run_id == self.reasoning_run_id else None

    async def get_action_plan(self, action_plan_id: UUID) -> ReasoningActionPlan | None:
        return self.action_plans[0] if action_plan_id == self.action_plan_id else None

    async def get_outcome(self, outcome_id: UUID) -> SignalOutcome | None:
        return self.outcomes[0] if outcome_id == self.outcome_id else None

    async def get_chart_screenshot_run(self, run_id: UUID) -> ChartScreenshotRun | None:
        return self.chart_runs[0] if run_id == self.chart_run_id else None

    async def get_feature_snapshot(self, analysis_run_id: UUID) -> FeatureSnapshot | None:
        return self.feature_snapshot if analysis_run_id == self.run.id else None

    async def get_indicator_snapshot(self, analysis_run_id: UUID) -> IndicatorSnapshot | None:
        return self.indicator_snapshot if analysis_run_id == self.run.id else None

    async def get_pattern_candidate(self, pattern_candidate_id: UUID) -> PatternCandidate | None:
        for candidate in self.patterns:
            if candidate.id == pattern_candidate_id:
                return candidate
        return None

    async def list_pattern_candidates(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[PatternCandidate]:
        return self.patterns[:limit] if analysis_run_id == self.run.id else []

    async def list_confidence_components(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[SignalConfidenceComponent]:
        return self.components[:limit] if signal_id == self.signal.id else []

    async def list_evidence(self, signal_id: UUID, limit: int) -> list[SignalEvidence]:
        return self.evidence[:limit] if signal_id == self.signal.id else []

    async def list_risk_notes(self, signal_id: UUID, limit: int) -> list[SignalRiskNote]:
        return self.risk_notes[:limit] if signal_id == self.signal.id else []

    async def get_deterministic_explanation_by_signal_id(
        self,
        signal_id: UUID,
    ) -> DeterministicExplanation | None:
        return self.explanation if signal_id == self.signal.id else None

    async def get_deterministic_explanation_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> DeterministicExplanation | None:
        return self.explanation if analysis_run_id == self.run.id else None

    async def list_llm_explanations_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[LlmExplanation]:
        return self.llm_explanations[:limit] if signal_id == self.signal.id else []

    async def list_llm_explanations_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[LlmExplanation]:
        return self.llm_explanations[:limit] if analysis_run_id == self.run.id else []

    async def list_news_correlations_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[SignalNewsCorrelation]:
        return self.news_correlations[:limit] if signal_id == self.signal.id else []

    async def list_news_correlations_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[SignalNewsCorrelation]:
        return self.news_correlations[:limit] if analysis_run_id == self.run.id else []

    async def list_news_events(self, news_event_ids: list[UUID]) -> list[object]:
        return []

    async def list_signal_outcomes(self, signal_id: UUID, limit: int) -> list[SignalOutcome]:
        return self.outcomes[:limit] if signal_id == self.signal.id else []

    async def list_analysis_outcomes(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[SignalOutcome]:
        return self.outcomes[:limit] if analysis_run_id == self.run.id else []

    async def list_reasoning_runs_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[LlmReasoningRun]:
        return self.reasoning_runs[:limit] if signal_id == self.signal.id else []

    async def list_reasoning_runs_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[LlmReasoningRun]:
        return self.reasoning_runs[:limit] if analysis_run_id == self.run.id else []

    async def list_reasoning_runs_by_outcome_id(
        self,
        outcome_id: UUID,
        limit: int,
    ) -> list[LlmReasoningRun]:
        return self.reasoning_runs[:limit] if outcome_id == self.outcome_id else []

    async def list_scenario_hypotheses(
        self,
        reasoning_run_id: UUID,
        limit: int,
    ) -> list[ScenarioHypothesis]:
        return self.scenarios[:limit] if reasoning_run_id == self.reasoning_run_id else []

    async def list_action_plans_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[ReasoningActionPlan]:
        return self.action_plans[:limit] if signal_id == self.signal.id else []

    async def list_action_plans_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[ReasoningActionPlan]:
        return self.action_plans[:limit] if analysis_run_id == self.run.id else []

    async def list_action_plans_by_reasoning_run_id(
        self,
        reasoning_run_id: UUID,
        limit: int,
    ) -> list[ReasoningActionPlan]:
        return self.action_plans[:limit] if reasoning_run_id == self.reasoning_run_id else []

    async def list_action_items(
        self,
        action_plan_id: UUID,
        limit: int,
    ) -> list[ReasoningActionItem]:
        return self.action_items[:limit] if action_plan_id == self.action_plan_id else []

    async def list_action_items_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[ReasoningActionItem]:
        return self.action_items[:limit] if signal_id == self.signal.id else []

    async def list_chart_screenshot_runs_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[ChartScreenshotRun]:
        return self.chart_runs[:limit] if analysis_run_id == self.run.id else []

    async def list_chart_corrections(
        self,
        run_id: UUID,
        limit: int,
    ) -> list[ChartScreenshotRun]:
        return self.chart_corrections[:limit] if run_id == self.chart_run_id else []

    async def list_scheduled_scan_items_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[ScheduledScanRunItem]:
        return self.scan_items[:limit] if analysis_run_id == self.run.id else []

    async def list_scheduled_scan_runs_by_item_ids(
        self,
        scan_run_ids: list[UUID],
        limit: int,
    ) -> list[ScheduledScanRun]:
        return [self.scan_run][:limit] if self.scan_run.id in scan_run_ids else []

    async def list_quality_runs_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[IntelligenceQualityRun]:
        return [self.quality_run][:limit] if analysis_run_id == self.run.id else []

    async def list_quality_runs_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[IntelligenceQualityRun]:
        return [self.quality_run][:limit] if signal_id == self.signal.id else []

    async def list_quality_findings_by_run_ids(
        self,
        quality_run_ids: list[UUID],
        limit: int,
    ) -> list[IntelligenceQualityFinding]:
        return self.quality_findings[:limit] if self.quality_run.id in quality_run_ids else []

    async def list_shadow_results_by_quality_run_ids(
        self,
        quality_run_ids: list[UUID],
        limit: int,
    ) -> list[ShadowClassificationResult]:
        return self.shadow_results[:limit] if self.quality_run.id in quality_run_ids else []

    async def list_replay_runs(self, analysis_run_id: UUID, limit: int) -> list[AnalysisRun]:
        return self.replay_runs[:limit] if analysis_run_id == self.run.id else []

    async def list_audit_logs(self, analysis_run_id: UUID, limit: int) -> list[AnalysisAuditLog]:
        return self.audit_logs[:limit] if analysis_run_id == self.run.id else []

    async def list_optional_strategy_profile_diagnostics(
        self,
        workspace_id: UUID,
        strategy_profile_key: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.profile_diagnostics[:limit]

    async def list_optional_pattern_diagnostics(
        self,
        workspace_id: UUID,
        pattern_type: str | None,
        strategy_profile_key: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.pattern_diagnostics[:limit]

    async def list_optional_calibration_recommendations(
        self,
        workspace_id: UUID,
        strategy_profile_key: str | None,
        pattern_type: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.recommendations[:limit]

    async def list_optional_action_worker_runs(
        self,
        workspace_id: UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self.worker_runs[:limit]


@pytest.mark.anyio
async def test_builds_analysis_timeline_with_synthetic_artifact_timestamps() -> None:
    service, repository = service_with_fake_repository()

    timeline = await service.build_analysis_run_timeline(repository.run.id)
    event_types = [event.event_type for event in timeline.timeline]

    assert "feature_snapshot_created" in event_types
    assert "indicator_snapshot_created" in event_types
    assert "signal_classified" in event_types
    assert timeline.completeness.label == CompletenessLabel.COMPLETE


@pytest.mark.anyio
async def test_analysis_timeline_includes_scan_and_quality_provenance() -> None:
    service, repository = service_with_fake_repository()

    timeline = await service.build_analysis_run_timeline(repository.run.id)
    event_types = {event.event_type for event in timeline.timeline}

    assert "scheduled_scan_run_linked" in event_types
    assert "scheduled_scan_item_linked" in event_types
    assert "intelligence_quality_finding_linked" in event_types
    assert timeline.sections["scheduled_scan_runs"]["returned_count"] == 1
    assert timeline.sections["quality_findings"]["returned_count"] == 1


@pytest.mark.anyio
async def test_builds_signal_timeline_with_evidence_confidence_and_explanation() -> None:
    service, repository = service_with_fake_repository()

    timeline = await service.build_signal_timeline(repository.signal.id)
    event_types = [event.event_type for event in timeline.timeline]

    assert "signal_evidence_persisted" in event_types
    assert "signal_confidence_persisted" in event_types
    assert "deterministic_explanation_generated" in event_types
    assert timeline.sections["evidence"]["returned_count"] == 1
    assert timeline.sections["diagnostics"]["quality_runs"]["returned_count"] == 1


@pytest.mark.anyio
async def test_builds_reasoning_timeline_with_scenario_hypotheses() -> None:
    service, repository = service_with_fake_repository()

    timeline = await service.build_reasoning_run_timeline(repository.reasoning_run_id)

    assert timeline.sections["scenario_hypotheses"]["returned_count"] == 1
    assert any(event.event_type == "scenario_hypothesis_persisted" for event in timeline.timeline)


@pytest.mark.anyio
async def test_builds_action_plan_timeline_without_executing_actions() -> None:
    service, repository = service_with_fake_repository()

    timeline = await service.build_action_plan_timeline(repository.action_plan_id)

    assert timeline.sections["actions_executed_by_timeline"] is False
    assert repository.action_items[0].status == "pending"
    assert any(event.event_type == "action_item_created" for event in timeline.timeline)


@pytest.mark.anyio
async def test_builds_outcome_timeline_with_movement_fields() -> None:
    service, repository = service_with_fake_repository()

    timeline = await service.build_outcome_timeline(repository.outcome_id)

    assert timeline.sections["outcome"]["net_pips"] == "15"
    assert timeline.sections["outcome"]["outcome_label"] == OutcomeLabel.CONTINUATION.value
    assert any(event.event_type == "outcome_evaluated" for event in timeline.timeline)


@pytest.mark.anyio
async def test_chart_screenshot_adapter_handles_missing_optional_ocr_review_fields() -> None:
    service, repository = service_with_fake_repository()
    repository.chart_runs[0].parser_metadata_json = {}

    timeline = await service.build_chart_screenshot_run_timeline(repository.chart_run_id)

    assert timeline.sections["chart_screenshot_run"]["ocr"] is None
    assert timeline.sections["human_review"] is None
    assert "human_review" in timeline.completeness.missing_sections


def test_completeness_score_complete_partial_sparse() -> None:
    complete = completeness_from_components(
        {"a": True, "b": True, "c": True, "d": True, "e": False}
    )
    partial = completeness_from_components({"a": True, "b": False})
    sparse = completeness_from_components({"a": False, "b": False, "c": True})

    assert complete.label == CompletenessLabel.COMPLETE
    assert partial.label == CompletenessLabel.PARTIAL
    assert sparse.label == CompletenessLabel.SPARSE


def test_redaction_removes_secret_like_metadata_and_payloads() -> None:
    payload = safe_metadata(
        {
            "apiKey": "secret-value",
            "databaseUrl": "postgresql://secret",
            "rawPayload": {"token": "secret"},
            "imageBase64": "a" * 600,
            "summary": "buy now with guaranteed profit",
        }
    )

    serialized = str(payload).lower()
    assert "secret-value" not in serialized
    assert "postgresql://secret" not in serialized
    assert "buy now" not in serialized
    assert "guaranteed profit" not in serialized
    assert "redacted" in serialized


def test_timeline_enforces_event_limit() -> None:
    events = [
        timeline_event(
            BASE_TIME + timedelta(minutes=index),
            f"event_{index}",
            "test",
            str(index),
            "Test",
            "Test",
        )
        for index in range(10)
    ]

    assert len(bounded_timeline(events, 3)) == 3


@pytest.mark.anyio
async def test_missing_optional_artifacts_become_missing_sections_not_failures() -> None:
    service, repository = service_with_fake_repository()
    repository.feature_snapshot = None
    repository.indicator_snapshot = None
    repository.patterns = []
    repository.explanation = None

    timeline = await service.build_analysis_run_timeline(repository.run.id)

    assert "feature_snapshot" in timeline.completeness.missing_sections
    assert "indicator_snapshot" in timeline.completeness.missing_sections
    assert "pattern_candidates" in timeline.completeness.missing_sections
    assert "deterministic_explanation" in timeline.completeness.missing_sections


@pytest.mark.anyio
async def test_artifact_graph_nodes_and_edges_are_built() -> None:
    service, repository = service_with_fake_repository()

    timeline = await service.build_signal_timeline(repository.signal.id)

    node_types = {node.type for node in timeline.artifact_graph.nodes}
    relationships = {edge.relationship for edge in timeline.artifact_graph.edges}
    assert "signal" in node_types
    assert "deterministic_explanation" in node_types
    assert "explained_by" in relationships


@pytest.mark.anyio
async def test_no_report_contains_banned_trading_phrases() -> None:
    service, repository = service_with_fake_repository()
    repository.evidence = [evidence_row(repository.signal.id, "buy now and place order")]

    timeline = await service.build_signal_timeline(repository.signal.id)

    assert not contains_banned_timeline_phrase(timeline.model_dump(mode="json", by_alias=True))
    serialized = str(timeline.model_dump(mode="json", by_alias=True)).lower()
    for phrase in BANNED_TIMELINE_PHRASES:
        assert phrase not in serialized


def service_with_fake_repository() -> tuple[AuditTimelineService, FakeAuditTimelineRepository]:
    repository = FakeAuditTimelineRepository()
    service = AuditTimelineService(cast(AsyncSession, object()))
    service.repository = repository  # type: ignore[assignment]
    return service, repository


def analysis_run_row(run_id: UUID, workspace_id: UUID, symbol_id: UUID) -> AnalysisRun:
    return AnalysisRun(
        id=run_id,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe="1m",
        start_time=BASE_TIME - timedelta(minutes=30),
        end_time=BASE_TIME,
        warmup_start_time=BASE_TIME - timedelta(minutes=60),
        baseline_start_time=BASE_TIME - timedelta(minutes=120),
        analysis_mode=AnalysisMode.HISTORICAL.value,
        include_partial_live_candle=False,
        include_news_correlation=True,
        include_ai_explanation=True,
        status="completed",
        engine_version="engine_v1",
        rule_set_version="rules_v1",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
        started_at=BASE_TIME,
        completed_at=BASE_TIME + timedelta(seconds=10),
    )


def replay_run_row(run_id: UUID, original: AnalysisRun) -> AnalysisRun:
    return AnalysisRun(
        id=run_id,
        workspace_id=original.workspace_id,
        symbol_id=original.symbol_id,
        timeframe=original.timeframe,
        start_time=original.start_time,
        end_time=original.end_time,
        analysis_mode=AnalysisMode.REPLAY.value,
        replayed_from_analysis_run_id=original.id,
        replay_mode="latest_engine_version",
        include_partial_live_candle=False,
        include_news_correlation=False,
        include_ai_explanation=False,
        status="completed",
        engine_version="engine_v1",
        rule_set_version="rules_v1",
        created_at=BASE_TIME + timedelta(minutes=5),
        updated_at=BASE_TIME + timedelta(minutes=5),
        completed_at=BASE_TIME + timedelta(minutes=5),
    )


def signal_row(signal_id: UUID, workspace_id: UUID, symbol_id: UUID, run_id: UUID) -> Signal:
    candidate_id = uuid4()
    return Signal(
        id=signal_id,
        analysis_run_id=run_id,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe="1m",
        strategy_profile_key="breakout_continuation",
        strategy_profile_version="v1",
        strategy_profile_snapshot_json={"profile": "snapshot"},
        bias="bullish",
        pattern_type="bullish_breakout",
        classification_status="signal",
        confidence_score=Decimal("0.8200"),
        confidence_label="high",
        candidate_strength=Decimal("0.9000"),
        selected_pattern_candidate_id=candidate_id,
        movement_direction="up",
        movement_quality="directional",
        volatility_state="normal",
        trend_state="uptrend",
        range_state="breakout",
        summary="Deterministic signal summary.",
        no_signal_reason=None,
        created_at=BASE_TIME + timedelta(seconds=5),
    )


def feature_snapshot_row(run: AnalysisRun) -> FeatureSnapshot:
    return FeatureSnapshot(
        id=uuid4(),
        analysis_run_id=run.id,
        workspace_id=run.workspace_id,
        symbol_id=run.symbol_id,
        timeframe=run.timeframe,
        start_time=run.start_time,
        end_time=run.end_time,
        features_json={"movement": {"net": "1"}},
        created_at=BASE_TIME + timedelta(seconds=1),
    )


def indicator_snapshot_row(run: AnalysisRun) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        id=uuid4(),
        analysis_run_id=run.id,
        workspace_id=run.workspace_id,
        symbol_id=run.symbol_id,
        timeframe=run.timeframe,
        indicators_json={"rsi": {"value": "55"}},
        created_at=BASE_TIME + timedelta(seconds=2),
    )


def pattern_candidate_row(run: AnalysisRun, candidate_id: UUID | None) -> PatternCandidate:
    return PatternCandidate(
        id=candidate_id or uuid4(),
        analysis_run_id=run.id,
        workspace_id=run.workspace_id,
        symbol_id=run.symbol_id,
        pattern_type="bullish_breakout",
        bias="bullish",
        strength_score=Decimal("0.9000"),
        is_selected=True,
        evidence_json=[{"message": "Stored pattern evidence"}],
        risk_notes_json=[],
        metrics_json={"score": "0.9"},
        created_at=BASE_TIME + timedelta(seconds=3),
    )


def evidence_row(signal_id: UUID, message: str) -> SignalEvidence:
    return SignalEvidence(
        id=uuid4(),
        signal_id=signal_id,
        evidence_type="pattern",
        direction="supports_bullish",
        message=message,
        numeric_value=Decimal("0.8"),
        weight=Decimal("0.80000"),
        metadata_json={},
        created_at=BASE_TIME + timedelta(seconds=6),
    )


def confidence_component_row(signal_id: UUID) -> SignalConfidenceComponent:
    return SignalConfidenceComponent(
        id=uuid4(),
        signal_id=signal_id,
        component_name="pattern_strength",
        component_score=Decimal("0.9000"),
        component_weight=Decimal("0.5000"),
        weighted_score=Decimal("0.45000"),
        reason="Stored confidence component.",
        created_at=BASE_TIME + timedelta(seconds=6),
    )


def risk_note_row(signal_id: UUID) -> SignalRiskNote:
    return SignalRiskNote(
        id=uuid4(),
        signal_id=signal_id,
        code="volatility_expansion",
        message="Stored risk note.",
        severity="medium",
        metadata_json={},
        created_at=BASE_TIME + timedelta(seconds=7),
    )


def explanation_row(signal_id: UUID, run_id: UUID, workspace_id: UUID) -> DeterministicExplanation:
    return DeterministicExplanation(
        id=uuid4(),
        signal_id=signal_id,
        analysis_run_id=run_id,
        workspace_id=workspace_id,
        template_version="deterministic_v1",
        explanation_type=ExplanationType.DETERMINISTIC_SIGNAL.value,
        short_summary="Deterministic explanation summary.",
        market_behavior="Market behavior persisted.",
        evidence_summary="Evidence persisted.",
        confidence_summary="Confidence persisted.",
        risk_summary="Risk persisted.",
        no_signal_summary=None,
        full_text="Read-only market intelligence explanation.",
        source_snapshot_json={},
        safety_status="passed",
        blocked_terms_json=[],
        created_at=BASE_TIME + timedelta(seconds=8),
        updated_at=BASE_TIME + timedelta(seconds=8),
    )


def llm_explanation_row(signal_id: UUID, run_id: UUID, workspace_id: UUID) -> LlmExplanation:
    return LlmExplanation(
        id=uuid4(),
        signal_id=signal_id,
        analysis_run_id=run_id,
        workspace_id=workspace_id,
        provider="mock",
        model="mock-safe",
        prompt_version="v1",
        input_json={},
        output_text="Grounded explanation output.",
        safety_status="passed",
        blocked_terms_json=[],
        grounding_status="grounded",
        grounding_issues_json=[],
        created_at=BASE_TIME + timedelta(seconds=9),
        updated_at=BASE_TIME + timedelta(seconds=9),
    )


def news_correlation_row(
    signal_id: UUID,
    run_id: UUID,
    workspace_id: UUID,
) -> SignalNewsCorrelation:
    return SignalNewsCorrelation(
        id=uuid4(),
        workspace_id=workspace_id,
        analysis_run_id=run_id,
        signal_id=signal_id,
        news_event_id=uuid4(),
        correlation_score=Decimal("0.5000"),
        correlation_label="possible",
        time_delta_minutes=Decimal("3"),
        direction_alignment="aligned",
        volatility_reaction="normal",
        relevance_score=Decimal("0.5000"),
        importance_score=Decimal("0.5000"),
        magnitude_score=Decimal("0.5000"),
        sentiment_score=Decimal("0.5000"),
        reason="Contextual correlation only.",
        metadata_json={},
        created_at=BASE_TIME + timedelta(seconds=10),
    )


def reasoning_run_row(
    reasoning_run_id: UUID,
    workspace_id: UUID,
    run_id: UUID,
    signal_id: UUID,
    outcome_id: UUID,
) -> LlmReasoningRun:
    return LlmReasoningRun(
        id=reasoning_run_id,
        workspace_id=workspace_id,
        analysis_run_id=run_id,
        signal_id=signal_id,
        outcome_id=outcome_id,
        source_type="signal",
        provider="mock",
        model="mock-reasoner",
        prompt_version="v1",
        reasoning_type="next_scenarios",
        status="completed",
        input_snapshot_json={"signalId": str(signal_id)},
        output_json={"summary": "Scenario summary."},
        output_text="Scenario summary.",
        safety_status="passed",
        grounding_status="grounded",
        blocked_terms_json=[],
        grounding_issues_json=[],
        created_at=BASE_TIME + timedelta(seconds=12),
        updated_at=BASE_TIME + timedelta(seconds=12),
    )


def scenario_row(reasoning_run_id: UUID, signal_id: UUID) -> ScenarioHypothesis:
    return ScenarioHypothesis(
        id=uuid4(),
        reasoning_run_id=reasoning_run_id,
        workspace_id=uuid4(),
        analysis_run_id=None,
        signal_id=signal_id,
        scenario_type="continuation",
        scenario_label="Continuation remains possible.",
        possibility_label="uncertain",
        supporting_evidence_json=["Stored evidence"],
        conflicting_evidence_json=[],
        outcome_history_json=None,
        next_observations_json=["Observe final candles"],
        suggested_backend_actions_json=["request_human_review"],
        risk_notes_json=[],
        sort_order=1,
        created_at=BASE_TIME + timedelta(seconds=13),
    )


def action_plan_row(
    plan_id: UUID,
    workspace_id: UUID,
    reasoning_run_id: UUID,
    signal_id: UUID,
    run_id: UUID,
) -> ReasoningActionPlan:
    return ReasoningActionPlan(
        id=plan_id,
        workspace_id=workspace_id,
        source_type="reasoning_run",
        source_id=reasoning_run_id,
        signal_id=signal_id,
        analysis_run_id=run_id,
        reasoning_run_id=reasoning_run_id,
        status="active",
        plan_version="v1",
        created_from="scenario_reasoning",
        summary="Backend follow-up plan.",
        metadata_json={"rejectedActions": ["execute_trade"]},
        created_at=BASE_TIME + timedelta(seconds=14),
        updated_at=BASE_TIME + timedelta(seconds=14),
    )


def action_item_row(plan_id: UUID, workspace_id: UUID, signal_id: UUID) -> ReasoningActionItem:
    return ReasoningActionItem(
        id=uuid4(),
        workspace_id=workspace_id,
        action_plan_id=plan_id,
        source_type="signal",
        source_id=signal_id,
        signal_id=signal_id,
        analysis_run_id=None,
        reasoning_run_id=None,
        action_type="request_human_review",
        status="pending",
        priority="normal",
        due_at=BASE_TIME + timedelta(minutes=10),
        horizon_minutes=None,
        idempotency_key=f"test-{uuid4()}",
        input_json={},
        result_json=None,
        attempts=0,
        max_attempts=3,
        created_at=BASE_TIME + timedelta(seconds=15),
        updated_at=BASE_TIME + timedelta(seconds=15),
    )


def outcome_row(outcome_id: UUID, signal: Signal) -> SignalOutcome:
    return SignalOutcome(
        id=outcome_id,
        workspace_id=signal.workspace_id,
        analysis_run_id=signal.analysis_run_id,
        signal_id=signal.id,
        symbol_id=signal.symbol_id,
        timeframe=signal.timeframe,
        strategy_profile_key=signal.strategy_profile_key,
        strategy_profile_version=signal.strategy_profile_version,
        pattern_type=signal.pattern_type,
        bias=signal.bias,
        classification_status=signal.classification_status,
        horizon_minutes=15,
        evaluation_status=OutcomeEvaluationStatus.EVALUATED.value,
        reference_time=BASE_TIME,
        reference_price=Decimal("1.1000"),
        future_window_start=BASE_TIME + timedelta(minutes=1),
        future_window_end=BASE_TIME + timedelta(minutes=15),
        future_candle_count=15,
        max_favorable_move=Decimal("0.0020"),
        max_adverse_move=Decimal("0.0005"),
        net_move=Decimal("0.0015"),
        max_favorable_pips=Decimal("20"),
        max_adverse_pips=Decimal("5"),
        net_pips=Decimal("15"),
        max_favorable_ticks=Decimal("200"),
        max_adverse_ticks=Decimal("50"),
        net_ticks=Decimal("150"),
        direction_followed=True,
        reversal_detected=False,
        outcome_label=OutcomeLabel.CONTINUATION.value,
        movement_quality="follow_through",
        evaluation_version="v1",
        metadata_json={},
        created_at=BASE_TIME + timedelta(seconds=11),
        updated_at=BASE_TIME + timedelta(seconds=11),
    )


def chart_run_row(
    run_id: UUID,
    workspace_id: UUID,
    source_id: UUID,
    symbol_id: UUID,
    analysis_run_id: UUID,
) -> ChartScreenshotRun:
    return ChartScreenshotRun(
        id=run_id,
        workspace_id=workspace_id,
        source_id=source_id,
        symbol_id=symbol_id,
        analysis_run_id=analysis_run_id,
        timeframe="1m",
        file_name="chart.png",
        parser_name="manual",
        parser_version="v1",
        parser_source_path=None,
        status="completed",
        extraction_confidence=Decimal("0.8500"),
        raw_candle_count=10,
        stored_candle_count=10,
        duplicate_count=0,
        conflict_count=0,
        analysis_hypothesis="bullish",
        analysis_hypothesis_confidence=Decimal("0.8000"),
        extracted_window_start=BASE_TIME - timedelta(minutes=10),
        extracted_window_end=BASE_TIME,
        extracted_payload_json={"trendMetrics": {"direction": "up"}},
        extraction_warnings_json={"warnings": []},
        parser_metadata_json={
            "chartType": "candlestick",
            "ocr": {"status": "not_configured"},
            "humanReview": {"status": "accepted"},
        },
        created_at=BASE_TIME + timedelta(seconds=4),
        updated_at=BASE_TIME + timedelta(seconds=16),
        started_at=BASE_TIME + timedelta(seconds=4),
        completed_at=BASE_TIME + timedelta(seconds=16),
    )


def chart_correction_row(
    run_id: UUID,
    original: ChartScreenshotRun,
    workspace_id: UUID,
) -> ChartScreenshotRun:
    assert original.analysis_run_id is not None
    item = chart_run_row(
        run_id,
        workspace_id,
        original.source_id,
        original.symbol_id,
        original.analysis_run_id,
    )
    item.parser_source_path = f"correction:{original.id}"
    item.parser_metadata_json = {"correctedFromChartScreenshotRunId": str(original.id)}
    return item


def scheduled_scan_run_row(
    run_id: UUID,
    workspace_id: UUID,
    analysis_run_id: UUID,
    signal_id: UUID,
) -> ScheduledScanRun:
    return ScheduledScanRun(
        id=run_id,
        workspace_id=workspace_id,
        scan_config_id=uuid4(),
        status="completed",
        scan_mode="single_symbol",
        scheduled_for=BASE_TIME,
        started_at=BASE_TIME + timedelta(seconds=18),
        completed_at=BASE_TIME + timedelta(seconds=19),
        scanned_item_count=1,
        analysis_run_count=1,
        skipped_count=0,
        failed_count=0,
        analysis_run_ids_json=[str(analysis_run_id)],
        signal_ids_json=[str(signal_id)],
        reasoning_run_ids_json=None,
        action_plan_ids_json=None,
        result_json={"safeBackendAnalysis": True},
        error_message=None,
        created_at=BASE_TIME + timedelta(seconds=18),
        updated_at=BASE_TIME + timedelta(seconds=19),
    )


def scheduled_scan_item_row(
    item_id: UUID,
    workspace_id: UUID,
    scan_run_id: UUID,
    scan_config_id: UUID,
    run: AnalysisRun,
    signal: Signal,
) -> ScheduledScanRunItem:
    return ScheduledScanRunItem(
        id=item_id,
        workspace_id=workspace_id,
        scan_run_id=scan_run_id,
        scan_config_id=scan_config_id,
        watchlist_item_id=None,
        symbol_id=run.symbol_id,
        source_id=run.source_id,
        timeframe=run.timeframe,
        status="completed",
        analysis_run_id=run.id,
        signal_id=signal.id,
        reasoning_run_id=None,
        action_plan_id=None,
        skipped_reason=None,
        error_message=None,
        created_at=BASE_TIME + timedelta(seconds=20),
        updated_at=BASE_TIME + timedelta(seconds=20),
    )


def quality_run_row(
    run_id: UUID,
    workspace_id: UUID,
    analysis_run_id: UUID,
    signal_id: UUID,
) -> IntelligenceQualityRun:
    return IntelligenceQualityRun(
        id=run_id,
        workspace_id=workspace_id,
        analysis_run_id=analysis_run_id,
        signal_id=signal_id,
        source_type="signal",
        status="completed",
        quality_score=Decimal("0.8750"),
        quality_label="acceptable",
        gate_version="quality_gates_v1",
        shadow_version="shadow_profiles_v1",
        checked_at=BASE_TIME + timedelta(seconds=21),
        summary="Diagnostic quality run.",
        metadata_json={"diagnosticOnly": True},
        created_at=BASE_TIME + timedelta(seconds=21),
        updated_at=BASE_TIME + timedelta(seconds=21),
    )


def quality_finding_row(
    finding_id: UUID,
    run: IntelligenceQualityRun,
) -> IntelligenceQualityFinding:
    return IntelligenceQualityFinding(
        id=finding_id,
        workspace_id=run.workspace_id,
        quality_run_id=run.id,
        finding_type="review_recommendation",
        severity="medium",
        code="review_context",
        title="Review context",
        message="Review persisted diagnostic context.",
        artifact_type="signal",
        artifact_id=run.signal_id,
        expected_value=None,
        observed_value=None,
        metadata_json={},
        created_at=BASE_TIME + timedelta(seconds=22),
    )


def shadow_result_row(
    result_id: UUID,
    quality_run: IntelligenceQualityRun,
    analysis_run: AnalysisRun,
    signal: Signal,
) -> ShadowClassificationResult:
    return ShadowClassificationResult(
        id=result_id,
        workspace_id=quality_run.workspace_id,
        quality_run_id=quality_run.id,
        analysis_run_id=analysis_run.id,
        signal_id=signal.id,
        strategy_profile_key=signal.strategy_profile_key,
        strategy_profile_version=signal.strategy_profile_version,
        classification_status=signal.classification_status,
        bias=signal.bias,
        pattern_type=signal.pattern_type,
        confidence_score=signal.confidence_score,
        confidence_label=signal.confidence_label,
        selected_candidate_id=signal.selected_pattern_candidate_id,
        agreement_with_final="agreed",
        disagreement_reason=None,
        metadata_json={"diagnosticOnly": True},
        created_at=BASE_TIME + timedelta(seconds=23),
    )


def audit_log_row(run_id: UUID) -> AnalysisAuditLog:
    return AnalysisAuditLog(
        id=uuid4(),
        analysis_run_id=run_id,
        event_type="signal_classification_completed",
        message="Signal classification completed.",
        metadata_json={},
        created_at=BASE_TIME + timedelta(seconds=17),
    )
