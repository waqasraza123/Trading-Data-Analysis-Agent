from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import (
    AnalysisAuditLog,
    AnalysisMode,
    AnalysisRun,
    AnalysisRunStatus,
)
from app.modules.explanations.models import (
    DeterministicExplanation,
    ExplanationSafetyStatus,
    ExplanationType,
)
from app.modules.intelligence_reports.sections import (
    BANNED_REPORT_PHRASES,
    bounded_items,
    report_contains_banned_phrase,
    to_report_value,
)
from app.modules.intelligence_reports.service import IntelligenceReportService
from app.modules.llm_explanations.models import (
    LlmExplanation,
    LlmExplanationGroundingStatus,
    LlmExplanationSafetyStatus,
)
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.reasoning.models import (
    LlmReasoningRun,
    ReasoningGroundingStatus,
    ReasoningRunStatus,
    ReasoningSafetyStatus,
    ReasoningSourceType,
    ReasoningType,
    ScenarioHypothesis,
    ScenarioPossibilityLabel,
    ScenarioType,
)
from app.modules.signals.models import (
    Signal,
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceComponent,
    SignalConfidenceLabel,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.symbols.models import MarketType, Symbol

BASE_TIME = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)


class FakeIntelligenceReportRepository:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.symbol_id = uuid4()
        self.analysis_run_id = uuid4()
        self.signal_id = uuid4()
        self.reasoning_run_id = uuid4()
        self.outcome_id = uuid4()
        self.signal = signal_row(
            self.signal_id,
            self.workspace_id,
            self.symbol_id,
            self.analysis_run_id,
        )
        self.symbol = symbol_row(self.symbol_id)
        self.analysis_run = analysis_run_row(
            self.analysis_run_id,
            self.workspace_id,
            self.symbol_id,
        )
        self.components = [component_row(self.signal_id, "pattern_strength", "0.9000")]
        self.evidence = [evidence_row(self.signal_id, "pattern", "Breakout evidence stored.")]
        self.risk_notes = [risk_note_row(self.signal_id)]
        self.explanation: DeterministicExplanation | None = explanation_row(
            self.signal_id,
            self.analysis_run_id,
            self.workspace_id,
        )
        self.llm_explanation: LlmExplanation | None = None
        self.reasoning_run: LlmReasoningRun | None = None
        self.scenarios: list[ScenarioHypothesis] = []
        self.outcomes: list[SignalOutcome] = [outcome_row(self.outcome_id, self.signal)]
        self.audit_logs = [audit_row(self.analysis_run_id)]

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return self.signal if signal_id == self.signal.id else None

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return self.analysis_run if analysis_run_id == self.analysis_run.id else None

    async def get_symbol(self, symbol_id: UUID) -> Symbol | None:
        return self.symbol if symbol_id == self.symbol.id else None

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        return self.signal if analysis_run_id == self.signal.analysis_run_id else None

    async def list_confidence_components(
        self,
        signal_id: UUID,
    ) -> list[SignalConfidenceComponent]:
        return self.components if signal_id == self.signal.id else []

    async def list_evidence(self, signal_id: UUID) -> list[SignalEvidence]:
        return self.evidence if signal_id == self.signal.id else []

    async def list_risk_notes(self, signal_id: UUID) -> list[SignalRiskNote]:
        return self.risk_notes if signal_id == self.signal.id else []

    async def get_deterministic_explanation_by_signal_id(
        self,
        signal_id: UUID,
    ) -> DeterministicExplanation | None:
        return self.explanation if signal_id == self.signal.id else None

    async def get_deterministic_explanation_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> DeterministicExplanation | None:
        return self.explanation if analysis_run_id == self.analysis_run.id else None

    async def get_llm_explanation_by_signal_id(self, signal_id: UUID) -> LlmExplanation | None:
        return self.llm_explanation if signal_id == self.signal.id else None

    async def list_news_correlations_by_signal_id(self, signal_id: UUID) -> list[object]:
        return []

    async def list_news_correlations_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> list[object]:
        return []

    async def list_news_events(self, news_event_ids: list[UUID]) -> list[object]:
        return []

    async def get_latest_reasoning_run_by_signal_id(
        self,
        signal_id: UUID,
    ) -> LlmReasoningRun | None:
        return self.reasoning_run if signal_id == self.signal.id else None

    async def get_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun | None:
        return self.reasoning_run if self.reasoning_run_id == reasoning_run_id else None

    async def list_scenario_hypotheses(self, reasoning_run_id: UUID) -> list[ScenarioHypothesis]:
        return self.scenarios if reasoning_run_id == self.reasoning_run_id else []

    async def get_latest_action_plan_by_reasoning_run_id(self, reasoning_run_id: UUID) -> None:
        return None

    async def get_latest_action_plan_by_signal_id(self, signal_id: UUID) -> None:
        return None

    async def get_latest_action_plan_by_analysis_run_id(self, analysis_run_id: UUID) -> None:
        return None

    async def list_action_items(self, action_plan_id: UUID) -> list[object]:
        return []

    async def list_signal_outcomes(self, signal_id: UUID) -> list[SignalOutcome]:
        return self.outcomes if signal_id == self.signal.id else []

    async def list_analysis_outcomes(self, analysis_run_id: UUID) -> list[SignalOutcome]:
        return self.outcomes if analysis_run_id == self.analysis_run.id else []

    async def get_outcome(self, outcome_id: UUID) -> SignalOutcome | None:
        for outcome in self.outcomes:
            if outcome.id == outcome_id:
                return outcome
        return None

    async def list_historical_outcomes(
        self,
        workspace_id: UUID,
        horizon_minutes: int,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        pattern_type: str | None = None,
        strategy_profile_key: str | None = None,
        limit: int = 1000,
    ) -> list[SignalOutcome]:
        return [outcome for outcome in self.outcomes if outcome.horizon_minutes == horizon_minutes]

    async def get_feature_snapshot(self, analysis_run_id: UUID) -> None:
        return None

    async def get_indicator_snapshot(self, analysis_run_id: UUID) -> None:
        return None

    async def list_pattern_candidates(self, analysis_run_id: UUID) -> list[object]:
        return []

    async def list_audit_logs(self, analysis_run_id: UUID) -> list[AnalysisAuditLog]:
        return self.audit_logs if analysis_run_id == self.analysis_run.id else []

    async def count_candles_for_run(self, run: AnalysisRun) -> int:
        return 42

    async def list_optional_strategy_profile_diagnostics(
        self,
        workspace_id: UUID,
        strategy_profile_key: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        return []

    async def list_optional_pattern_diagnostics(
        self,
        workspace_id: UUID,
        pattern_type: str | None,
        strategy_profile_key: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        return []

    async def list_optional_calibration_recommendations(
        self,
        workspace_id: UUID,
        strategy_profile_key: str | None,
        pattern_type: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        return []

    async def list_chart_screenshot_runs_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> list[object]:
        return []


@pytest.mark.anyio
async def test_signal_report_includes_core_sections() -> None:
    service, repository = service_with_fake_repository()

    report = await service.build_signal_report(repository.signal.id)

    assert report.sections["summary"]["signal_id"] == str(repository.signal.id)
    assert report.sections["evidence"]["returned_count"] == 1
    assert report.sections["confidence"]["highest_component"]["component_name"] == (
        "pattern_strength"
    )
    assert report.sections["risk"]["risk_notes"]["returned_count"] == 1


@pytest.mark.anyio
async def test_signal_report_handles_missing_optional_sections() -> None:
    service, repository = service_with_fake_repository()
    repository.explanation = None
    repository.outcomes = []

    report = await service.build_signal_report(repository.signal.id)

    assert "deterministic_explanation" in report.missing_sections
    assert "news_correlation" in report.missing_sections
    assert "scenario_reasoning" in report.missing_sections
    assert "outcomes" in report.missing_sections
    assert "historical_behavior.profile_diagnostics" in report.missing_sections


@pytest.mark.anyio
async def test_analysis_run_report_references_signal_summary() -> None:
    service, repository = service_with_fake_repository()

    report = await service.build_analysis_run_report(repository.analysis_run.id)

    assert report.sections["signal"]["signal_id"] == str(repository.signal.id)
    assert report.sections["candle_source_context"]["final_candle_count"] == 42


@pytest.mark.anyio
async def test_reasoning_run_report_includes_scenario_hypotheses() -> None:
    service, repository = service_with_fake_repository()
    repository.reasoning_run = reasoning_run_row(
        repository.reasoning_run_id,
        repository.workspace_id,
        repository.analysis_run_id,
        repository.signal_id,
    )
    repository.scenarios = [scenario_row(repository.reasoning_run_id, repository.signal_id)]

    report = await service.build_reasoning_run_report(repository.reasoning_run_id)

    assert report.sections["scenario_hypotheses"]["returned_count"] == 1
    assert report.sections["suggested_backend_actions"]["items"][0]["action"] == (
        "request_human_review"
    )


@pytest.mark.anyio
async def test_outcome_report_uses_safe_terminology() -> None:
    service, repository = service_with_fake_repository()

    report = await service.build_outcome_report(outcome_id=repository.outcome_id)
    serialized = str(report.model_dump(mode="json", by_alias=True)).lower()

    assert "continuation" in serialized
    assert "profit" not in serialized
    assert "pnl" not in serialized
    assert "trade result" not in serialized


def test_report_truncation_metadata() -> None:
    section = bounded_items(list(range(60)), 50)

    assert section["returned_count"] == 50
    assert section["total_count"] == 60
    assert section["truncated"] is True


def test_report_redaction_removes_secrets_and_banned_phrases() -> None:
    payload = to_report_value(
        {
            "apiKey": "secret-value",
            "databaseUrl": "postgresql://secret",
            "message": "buy now with guaranteed profit",
            "candles": [{"open": "1"}],
        }
    )

    serialized = str(payload).lower()
    assert "secret-value" not in serialized
    assert "postgresql://secret" not in serialized
    assert "buy now" not in serialized
    assert "guaranteed profit" not in serialized


@pytest.mark.anyio
async def test_blocked_llm_output_is_not_exposed() -> None:
    service, repository = service_with_fake_repository()
    repository.llm_explanation = blocked_llm_explanation_row(
        repository.signal_id,
        repository.analysis_run_id,
        repository.workspace_id,
    )

    report = await service.build_signal_report(repository.signal.id)
    llm_section = report.sections["llm_explanation"]
    serialized = str(report.model_dump(mode="json", by_alias=True)).lower()

    assert llm_section["output_text"] is None
    assert llm_section["unsafe_output_redacted"] is True
    assert "buy now" not in serialized
    assert "guaranteed profit" not in serialized


@pytest.mark.anyio
async def test_no_report_contains_banned_trade_advice_phrases() -> None:
    service, repository = service_with_fake_repository()
    repository.llm_explanation = blocked_llm_explanation_row(
        repository.signal_id,
        repository.analysis_run_id,
        repository.workspace_id,
    )
    repository.evidence = [evidence_row(repository.signal_id, "pattern", "place order now")]

    report = await service.build_signal_report(repository.signal.id)

    assert not report_contains_banned_phrase(report.model_dump(mode="json", by_alias=True))
    for phrase in BANNED_REPORT_PHRASES:
        assert phrase not in str(report.model_dump(mode="json", by_alias=True)).lower()


def service_with_fake_repository() -> tuple[
    IntelligenceReportService,
    FakeIntelligenceReportRepository,
]:
    repository = FakeIntelligenceReportRepository()
    service = IntelligenceReportService(cast(AsyncSession, object()))
    service.repository = repository  # type: ignore[assignment]
    return service, repository


def signal_row(
    signal_id: UUID,
    workspace_id: UUID,
    symbol_id: UUID,
    analysis_run_id: UUID,
) -> Signal:
    return Signal(
        id=signal_id,
        analysis_run_id=analysis_run_id,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe="1m",
        strategy_profile_key="breakout_continuation",
        strategy_profile_version="v1",
        bias=SignalBias.BULLISH.value,
        pattern_type="bullish_breakout",
        classification_status=SignalClassificationStatus.SIGNAL.value,
        confidence_score=Decimal("0.8200"),
        confidence_label=SignalConfidenceLabel.HIGH.value,
        summary="Deterministic backend classified bullish continuation.",
        no_signal_reason=None,
        created_at=BASE_TIME,
    )


def symbol_row(symbol_id: UUID) -> Symbol:
    return Symbol(
        id=symbol_id,
        symbol="EURUSD",
        display_name="EUR/USD",
        market_type=MarketType.FOREX.value,
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        price_precision=5,
        quantity_precision=2,
        is_active=True,
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )


def analysis_run_row(analysis_run_id: UUID, workspace_id: UUID, symbol_id: UUID) -> AnalysisRun:
    return AnalysisRun(
        id=analysis_run_id,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe="1m",
        start_time=BASE_TIME - timedelta(minutes=30),
        end_time=BASE_TIME,
        analysis_mode=AnalysisMode.HISTORICAL.value,
        include_partial_live_candle=False,
        include_news_correlation=True,
        include_ai_explanation=True,
        status=AnalysisRunStatus.COMPLETED.value,
        engine_version="test_engine",
        rule_set_version="test_rules",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
        completed_at=BASE_TIME,
    )


def component_row(signal_id: UUID, name: str, score: str) -> SignalConfidenceComponent:
    return SignalConfidenceComponent(
        id=uuid4(),
        signal_id=signal_id,
        component_name=name,
        component_score=Decimal(score),
        component_weight=Decimal("0.5000"),
        weighted_score=Decimal("0.45000"),
        reason="Persisted confidence component.",
        created_at=BASE_TIME,
    )


def evidence_row(signal_id: UUID, evidence_type: str, message: str) -> SignalEvidence:
    return SignalEvidence(
        id=uuid4(),
        signal_id=signal_id,
        evidence_type=evidence_type,
        direction="supports_bullish",
        message=message,
        numeric_value=Decimal("0.8"),
        weight=Decimal("0.80000"),
        metadata_json={},
        created_at=BASE_TIME,
    )


def risk_note_row(signal_id: UUID) -> SignalRiskNote:
    return SignalRiskNote(
        id=uuid4(),
        signal_id=signal_id,
        code="volatility_expansion",
        message="Stored risk note.",
        severity="medium",
        metadata_json={},
        created_at=BASE_TIME,
    )


def explanation_row(
    signal_id: UUID,
    analysis_run_id: UUID,
    workspace_id: UUID,
) -> DeterministicExplanation:
    return DeterministicExplanation(
        id=uuid4(),
        signal_id=signal_id,
        analysis_run_id=analysis_run_id,
        workspace_id=workspace_id,
        template_version="deterministic_v1",
        explanation_type=ExplanationType.DETERMINISTIC_SIGNAL.value,
        short_summary="Deterministic explanation summary.",
        market_behavior="Market behavior was persisted.",
        evidence_summary="Evidence summary was persisted.",
        confidence_summary="Confidence summary was persisted.",
        risk_summary="Risk summary was persisted.",
        no_signal_summary=None,
        full_text="This is a market-analysis artifact, not a trade instruction.",
        source_snapshot_json={},
        safety_status=ExplanationSafetyStatus.PASSED.value,
        blocked_terms_json=[],
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )


def blocked_llm_explanation_row(
    signal_id: UUID,
    analysis_run_id: UUID,
    workspace_id: UUID,
) -> LlmExplanation:
    return LlmExplanation(
        id=uuid4(),
        signal_id=signal_id,
        analysis_run_id=analysis_run_id,
        workspace_id=workspace_id,
        provider="mock",
        model="mock-safe",
        prompt_version="v1",
        input_json={"apiKey": "secret"},
        output_text="buy now for guaranteed profit",
        safety_status=LlmExplanationSafetyStatus.BLOCKED.value,
        blocked_terms_json=["buy now", "guaranteed profit"],
        grounding_status=LlmExplanationGroundingStatus.FAILED.value,
        grounding_issues_json=["unsafe output"],
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )


def reasoning_run_row(
    reasoning_run_id: UUID,
    workspace_id: UUID,
    analysis_run_id: UUID,
    signal_id: UUID,
) -> LlmReasoningRun:
    return LlmReasoningRun(
        id=reasoning_run_id,
        workspace_id=workspace_id,
        analysis_run_id=analysis_run_id,
        signal_id=signal_id,
        source_type=ReasoningSourceType.SIGNAL.value,
        provider="mock",
        model="mock-reasoner",
        prompt_version="v1",
        reasoning_type=ReasoningType.NEXT_SCENARIOS.value,
        status=ReasoningRunStatus.COMPLETED.value,
        input_snapshot_json={"signalId": str(signal_id)},
        output_json={"summary": "Scenario reasoning summary."},
        output_text="Scenario reasoning summary.",
        safety_status=ReasoningSafetyStatus.PASSED.value,
        grounding_status=ReasoningGroundingStatus.GROUNDED.value,
        blocked_terms_json=[],
        grounding_issues_json=[],
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )


def scenario_row(reasoning_run_id: UUID, signal_id: UUID) -> ScenarioHypothesis:
    return ScenarioHypothesis(
        id=uuid4(),
        reasoning_run_id=reasoning_run_id,
        workspace_id=uuid4(),
        analysis_run_id=None,
        signal_id=signal_id,
        scenario_type=ScenarioType.CONTINUATION.value,
        scenario_label="Continuation remains possible.",
        possibility_label=ScenarioPossibilityLabel.UNCERTAIN.value,
        supporting_evidence_json=["Stored evidence"],
        conflicting_evidence_json=[],
        outcome_history_json=None,
        next_observations_json=["Observe final candles"],
        suggested_backend_actions_json=["request_human_review"],
        risk_notes_json=[],
        sort_order=1,
        created_at=BASE_TIME,
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
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )


def audit_row(analysis_run_id: UUID) -> AnalysisAuditLog:
    return AnalysisAuditLog(
        id=uuid4(),
        analysis_run_id=analysis_run_id,
        event_type="signal_classification_completed",
        message="Signal classification completed.",
        metadata_json={},
        created_at=BASE_TIME,
    )
