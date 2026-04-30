from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.config import Settings
from app.modules.analysis.models import (
    AnalysisAuditLog,
    AnalysisMode,
    AnalysisRun,
    AnalysisRunStatus,
)
from app.modules.llm_adapters.registry import LlmAdapterRegistry
from app.modules.reasoning.input_builder import ScenarioReasoningInputBuilder
from app.modules.reasoning.models import (
    LlmReasoningRun,
    ReasoningRunStatus,
    ScenarioHypothesis,
)
from app.modules.reasoning.schemas import ScenarioReasoningInputSnapshot
from app.modules.reasoning.service import ScenarioReasoningService
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
from app.tests.unit.reasoning_factories import reasoning_input_snapshot


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class FakeExecuteResult:
    def scalar_one_or_none(self) -> None:
        return None


class FakeInputSession:
    async def execute(self, statement: object) -> FakeExecuteResult:
        return FakeExecuteResult()


class FakeOutcomeRepository:
    async def list_by_signal_id(self, signal_id: UUID) -> list[Any]:
        return []

    async def list_filtered_outcomes(
        self,
        workspace_id: UUID,
        horizon_minutes: int,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        pattern_type: str | None = None,
        strategy_profile_key: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Any]:
        if horizon_minutes == 5:
            return [
                type(
                    "Outcome",
                    (),
                    {
                        "outcome_label": "continuation",
                        "evaluation_status": "evaluated",
                    },
                )()
            ]
        return []


class FakeReasoningRepository:
    def __init__(self) -> None:
        self.runs: list[LlmReasoningRun] = []
        self.scenarios: dict[UUID, list[ScenarioHypothesis]] = {}

    async def create_run(self, run: LlmReasoningRun) -> LlmReasoningRun:
        now = datetime.now(UTC)
        run.created_at = now
        run.updated_at = now
        self.runs.append(run)
        return run

    async def get_latest_completed_signal_run(
        self,
        signal_id: UUID,
        reasoning_type: str,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> LlmReasoningRun | None:
        for run in reversed(self.runs):
            if (
                run.signal_id == signal_id
                and run.reasoning_type == reasoning_type
                and run.provider == provider
                and run.model == model
                and run.prompt_version == prompt_version
                and run.status == ReasoningRunStatus.COMPLETED
            ):
                return run
        return None

    async def get_latest_signal_run(self, signal_id: UUID) -> LlmReasoningRun | None:
        for run in reversed(self.runs):
            if run.signal_id == signal_id:
                return run
        return None

    async def replace_scenarios(
        self,
        reasoning_run_id: UUID,
        scenarios: list[ScenarioHypothesis],
    ) -> list[ScenarioHypothesis]:
        for scenario in scenarios:
            scenario.created_at = datetime.now(UTC)
        self.scenarios[reasoning_run_id] = scenarios
        return scenarios

    async def update_run(self, run: LlmReasoningRun) -> LlmReasoningRun:
        return run

    async def list_scenarios(self, reasoning_run_id: UUID) -> list[ScenarioHypothesis]:
        return self.scenarios.get(reasoning_run_id, [])

    async def list_signal_runs(self, signal_id: UUID) -> list[LlmReasoningRun]:
        return [run for run in self.runs if run.signal_id == signal_id]


class FakeSignalRepository:
    def __init__(self, signal: Signal) -> None:
        self.signal = signal

    async def get_by_id(self, signal_id: UUID) -> Signal | None:
        return self.signal if signal_id == self.signal.id else None


class FakeAnalysisRepository:
    def __init__(self) -> None:
        self.audit_events: list[str] = []

    async def add_audit_log(self, audit_log: AnalysisAuditLog) -> AnalysisAuditLog:
        self.audit_events.append(audit_log.event_type)
        return audit_log


@pytest.mark.anyio
async def test_input_builder_includes_signal_artifacts_and_excludes_raw_candles() -> None:
    signal = signal_row()
    run = run_row(signal)
    builder = ScenarioReasoningInputBuilder(FakeInputSession())  # type: ignore[arg-type]
    builder_any: Any = builder
    builder_any.outcome_repository = FakeOutcomeRepository()

    snapshot = await builder.build_signal_input(
        signal=signal,
        run=run,
        symbol=symbol_row(signal.symbol_id),
        confidence_components=[
            SignalConfidenceComponent(
                signal_id=signal.id,
                component_name="pattern",
                component_score=Decimal("0.8"),
                component_weight=Decimal("0.5"),
                weighted_score=Decimal("0.4"),
                reason="Stored pattern confidence.",
            )
        ],
        evidence=[
            SignalEvidence(
                signal_id=signal.id,
                evidence_type="pattern",
                direction="supporting",
                message="Stored breakout evidence.",
                numeric_value=Decimal("0.8"),
                weight=Decimal("0.8"),
                metadata_json={},
            )
        ],
        risk_notes=[
            SignalRiskNote(
                signal_id=signal.id,
                code="late_move",
                message="Stored risk note.",
                severity="medium",
                metadata_json={},
            )
        ],
        deterministic_explanation=None,
        feature_snapshot=None,
        indicator_snapshot=None,
        news_correlations=[],
        horizons_minutes=[5, 15],
    )
    payload = snapshot.model_dump(mode="json", by_alias=True)

    assert payload["signalEvidence"][0]["message"] == "Stored breakout evidence."
    assert payload["riskNotes"][0]["message"] == "Stored risk note."
    assert payload["outcomeHistory"]["items"][0]["matchingOutcomeCount"] == 1
    assert "candles" not in payload
    assert "databaseUrl" not in payload


@pytest.mark.anyio
async def test_service_returns_provider_not_configured_when_reasoning_disabled() -> None:
    service, signal, repository, session = fake_service(llm_reasoning_enabled=False)

    response = await service.generate_signal_scenarios(signal.id)

    assert response.reasoning_run.status == ReasoningRunStatus.PROVIDER_NOT_CONFIGURED
    assert response.scenarios[0].scenario_type.value == "insufficient_context"
    assert repository.runs[0].error_message == "llm_reasoning_disabled"
    assert session.commit_count == 1


@pytest.mark.anyio
async def test_service_persists_reasoning_run_with_mock_provider() -> None:
    service, signal, repository, _session = fake_service(llm_reasoning_enabled=True)

    response = await service.generate_signal_scenarios(signal.id)

    assert response.reasoning_run.status == ReasoningRunStatus.COMPLETED
    assert response.reasoning_run.provider == "mock"
    assert response.scenarios[0].suggested_backend_actions
    assert len(repository.runs) == 1


@pytest.mark.anyio
async def test_service_idempotency_reuses_completed_run_without_force() -> None:
    service, signal, repository, _session = fake_service(llm_reasoning_enabled=True)

    first = await service.generate_signal_scenarios(signal.id)
    second = await service.generate_signal_scenarios(signal.id)

    assert first.reasoning_run.id == second.reasoning_run.id
    assert len(repository.runs) == 1


@pytest.mark.anyio
async def test_force_recompute_creates_new_reasoning_run() -> None:
    service, signal, repository, _session = fake_service(llm_reasoning_enabled=True)

    first = await service.generate_signal_scenarios(signal.id)
    second = await service.generate_signal_scenarios(signal.id, force_recompute=True)

    assert first.reasoning_run.id != second.reasoning_run.id
    assert len(repository.runs) == 2


def fake_service(
    llm_reasoning_enabled: bool,
) -> tuple[ScenarioReasoningService, Signal, FakeReasoningRepository, FakeSession]:
    signal = signal_row()
    session = FakeSession()
    repository = FakeReasoningRepository()
    service = ScenarioReasoningService.__new__(ScenarioReasoningService)
    service_any: Any = service
    service_any.session = session
    service_any.settings = Settings(
        _env_file=None,
        llm_reasoning_enabled=llm_reasoning_enabled,
        llm_store_inputs=True,
        llm_store_outputs=True,
    )
    service_any.reasoning_repository = repository
    service_any.analysis_repository = FakeAnalysisRepository()
    service_any.signal_repository = FakeSignalRepository(signal)
    service_any.adapter_registry = LlmAdapterRegistry(service_any.settings)

    async def build_input(signal_id: UUID) -> ScenarioReasoningInputSnapshot:
        return reasoning_input_snapshot(
            outcome_items=[{"horizonMinutes": 5, "matchingOutcomeCount": 1}]
        )

    service_any.build_signal_reasoning_input = build_input
    return service, signal, repository, session


def signal_row() -> Signal:
    return Signal(
        id=uuid4(),
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="1m",
        bias=SignalBias.BULLISH.value,
        classification_status=SignalClassificationStatus.SIGNAL.value,
        confidence_score=Decimal("0.8000"),
        confidence_label=SignalConfidenceLabel.HIGH.value,
        strategy_profile_key="default",
        strategy_profile_version="v1",
        pattern_type="breakout",
        summary="Stored signal summary.",
    )


def run_row(signal: Signal) -> AnalysisRun:
    return AnalysisRun(
        id=signal.analysis_run_id,
        workspace_id=signal.workspace_id,
        user_id=None,
        symbol_id=signal.symbol_id,
        source_id=None,
        timeframe=signal.timeframe,
        start_time=datetime(2026, 4, 30, 10, 0, tzinfo=UTC),
        end_time=datetime(2026, 4, 30, 10, 15, tzinfo=UTC),
        analysis_mode=AnalysisMode.HISTORICAL.value,
        include_partial_live_candle=False,
        include_news_correlation=False,
        include_ai_explanation=False,
        status=AnalysisRunStatus.COMPLETED.value,
        engine_version="test",
        rule_set_version="test",
    )


def symbol_row(symbol_id: UUID) -> Symbol:
    return Symbol(
        id=symbol_id,
        symbol="EURUSD",
        display_name="EUR/USD",
        market_type=MarketType.FOREX.value,
        base_asset="EUR",
        quote_asset="USD",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        price_precision=5,
        quantity_precision=2,
        is_active=True,
    )
