from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from app.modules.analysis.models import AnalysisAuditLog
from app.modules.candles.timeframes import Timeframe
from app.modules.outcomes.calculator import OutcomeCalculator
from app.modules.outcomes.models import OutcomeLabel, SignalOutcome
from app.modules.outcomes.service import OutcomeEvaluationService
from app.modules.symbols.models import MarketType
from app.tests.unit.outcomes.factories import BASE_TIME, service_run, service_signal


class FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeSignalRepository:
    def __init__(self, signal: SimpleNamespace) -> None:
        self.signal = signal

    async def get_by_id(self, signal_id: UUID) -> SimpleNamespace | None:
        return self.signal if self.signal.id == signal_id else None


class FakeAnalysisRepository:
    def __init__(self, run: SimpleNamespace) -> None:
        self.run = run
        self.audit_events: list[str] = []

    async def get_run(self, analysis_run_id: UUID) -> SimpleNamespace | None:
        return self.run if self.run.id == analysis_run_id else None

    async def add_audit_log(self, audit_log: AnalysisAuditLog) -> AnalysisAuditLog:
        self.audit_events.append(audit_log.event_type)
        return audit_log


class FakeSymbolRepository:
    async def get_by_id(self, symbol_id: UUID) -> SimpleNamespace:
        return SimpleNamespace(
            id=symbol_id,
            market_type=MarketType.FOREX,
            pip_size=Decimal("0.0001"),
            tick_size=None,
        )


class FakeCandleService:
    async def fetch_candle_window(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        source_id: UUID | None,
        include_partial: bool,
    ) -> list[SimpleNamespace]:
        if end_time <= BASE_TIME + timedelta(minutes=3):
            return [
                SimpleNamespace(
                    timestamp=BASE_TIME + timedelta(minutes=3),
                    close=Decimal("100"),
                )
            ]
        return [
            SimpleNamespace(
                timestamp=BASE_TIME + timedelta(minutes=4),
                high=Decimal("101"),
                low=Decimal("99.8"),
                close=Decimal("100.4"),
            ),
            SimpleNamespace(
                timestamp=BASE_TIME + timedelta(minutes=5),
                high=Decimal("102"),
                low=Decimal("100.2"),
                close=Decimal("101.4"),
            ),
            SimpleNamespace(
                timestamp=BASE_TIME + timedelta(minutes=6),
                high=Decimal("103"),
                low=Decimal("101.0"),
                close=Decimal("102.0"),
            ),
        ]


class FakeOutcomeRepository:
    def __init__(self) -> None:
        self.outcomes: dict[tuple[UUID, int, str], SignalOutcome] = {}
        self.upsert_count = 0

    async def get_outcome(
        self,
        signal_id: UUID,
        horizon_minutes: int,
        evaluation_version: str,
    ) -> SignalOutcome | None:
        return self.outcomes.get((signal_id, horizon_minutes, evaluation_version))

    async def list_by_signal_id(self, signal_id: UUID) -> list[SignalOutcome]:
        return [outcome for key, outcome in self.outcomes.items() if key[0] == signal_id]

    async def upsert_outcome(
        self,
        outcome: SignalOutcome,
        force_recompute: bool,
    ) -> SignalOutcome:
        self.upsert_count += 1
        key = (outcome.signal_id, outcome.horizon_minutes, outcome.evaluation_version)
        if key in self.outcomes and not force_recompute:
            return self.outcomes[key]
        self.outcomes[key] = outcome
        return outcome


def fake_service() -> tuple[OutcomeEvaluationService, SimpleNamespace, FakeOutcomeRepository]:
    signal = service_signal()
    run = service_run(signal)
    repository = FakeOutcomeRepository()
    service = OutcomeEvaluationService.__new__(OutcomeEvaluationService)
    service_any: Any = service
    service_any.session = FakeSession()
    service_any.settings = SimpleNamespace(
        outcome_default_horizons_minutes=[5, 15],
        outcome_min_future_candles=3,
        outcome_evaluation_version="v1",
    )
    service_any.outcome_repository = repository
    service_any.signal_repository = FakeSignalRepository(signal)
    service_any.analysis_repository = FakeAnalysisRepository(run)
    service_any.symbol_repository = FakeSymbolRepository()
    service_any.candle_service = FakeCandleService()
    service_any.calculator = OutcomeCalculator()
    return service, signal, repository


@pytest.mark.anyio
async def test_evaluate_one_signal_with_two_horizons() -> None:
    service, signal, repository = fake_service()

    outcomes = await service.evaluate_signal_outcomes(signal.id, [5, 15])

    assert len(outcomes) == 2
    assert repository.upsert_count == 2
    assert {outcome.outcome_label for outcome in outcomes} == {OutcomeLabel.CONTINUATION}


@pytest.mark.anyio
async def test_repeated_evaluate_without_force_recompute_reuses_existing_outcomes() -> None:
    service, signal, repository = fake_service()

    await service.evaluate_signal_outcomes(signal.id, [5])
    await service.evaluate_signal_outcomes(signal.id, [5])

    assert repository.upsert_count == 1


@pytest.mark.anyio
async def test_force_recompute_updates_existing_outcome_path() -> None:
    service, signal, repository = fake_service()

    await service.evaluate_signal_outcomes(signal.id, [5])
    await service.evaluate_signal_outcomes(signal.id, [5], force_recompute=True)

    assert repository.upsert_count == 2
