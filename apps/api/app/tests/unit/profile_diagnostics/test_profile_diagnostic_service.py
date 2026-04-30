from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.modules.analysis.models import AnalysisAuditLog
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendation,
    CalibrationRecommendationStatus,
    DiagnosticRunStatus,
    PatternOutcomeDiagnostic,
    StrategyProfileDiagnostic,
    StrategyProfileDiagnosticRun,
)
from app.modules.profile_diagnostics.repository import OutcomeSignalRow
from app.modules.profile_diagnostics.schemas import ProfileDiagnosticRunRequest
from app.modules.profile_diagnostics.service import ProfileDiagnosticService
from app.modules.signals.models import SignalBias, SignalClassificationStatus

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeDiagnosticRepository:
    def __init__(self, rows: list[OutcomeSignalRow]) -> None:
        self.rows = rows
        self.last_limit: int | None = None
        self.profile_diagnostics: list[StrategyProfileDiagnostic] = []
        self.pattern_diagnostics: list[PatternOutcomeDiagnostic] = []
        self.recommendations: list[CalibrationRecommendation] = []
        self.runs: dict[UUID, StrategyProfileDiagnosticRun] = {}

    async def create_run(
        self,
        run: StrategyProfileDiagnosticRun,
    ) -> StrategyProfileDiagnosticRun:
        run.id = uuid4()
        self.runs[run.id] = run
        return run

    async def update_run(
        self,
        run: StrategyProfileDiagnosticRun,
    ) -> StrategyProfileDiagnosticRun:
        self.runs[run.id] = run
        return run

    async def get_run(self, run_id: UUID) -> StrategyProfileDiagnosticRun | None:
        return self.runs.get(run_id)

    async def list_outcome_signal_rows(
        self,
        workspace_id: UUID,
        horizons_minutes: list[int],
        limit: int,
        strategy_profile_key: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        pattern_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[OutcomeSignalRow]:
        self.last_limit = limit
        return self.rows[:limit]

    async def create_strategy_profile_diagnostics(
        self,
        diagnostics: list[StrategyProfileDiagnostic],
    ) -> list[StrategyProfileDiagnostic]:
        self.profile_diagnostics.extend(diagnostics)
        return diagnostics

    async def create_pattern_diagnostics(
        self,
        diagnostics: list[PatternOutcomeDiagnostic],
    ) -> list[PatternOutcomeDiagnostic]:
        self.pattern_diagnostics.extend(diagnostics)
        return diagnostics

    async def create_recommendations(
        self,
        recommendations: list[CalibrationRecommendation],
    ) -> list[CalibrationRecommendation]:
        for recommendation in recommendations:
            recommendation.id = uuid4()
        self.recommendations.extend(recommendations)
        return recommendations

    async def get_recommendation(
        self,
        recommendation_id: UUID,
    ) -> CalibrationRecommendation | None:
        return next(
            (item for item in self.recommendations if item.id == recommendation_id),
            None,
        )

    async def update_recommendation(
        self,
        recommendation: CalibrationRecommendation,
    ) -> CalibrationRecommendation:
        return recommendation


class FakeStrategyProfileRepository:
    async def get_by_key_version(self, key: str, version: str) -> None:
        return None

    async def get_by_key(self, key: str) -> None:
        return None


class FakeAnalysisRepository:
    def __init__(self) -> None:
        self.audit_events: list[str] = []

    async def add_audit_log(self, audit_log: AnalysisAuditLog) -> AnalysisAuditLog:
        self.audit_events.append(audit_log.event_type)
        return audit_log


def fake_service(
    rows: list[OutcomeSignalRow],
) -> tuple[ProfileDiagnosticService, FakeDiagnosticRepository, FakeSession]:
    service = ProfileDiagnosticService.__new__(ProfileDiagnosticService)
    session = FakeSession()
    repository = FakeDiagnosticRepository(rows)
    service_any: Any = service
    service_any.session = session
    service_any.settings = SimpleNamespace(
        profile_diagnostics_minimum_sample_size=5,
        profile_diagnostics_strong_follow_through_rate=Decimal("0.65"),
        profile_diagnostics_high_reversal_rate=Decimal("0.35"),
        profile_diagnostics_high_no_follow_through_rate=Decimal("0.40"),
        profile_diagnostics_confidence_misalignment_threshold=Decimal("0.45"),
    )
    service_any.repository = repository
    service_any.strategy_profile_repository = FakeStrategyProfileRepository()
    service_any.analysis_repository = FakeAnalysisRepository()
    from app.modules.profile_diagnostics.calculator import ProfileDiagnosticCalculator
    from app.modules.profile_diagnostics.recommender import ProfileCalibrationRecommender

    service_any.calculator = ProfileDiagnosticCalculator()
    service_any.recommender = ProfileCalibrationRecommender()
    return service, repository, session


@pytest.mark.anyio
async def test_diagnostic_run_creates_profile_diagnostics() -> None:
    service, repository, _session = fake_service(outcome_rows(10, OutcomeLabel.CONTINUATION))

    run = await service.run_workspace_diagnostics(request(limit=50))

    assert run.status == DiagnosticRunStatus.COMPLETED.value
    assert repository.profile_diagnostics


@pytest.mark.anyio
async def test_diagnostic_run_creates_pattern_diagnostics() -> None:
    service, repository, _session = fake_service(outcome_rows(10, OutcomeLabel.CONTINUATION))

    await service.run_workspace_diagnostics(request(limit=50))

    assert repository.pattern_diagnostics


@pytest.mark.anyio
async def test_diagnostic_run_creates_recommendations() -> None:
    service, repository, _session = fake_service(outcome_rows(10, OutcomeLabel.REVERSAL))

    await service.run_workspace_diagnostics(request(limit=50))

    assert repository.recommendations


@pytest.mark.anyio
async def test_bounded_limit_is_respected() -> None:
    service, repository, _session = fake_service(outcome_rows(10, OutcomeLabel.CONTINUATION))

    await service.run_workspace_diagnostics(request(limit=3))

    assert repository.last_limit == 3
    assert repository.runs
    assert next(iter(repository.runs.values())).evaluated_outcome_count == 3


@pytest.mark.anyio
async def test_recommendation_status_update_works() -> None:
    service, repository, _session = fake_service(outcome_rows(10, OutcomeLabel.REVERSAL))
    await service.run_workspace_diagnostics(request(limit=50))
    recommendation = repository.recommendations[0]

    updated = await service.update_recommendation_status(
        recommendation.id,
        CalibrationRecommendationStatus.ACKNOWLEDGED,
    )

    assert updated.status == CalibrationRecommendationStatus.ACKNOWLEDGED.value


def request(limit: int) -> ProfileDiagnosticRunRequest:
    return ProfileDiagnosticRunRequest(
        workspaceId=uuid4(),
        horizonsMinutes=[15],
        minimumSampleSize=5,
        limit=limit,
    )


def outcome_rows(count: int, label: OutcomeLabel) -> list[OutcomeSignalRow]:
    workspace_id = uuid4()
    symbol_id = uuid4()
    analysis_run_id = uuid4()
    return [
        OutcomeSignalRow(
            outcome=SignalOutcome(
                workspace_id=workspace_id,
                analysis_run_id=analysis_run_id,
                signal_id=uuid4(),
                symbol_id=symbol_id,
                timeframe="1m",
                strategy_profile_key="default",
                strategy_profile_version="v1",
                pattern_type="breakout",
                bias=SignalBias.BULLISH.value,
                classification_status=SignalClassificationStatus.SIGNAL.value,
                horizon_minutes=15,
                evaluation_status=OutcomeEvaluationStatus.EVALUATED.value,
                reference_time=BASE_TIME,
                reference_price=Decimal("100"),
                future_window_start=BASE_TIME + timedelta(minutes=1),
                future_window_end=BASE_TIME + timedelta(minutes=15),
                future_candle_count=10,
                max_favorable_move=Decimal("1"),
                max_adverse_move=Decimal("0.2"),
                net_move=Decimal("0.5"),
                max_favorable_pips=Decimal("10"),
                max_adverse_pips=Decimal("2"),
                net_pips=Decimal("5"),
                max_favorable_ticks=None,
                max_adverse_ticks=None,
                net_ticks=None,
                direction_followed=label != OutcomeLabel.REVERSAL,
                reversal_detected=label == OutcomeLabel.REVERSAL,
                outcome_label=label.value,
                movement_quality="test",
                evaluation_version="v1",
                metadata_json={},
            ),
            confidence_score=Decimal("0.9000"),
            candidate_strength=Decimal("0.8000"),
        )
        for _ in range(count)
    ]
