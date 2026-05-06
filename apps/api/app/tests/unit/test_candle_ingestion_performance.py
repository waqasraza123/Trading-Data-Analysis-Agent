from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.modules.candle_ingestion_performance.batcher import iter_chunks
from app.modules.candle_ingestion_performance.bulk_repository import (
    CandleWriteState,
    resolve_candle_write_decision,
)
from app.modules.candle_ingestion_performance.models import CandleIngestionConflictType
from app.modules.candle_ingestion_performance.schemas import CandleIngestionRowOutcome
from app.modules.candles.schemas import CandleOriginType, NormalizedCandleInput
from app.modules.candles.timeframes import Timeframe


def test_iter_chunks_batches_without_dropping_tail() -> None:
    assert list(iter_chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]


def test_final_candle_rejects_later_partial() -> None:
    existing = candle_state(is_final=True)
    incoming = candle_input(is_final=False)

    decision = resolve_candle_write_decision(existing, incoming)

    assert decision.outcome == CandleIngestionRowOutcome.SKIPPED_DUPLICATE
    assert decision.conflict_type == CandleIngestionConflictType.PARTIAL_AFTER_FINAL


def test_matching_final_candle_is_duplicate() -> None:
    existing = candle_state(is_final=True)
    incoming = candle_input(is_final=True)

    decision = resolve_candle_write_decision(existing, incoming)

    assert decision.outcome == CandleIngestionRowOutcome.SKIPPED_DUPLICATE
    assert decision.conflict_type == CandleIngestionConflictType.DUPLICATE_FINAL


def test_conflicting_final_candle_is_reported() -> None:
    existing = candle_state(is_final=True)
    incoming = candle_input(is_final=True, close=Decimal("101.00"))

    decision = resolve_candle_write_decision(existing, incoming)

    assert decision.outcome == CandleIngestionRowOutcome.CONFLICTED
    assert decision.conflict_type == CandleIngestionConflictType.FINAL_CONFLICT


def test_partial_can_be_finalized() -> None:
    existing = candle_state(is_final=False)
    incoming = candle_input(is_final=True)

    decision = resolve_candle_write_decision(existing, incoming)

    assert decision.outcome == CandleIngestionRowOutcome.UPDATED


def candle_state(is_final: bool) -> CandleWriteState:
    workspace_id = uuid4()
    symbol_id = uuid4()
    source_id = uuid4()
    return CandleWriteState(
        candle_id=uuid4(),
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        source_id=source_id,
        timeframe=Timeframe.ONE_MINUTE.value,
        timestamp=datetime(2026, 5, 6, 10, 0, tzinfo=UTC),
        open=Decimal("100.00"),
        high=Decimal("102.00"),
        low=Decimal("99.00"),
        close=Decimal("100.50"),
        volume=Decimal("10.00"),
        is_final=is_final,
        exists_in_database=True,
    )


def candle_input(is_final: bool, close: Decimal = Decimal("100.50")) -> NormalizedCandleInput:
    return NormalizedCandleInput(
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        source_id=uuid4(),
        timeframe=Timeframe.ONE_MINUTE,
        timestamp=datetime(2026, 5, 6, 10, 0, tzinfo=UTC),
        open=Decimal("100.00"),
        high=Decimal("102.00"),
        low=Decimal("99.00"),
        close=close,
        volume=Decimal("10.00"),
        is_final=is_final,
        origin_type=CandleOriginType.JSON_IMPORT,
        origin_reference_id=uuid4(),
    )
