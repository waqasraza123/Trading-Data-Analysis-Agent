from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.analysis.models import AnalysisMode, AnalysisRun, AnalysisRunStatus
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.explanations.models import (
    DeterministicExplanation,
    ExplanationSafetyStatus,
    ExplanationType,
)
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.intelligence_quality.gates import (
    SUPPORTED_SAFE_ACTIONS,
    FindingDraft,
    IntelligenceQualityGateService,
    score_findings,
)
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFinding,
    IntelligenceQualityLabel,
    IntelligenceQualityRun,
    IntelligenceQualityRunStatus,
    IntelligenceQualitySourceType,
    ShadowClassificationResult,
)
from app.modules.intelligence_quality.repository import (
    IntelligenceQualityArtifacts,
    IntelligenceQualityRepository,
)
from app.modules.intelligence_quality.routes import (
    get_intelligence_quality_service,
)
from app.modules.intelligence_quality.routes import (
    router as intelligence_quality_router,
)
from app.modules.intelligence_quality.schemas import (
    IntelligenceQualityResponse,
    IntelligenceQualityRunRead,
)
from app.modules.intelligence_quality.service import IntelligenceQualityService
from app.modules.intelligence_quality.shadow import ShadowClassificationService
from app.modules.llm_explanations.models import (
    LlmExplanation,
    LlmExplanationGroundingStatus,
    LlmExplanationSafetyStatus,
)
from app.modules.news.models import (
    DirectionAlignment,
    SignalNewsCorrelation,
    VolatilityReaction,
)
from app.modules.outcomes.models import (
    OutcomeEvaluationStatus,
    OutcomeLabel,
    SignalOutcome,
)
from app.modules.patterns.models import PatternCandidate
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
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.strategy_profiles.seeds import DEFAULT_STRATEGY_PROFILES

NOW = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)


def test_missing_required_artifacts_create_findings() -> None:
    findings = IntelligenceQualityGateService().run_gates(
        IntelligenceQualityArtifacts(),
        require_signal=True,
    )

    codes = {finding.code for finding in findings}

    assert "missing_analysis_run" in codes
    assert "missing_signal" in codes
    assert "missing_feature_snapshot" in codes
    assert "missing_pattern_candidates" in codes


def test_selected_candidate_pattern_mismatch_creates_finding() -> None:
    artifacts = complete_artifacts()
    signal = require_signal(artifacts)
    signal.pattern_type = "bearish_breakdown"
    signal.bias = SignalBias.BEARISH.value

    findings = IntelligenceQualityGateService().signal_candidate_findings(artifacts)

    assert {finding.code for finding in findings} >= {
        "selected_candidate_pattern_mismatch",
        "selected_candidate_bias_mismatch",
    }


def test_confidence_weighted_sum_mismatch_creates_finding() -> None:
    artifacts = complete_artifacts()
    artifacts.confidence_components[0].weighted_score = Decimal("0.10000")

    findings = IntelligenceQualityGateService().confidence_findings(artifacts)

    assert "confidence_component_weight_mismatch" in {finding.code for finding in findings}
    assert "confidence_total_mismatch" in {finding.code for finding in findings}


def test_confidence_label_mismatch_creates_finding() -> None:
    artifacts = complete_artifacts()
    require_signal(artifacts).confidence_label = SignalConfidenceLabel.LOW.value

    findings = IntelligenceQualityGateService().confidence_findings(artifacts)

    assert "confidence_label_mismatch" in {finding.code for finding in findings}


def test_evidence_direction_conflict_creates_finding() -> None:
    artifacts = complete_artifacts()
    artifacts.evidence = [
        evidence_row(require_signal(artifacts).id, "supports_bearish", Decimal("1.00000"))
    ]
    artifacts.risk_notes = []

    findings = IntelligenceQualityGateService().evidence_findings(artifacts)

    assert "evidence_direction_conflict" in {finding.code for finding in findings}


def test_unsafe_explanation_language_creates_finding_without_echoing_phrase() -> None:
    artifacts = complete_artifacts()
    explanation = require_explanation(artifacts)
    explanation.full_text = "This says buy now with guaranteed movement."

    findings = IntelligenceQualityGateService().explanation_findings(artifacts)
    messages = " ".join(finding.message.lower() for finding in findings)

    assert "unsafe_explanation_language" in {finding.code for finding in findings}
    assert "buy now" not in messages
    assert "guaranteed" not in messages


def test_news_causation_language_creates_finding() -> None:
    artifacts = complete_artifacts()
    artifacts.news_correlations = [news_correlation_row(require_signal(artifacts).id)]

    findings = IntelligenceQualityGateService().news_findings(artifacts)

    assert "news_correlation_causation_language" in {finding.code for finding in findings}


def test_no_signal_reason_summary_conflict_creates_finding() -> None:
    artifacts = complete_artifacts()
    signal = require_signal(artifacts)
    signal.classification_status = SignalClassificationStatus.NO_SIGNAL.value
    signal.bias = SignalBias.NEUTRAL.value
    signal.no_signal_reason = "fakeout_risk"
    signal.summary = "Clean breakout summary."

    findings = IntelligenceQualityGateService().risk_confidence_findings(artifacts)

    assert "no_signal_reason_summary_conflict" in {finding.code for finding in findings}


def test_outcome_mismatch_creates_finding() -> None:
    artifacts = complete_artifacts()
    outcome = outcome_row(require_signal(artifacts))
    outcome.bias = SignalBias.BEARISH.value
    artifacts.outcomes = [outcome]

    findings = IntelligenceQualityGateService().outcome_findings(artifacts)

    assert "outcome_bias_mismatch" in {finding.code for finding in findings}


def test_quality_gates_use_backend_safe_action_names() -> None:
    assert {
        "evaluate_outcome_after_horizon",
        "run_replay",
        "run_news_correlation",
        "wait_for_more_final_candles",
        "request_human_review",
        "no_action",
    } <= SUPPORTED_SAFE_ACTIONS
    assert "replay_analysis" not in SUPPORTED_SAFE_ACTIONS
    assert "human_review" not in SUPPORTED_SAFE_ACTIONS


def test_chart_screenshot_review_metadata_creates_diagnostic_finding() -> None:
    artifacts = complete_artifacts()
    signal = require_signal(artifacts)
    artifacts.chart_screenshot_runs = [
        ChartScreenshotRun(
            id=uuid4(),
            workspace_id=signal.workspace_id,
            source_id=None,
            symbol_id=signal.symbol_id,
            analysis_run_id=signal.analysis_run_id,
            timeframe=signal.timeframe,
            file_name="chart.png",
            parser_name="opencv",
            parser_version="v1",
            status="review_required",
            extraction_confidence=Decimal("0.4000"),
            raw_candle_count=20,
            stored_candle_count=0,
            duplicate_count=0,
            conflict_count=0,
            extracted_payload_json={},
            extraction_warnings_json={"warnings": []},
            parser_metadata_json={
                "chartType": "line",
                "supportedForAnalysis": False,
                "analysisBlockedReason": "unsupported_chart_type",
                "ocr": {"status": "failed"},
            },
            created_at=NOW,
            updated_at=NOW,
        )
    ]

    findings = IntelligenceQualityGateService().chart_screenshot_findings(artifacts)
    codes = {finding.code for finding in findings}

    assert "unsupported_chart_source_context" in codes
    assert "chart_screenshot_review_required" in codes
    assert "chart_ocr_failed_context" in codes


def test_quality_score_labels() -> None:
    strong = score_findings([])
    acceptable = score_findings(
        [
            finding_stub("low", "one"),
            finding_stub("low", "two"),
            finding_stub("low", "three"),
            finding_stub("low", "four"),
        ]
    )
    review = score_findings([finding_stub("high", "one"), finding_stub("high", "two")])
    inconsistent = score_findings(
        [
            finding_stub("high", "one"),
            finding_stub("high", "two"),
            finding_stub("high", "three"),
        ]
    )

    assert strong.quality_label == IntelligenceQualityLabel.STRONG.value
    assert acceptable.quality_label == IntelligenceQualityLabel.ACCEPTABLE.value
    assert review.quality_label == IntelligenceQualityLabel.REVIEW_RECOMMENDED.value
    assert inconsistent.quality_label == IntelligenceQualityLabel.INCONSISTENT.value


def test_shadow_classification_agreement() -> None:
    artifacts = complete_artifacts()
    profile = profile_from_key("breakout_continuation")

    outcome = ShadowClassificationService().evaluate_profiles(artifacts, [profile])

    assert outcome.results[0].agreement_with_final == "agreed"


def test_shadow_classification_bias_disagreement() -> None:
    artifacts = complete_artifacts()
    require_signal(artifacts).bias = SignalBias.BEARISH.value
    profile = profile_from_key("breakout_continuation")

    outcome = ShadowClassificationService().evaluate_profiles(artifacts, [profile])

    assert outcome.results[0].agreement_with_final == "disagreed_bias"


def test_shadow_classification_no_candidate() -> None:
    artifacts = complete_artifacts()
    artifacts.pattern_candidates = []
    profile = profile_from_key("breakout_continuation")

    outcome = ShadowClassificationService().evaluate_profiles(artifacts, [profile])

    assert outcome.results[0].agreement_with_final == "no_candidate"


@pytest.mark.anyio
async def test_quality_run_idempotency_returns_existing_run() -> None:
    service, repository, _session = service_with_fake_repository()
    existing = quality_run_row(
        repository.workspace_id,
        repository.analysis_run_id,
        repository.signal_id,
    )
    repository.latest_signal_run = existing

    response = await service.run_for_signal(
        repository.signal_id,
        include_shadow_classification=True,
        force_recompute=False,
    )

    assert response.quality_run.id == existing.id
    assert repository.created_runs == []


@pytest.mark.anyio
async def test_force_recompute_creates_new_run() -> None:
    service, repository, _session = service_with_fake_repository()
    repository.latest_signal_run = quality_run_row(
        repository.workspace_id,
        repository.analysis_run_id,
        repository.signal_id,
    )

    response = await service.run_for_signal(
        repository.signal_id,
        include_shadow_classification=True,
        force_recompute=True,
    )

    assert response.quality_run.id != repository.latest_signal_run.id
    assert len(repository.created_runs) == 1


@pytest.mark.anyio
async def test_service_persists_findings_and_shadow_results() -> None:
    service, repository, session = service_with_fake_repository()

    response = await service.run_for_signal(
        repository.signal_id,
        include_shadow_classification=True,
        force_recompute=False,
    )

    assert response.quality_run.signal_id == repository.signal_id
    assert response.findings
    assert response.shadow_classifications
    assert session.committed is True


@pytest.mark.anyio
async def test_service_runs_quality_for_analysis_run() -> None:
    service, repository, _session = service_with_fake_repository()

    response = await service.run_for_analysis_run(
        repository.analysis_run_id,
        include_shadow_classification=False,
        force_recompute=False,
    )

    assert response.quality_run.analysis_run_id == repository.analysis_run_id
    assert response.shadow_classifications == []


@pytest.mark.anyio
async def test_run_signal_quality_api_contract() -> None:
    signal_id = uuid4()
    fake_service = FakeRouteQualityService(signal_id)
    app = FastAPI()
    app.include_router(intelligence_quality_router)
    app.dependency_overrides[get_intelligence_quality_service] = lambda: fake_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/intelligence-quality/signals/{signal_id}/run",
            json={"includeShadowClassification": True, "forceRecompute": False},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["qualityRun"]["signalId"] == str(signal_id)
    assert payload["qualityRun"]["qualityLabel"] == IntelligenceQualityLabel.STRONG.value


@pytest.mark.anyio
async def test_quality_findings_api_contract() -> None:
    signal_id = uuid4()
    fake_service = FakeRouteQualityService(signal_id)
    app = FastAPI()
    app.include_router(intelligence_quality_router)
    app.dependency_overrides[get_intelligence_quality_service] = lambda: fake_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/intelligence-quality/runs/{fake_service.run_id}/findings")

    assert response.status_code == 200
    assert response.json() == []


def complete_artifacts() -> IntelligenceQualityArtifacts:
    workspace_id = uuid4()
    symbol_id = uuid4()
    analysis_run_id = uuid4()
    signal_id = uuid4()
    candidate_id = uuid4()
    signal = signal_row(workspace_id, symbol_id, analysis_run_id, signal_id, candidate_id)
    return IntelligenceQualityArtifacts(
        analysis_run=analysis_run_row(workspace_id, symbol_id, analysis_run_id),
        signal=signal,
        feature_snapshot=FeatureSnapshot(
            id=uuid4(),
            analysis_run_id=analysis_run_id,
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe="1m",
            start_time=NOW - timedelta(minutes=30),
            end_time=NOW,
            features_json={
                "trend": {"trendState": "short_term_uptrend"},
                "volatility": {"volatilityState": "expanding"},
                "dataQuality": {"qualityScore": "1.0000"},
                "movement": {"movementEfficiency": "0.7000", "netDirection": "bullish"},
                "range": {"rangeState": "above_previous_range"},
            },
        ),
        indicator_snapshot=IndicatorSnapshot(
            id=uuid4(),
            analysis_run_id=analysis_run_id,
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe="1m",
            indicators_json={
                "ema": {"alignment": "bullish_alignment"},
                "rsi": {"state": "bullish_momentum"},
                "macd": {"state": "bullish"},
            },
        ),
        pattern_candidates=[
            pattern_candidate_row(workspace_id, symbol_id, analysis_run_id, candidate_id)
        ],
        confidence_components=confidence_components(signal_id),
        evidence=[evidence_row(signal_id, "supports_bullish", Decimal("1.00000"))],
        risk_notes=[],
        deterministic_explanation=explanation_row(signal_id, analysis_run_id, workspace_id),
    )


def analysis_run_row(workspace_id: UUID, symbol_id: UUID, analysis_run_id: UUID) -> AnalysisRun:
    return AnalysisRun(
        id=analysis_run_id,
        workspace_id=workspace_id,
        user_id=None,
        symbol_id=symbol_id,
        source_id=None,
        replayed_from_analysis_run_id=None,
        replay_mode=None,
        timeframe="1m",
        start_time=NOW - timedelta(minutes=30),
        end_time=NOW,
        warmup_start_time=NOW - timedelta(minutes=130),
        baseline_start_time=NOW - timedelta(minutes=90),
        analysis_mode=AnalysisMode.HISTORICAL.value,
        include_partial_live_candle=False,
        include_news_correlation=False,
        include_ai_explanation=False,
        status=AnalysisRunStatus.COMPLETED.value,
        engine_version="test",
        rule_set_version="test",
        engine_snapshot_json={},
        rule_set_snapshot_json={},
    )


def signal_row(
    workspace_id: UUID,
    symbol_id: UUID,
    analysis_run_id: UUID,
    signal_id: UUID,
    candidate_id: UUID,
) -> Signal:
    return Signal(
        id=signal_id,
        analysis_run_id=analysis_run_id,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        timeframe="1m",
        strategy_profile_id=uuid4(),
        strategy_profile_key="breakout_continuation",
        strategy_profile_version="v1",
        strategy_profile_snapshot_json={},
        bias=SignalBias.BULLISH.value,
        pattern_type="bullish_breakout",
        classification_status=SignalClassificationStatus.SIGNAL.value,
        confidence_score=Decimal("0.9000"),
        confidence_label=SignalConfidenceLabel.VERY_HIGH.value,
        candidate_strength=Decimal("0.9000"),
        selected_pattern_candidate_id=candidate_id,
        pips_moved=None,
        tick_moved=None,
        movement_direction="bullish",
        movement_quality="efficient",
        volatility_state="expanding",
        trend_state="short_term_uptrend",
        range_state="above_previous_range",
        summary="Bullish bullish_breakout classified by breakout_continuation profile.",
        no_signal_reason=None,
    )


def pattern_candidate_row(
    workspace_id: UUID,
    symbol_id: UUID,
    analysis_run_id: UUID,
    candidate_id: UUID,
) -> PatternCandidate:
    return PatternCandidate(
        id=candidate_id,
        analysis_run_id=analysis_run_id,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        pattern_type="bullish_breakout",
        bias=SignalBias.BULLISH.value,
        strength_score=Decimal("0.9000"),
        is_selected=True,
        evidence_json=[
            {
                "name": "breakout",
                "passed": True,
                "value": "0.9000",
                "threshold": "0.6500",
                "weight": "1.0000",
            }
        ],
        risk_notes_json=[],
        metrics_json={},
    )


def confidence_components(signal_id: UUID) -> list[SignalConfidenceComponent]:
    return [
        SignalConfidenceComponent(
            id=uuid4(),
            signal_id=signal_id,
            component_name="pattern_strength",
            component_score=Decimal("0.9000"),
            component_weight=Decimal("1.0000"),
            weighted_score=Decimal("0.90000"),
            reason="Pattern strength.",
        )
    ]


def evidence_row(signal_id: UUID, direction: str, weight: Decimal) -> SignalEvidence:
    return SignalEvidence(
        id=uuid4(),
        signal_id=signal_id,
        evidence_type="classification",
        direction=direction,
        message="Persisted deterministic evidence.",
        numeric_value=None,
        weight=weight,
        metadata_json={},
    )


def risk_note_row(signal_id: UUID, severity: str = "high") -> SignalRiskNote:
    return SignalRiskNote(
        id=uuid4(),
        signal_id=signal_id,
        code="test_risk",
        message="Severe risk context.",
        severity=severity,
        metadata_json={},
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
        template_version="test",
        explanation_type=ExplanationType.DETERMINISTIC_SIGNAL.value,
        short_summary="Bullish bullish_breakout context.",
        market_behavior="Bullish bullish_breakout context.",
        evidence_summary="Persisted evidence.",
        confidence_summary="Persisted confidence.",
        risk_summary="Persisted risk.",
        no_signal_summary=None,
        full_text="Bullish bullish_breakout context with persisted evidence.",
        source_snapshot_json={},
        safety_status=ExplanationSafetyStatus.PASSED.value,
        blocked_terms_json=[],
    )


def news_correlation_row(signal_id: UUID) -> SignalNewsCorrelation:
    return SignalNewsCorrelation(
        id=uuid4(),
        workspace_id=uuid4(),
        analysis_run_id=uuid4(),
        signal_id=signal_id,
        news_event_id=uuid4(),
        correlation_score=Decimal("0.8000"),
        correlation_label="weak",
        time_delta_minutes=Decimal("30.0000"),
        direction_alignment=DirectionAlignment.ALIGNED.value,
        volatility_reaction=VolatilityReaction.NORMAL.value,
        relevance_score=Decimal("0.8000"),
        importance_score=Decimal("0.8000"),
        magnitude_score=Decimal("0.8000"),
        sentiment_score=Decimal("0.8000"),
        reason="News caused this market behavior.",
        metadata_json={},
    )


def outcome_row(signal: Signal) -> SignalOutcome:
    return SignalOutcome(
        id=uuid4(),
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
        horizon_minutes=30,
        evaluation_status=OutcomeEvaluationStatus.EVALUATED.value,
        reference_time=NOW,
        reference_price=Decimal("1.0000"),
        future_window_start=NOW,
        future_window_end=NOW + timedelta(minutes=30),
        future_candle_count=30,
        max_favorable_move=Decimal("0.0100"),
        max_adverse_move=Decimal("0.0010"),
        net_move=Decimal("0.0050"),
        max_favorable_pips=None,
        max_adverse_pips=None,
        net_pips=None,
        max_favorable_ticks=None,
        max_adverse_ticks=None,
        net_ticks=None,
        direction_followed=True,
        reversal_detected=False,
        outcome_label=OutcomeLabel.CONTINUATION.value,
        movement_quality="directional",
        evaluation_version="test",
        metadata_json={},
    )


def profile_from_key(key: str) -> StrategyProfile:
    definition = next(profile for profile in DEFAULT_STRATEGY_PROFILES if profile.key == key)
    return StrategyProfile(
        id=uuid4(),
        key=definition.key,
        name=definition.name,
        description=definition.description,
        version=definition.version,
        is_active=True,
        allowed_patterns_json=list(definition.allowed_patterns),
        excluded_patterns_json=list(definition.excluded_patterns),
        minimum_candidate_strength=definition.minimum_candidate_strength,
        minimum_confidence=definition.minimum_confidence,
        component_weights_json=definition.component_weights,
        risk_filters_json=definition.risk_filters,
        no_signal_rules_json=definition.no_signal_rules,
    )


def require_signal(artifacts: IntelligenceQualityArtifacts) -> Signal:
    assert artifacts.signal is not None
    return artifacts.signal


def require_explanation(artifacts: IntelligenceQualityArtifacts) -> DeterministicExplanation:
    assert artifacts.deterministic_explanation is not None
    return artifacts.deterministic_explanation


def finding_stub(severity: str, code: str) -> FindingDraft:
    return FindingDraft(
        finding_type="invariant_failure",
        severity=severity,
        code=code,
        title=code,
        message=code,
        artifact_type="signal",
        metadata_json={},
    )


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeQualityRepository:
    def __init__(self) -> None:
        self.artifacts = complete_artifacts()
        signal = require_signal(self.artifacts)
        self.workspace_id = signal.workspace_id
        self.analysis_run_id = signal.analysis_run_id
        self.signal_id = signal.id
        self.latest_signal_run: IntelligenceQualityRun | None = None
        self.latest_analysis_run: IntelligenceQualityRun | None = None
        self.created_runs: list[IntelligenceQualityRun] = []
        self.findings: list[IntelligenceQualityFinding] = []
        self.shadow_results: list[ShadowClassificationResult] = []
        self.profiles = [profile_from_key("breakout_continuation")]

    async def get_latest_signal_run(
        self,
        signal_id: UUID,
        gate_version: str,
        shadow_version: str,
    ) -> IntelligenceQualityRun | None:
        return self.latest_signal_run

    async def get_latest_analysis_run(
        self,
        analysis_run_id: UUID,
        gate_version: str,
        shadow_version: str,
    ) -> IntelligenceQualityRun | None:
        return self.latest_analysis_run

    async def load_for_signal(self, signal_id: UUID) -> IntelligenceQualityArtifacts:
        return self.artifacts

    async def load_for_analysis_run(self, analysis_run_id: UUID) -> IntelligenceQualityArtifacts:
        return self.artifacts

    async def list_active_strategy_profiles(self) -> list[StrategyProfile]:
        return self.profiles

    async def create_quality_run(self, run: IntelligenceQualityRun) -> IntelligenceQualityRun:
        run.id = uuid4()
        run.created_at = NOW
        run.updated_at = NOW
        self.created_runs.append(run)
        return run

    async def create_findings(
        self,
        findings: list[IntelligenceQualityFinding],
    ) -> list[IntelligenceQualityFinding]:
        for item in findings:
            item.id = uuid4()
            item.created_at = NOW
        self.findings = findings
        return findings

    async def create_shadow_results(
        self,
        results: list[ShadowClassificationResult],
    ) -> list[ShadowClassificationResult]:
        for item in results:
            item.id = uuid4()
            item.created_at = NOW
        self.shadow_results = results
        return results

    async def get_run(self, quality_run_id: UUID) -> IntelligenceQualityRun | None:
        if self.latest_signal_run is not None and self.latest_signal_run.id == quality_run_id:
            return self.latest_signal_run
        for run in self.created_runs:
            if run.id == quality_run_id:
                return run
        return None

    async def list_findings(self, quality_run_id: UUID) -> list[IntelligenceQualityFinding]:
        return self.findings

    async def list_shadow_results(self, quality_run_id: UUID) -> list[ShadowClassificationResult]:
        return self.shadow_results


def service_with_fake_repository() -> tuple[
    IntelligenceQualityService,
    FakeQualityRepository,
    FakeSession,
]:
    session = FakeSession()
    service = IntelligenceQualityService.__new__(IntelligenceQualityService)
    repository = FakeQualityRepository()
    service.session = cast(AsyncSession, session)
    service.settings = Settings(_env_file=None)
    service.repository = cast(IntelligenceQualityRepository, repository)
    service.gate_service = IntelligenceQualityGateService()
    service.shadow_service = ShadowClassificationService()
    return service, repository, session


class FakeRouteQualityService:
    def __init__(self, signal_id: UUID) -> None:
        self.workspace_id = uuid4()
        self.analysis_run_id = uuid4()
        self.signal_id = signal_id
        self.run_id = uuid4()
        self.response = IntelligenceQualityResponse(
            quality_run=IntelligenceQualityRunRead.model_validate(
                quality_run_row(self.workspace_id, self.analysis_run_id, self.signal_id)
            ),
            findings=[],
            shadow_classifications=[],
        )
        self.response.quality_run.id = self.run_id

    async def run_for_signal(
        self,
        signal_id: UUID,
        include_shadow_classification: bool,
        force_recompute: bool,
    ) -> IntelligenceQualityResponse:
        return self.response

    async def list_findings(self, quality_run_id: UUID) -> list[IntelligenceQualityFinding]:
        return []


def quality_run_row(
    workspace_id: UUID,
    analysis_run_id: UUID,
    signal_id: UUID,
) -> IntelligenceQualityRun:
    return IntelligenceQualityRun(
        id=uuid4(),
        workspace_id=workspace_id,
        analysis_run_id=analysis_run_id,
        signal_id=signal_id,
        source_type=IntelligenceQualitySourceType.SIGNAL.value,
        status=IntelligenceQualityRunStatus.COMPLETED.value,
        quality_score=Decimal("1.0000"),
        quality_label=IntelligenceQualityLabel.STRONG.value,
        gate_version="quality_gates_v1",
        shadow_version="shadow_profiles_v1",
        checked_at=NOW,
        summary="Existing quality run.",
        metadata_json={},
        created_at=NOW,
        updated_at=NOW,
    )


def llm_explanation_row(signal: Signal) -> LlmExplanation:
    return LlmExplanation(
        id=uuid4(),
        signal_id=signal.id,
        analysis_run_id=signal.analysis_run_id,
        workspace_id=signal.workspace_id,
        provider="mock",
        model="mock",
        prompt_version="test",
        input_json={},
        output_text="Blocked output.",
        safety_status=LlmExplanationSafetyStatus.BLOCKED.value,
        blocked_terms_json=[],
        grounding_status=LlmExplanationGroundingStatus.GROUNDED.value,
        grounding_issues_json=[],
        tokens_input=None,
        tokens_output=None,
        estimated_cost=None,
        error_message=None,
    )


def reasoning_run_row(signal: Signal) -> LlmReasoningRun:
    return LlmReasoningRun(
        id=uuid4(),
        workspace_id=signal.workspace_id,
        analysis_run_id=signal.analysis_run_id,
        signal_id=signal.id,
        outcome_id=None,
        source_type=ReasoningSourceType.SIGNAL.value,
        provider="mock",
        model="mock",
        prompt_version="test",
        reasoning_type=ReasoningType.NEXT_SCENARIOS.value,
        status=ReasoningRunStatus.COMPLETED.value,
        input_snapshot_json={},
        output_json={},
        output_text="Reasoning output.",
        safety_status=ReasoningSafetyStatus.PASSED.value,
        grounding_status=ReasoningGroundingStatus.GROUNDED.value,
        blocked_terms_json=[],
        grounding_issues_json=[],
        tokens_input=None,
        tokens_output=None,
        estimated_cost=None,
        latency_ms=None,
        error_message=None,
    )


def scenario_row(signal: Signal, reasoning_run_id: UUID) -> ScenarioHypothesis:
    return ScenarioHypothesis(
        id=uuid4(),
        reasoning_run_id=reasoning_run_id,
        workspace_id=signal.workspace_id,
        analysis_run_id=signal.analysis_run_id,
        signal_id=signal.id,
        scenario_type=ScenarioType.CONTINUATION.value,
        scenario_label="Scenario",
        possibility_label=ScenarioPossibilityLabel.MEDIUM.value,
        supporting_evidence_json=[],
        conflicting_evidence_json=[],
        outcome_history_json=None,
        next_observations_json=[],
        suggested_backend_actions_json=["unknown_action"],
        risk_notes_json=[],
        sort_order=0,
    )
