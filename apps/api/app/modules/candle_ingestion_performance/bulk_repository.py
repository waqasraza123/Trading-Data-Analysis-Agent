from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, insert, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candle_ingestion_performance.diagnostics import (
    decimal_to_json,
    serialize_incoming_candle,
)
from app.modules.candle_ingestion_performance.models import (
    CandleIngestionConflict,
    CandleIngestionConflictResolution,
    CandleIngestionConflictType,
)
from app.modules.candle_ingestion_performance.schemas import (
    CandleIngestionBatchOutcome,
    CandleIngestionCandidate,
    CandleIngestionConflictRecord,
    CandleIngestionCounters,
    CandleIngestionRowOutcome,
)
from app.modules.candles.models import Candle
from app.modules.candles.schemas import CandleOriginType, NormalizedCandleInput

CandleIdentity = tuple[UUID, UUID, UUID, str, datetime]


@dataclass(frozen=True)
class CandleWriteState:
    candle_id: UUID | None
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    is_final: bool
    exists_in_database: bool


@dataclass(frozen=True)
class CandleWriteDecision:
    outcome: CandleIngestionRowOutcome
    conflict_type: CandleIngestionConflictType | None = None
    resolution: CandleIngestionConflictResolution | None = None


class CandleBulkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def apply_candidates(
        self,
        candidates: list[CandleIngestionCandidate],
        performance_run_id: UUID,
    ) -> CandleIngestionBatchOutcome:
        outcome = CandleIngestionBatchOutcome(
            counters=CandleIngestionCounters(rows_validated=len(candidates), batch_count=1)
        )
        if not candidates:
            return outcome
        existing_by_key = await self.fetch_existing_by_key(candidates)
        virtual_state_by_key: dict[CandleIdentity, CandleWriteState] = {
            key: candle_state_from_model(candle) for key, candle in existing_by_key.items()
        }
        insert_values_by_key: dict[CandleIdentity, dict[str, object]] = {}
        update_values_by_key: dict[CandleIdentity, dict[str, object]] = {}
        for candidate in candidates:
            key = candle_identity(candidate.candle)
            existing_state = virtual_state_by_key.get(key)
            decision = resolve_candle_write_decision(existing_state, candidate.candle)
            if decision.outcome == CandleIngestionRowOutcome.INSERTED:
                insert_values_by_key[key] = insert_values_for_candle(candidate.candle)
                virtual_state_by_key[key] = candle_state_from_input(
                    candidate.candle,
                    exists_in_database=False,
                )
                outcome.counters.rows_inserted += 1
                continue
            if decision.outcome == CandleIngestionRowOutcome.UPDATED:
                next_state = candle_state_from_input(
                    candidate.candle,
                    candle_id=existing_state.candle_id if existing_state is not None else None,
                    exists_in_database=(
                        existing_state.exists_in_database if existing_state is not None else False
                    ),
                )
                virtual_state_by_key[key] = next_state
                if key in insert_values_by_key:
                    insert_values_by_key[key].update(insert_mutable_values(candidate.candle))
                elif existing_state is not None and existing_state.candle_id is not None:
                    update_values_by_key[key] = update_values_for_candle(candidate.candle)
                    update_values_by_key[key]["id"] = existing_state.candle_id
                outcome.counters.rows_updated += 1
                continue
            if decision.outcome == CandleIngestionRowOutcome.SKIPPED_DUPLICATE:
                outcome.counters.rows_skipped_duplicate += 1
                if decision.conflict_type is not None and decision.resolution is not None:
                    outcome.conflicts.append(
                        build_conflict_record(
                            candidate=candidate,
                            existing_state=existing_state,
                            conflict_type=decision.conflict_type,
                            resolution=decision.resolution,
                        )
                    )
                continue
            if decision.outcome == CandleIngestionRowOutcome.CONFLICTED:
                outcome.counters.rows_conflicted += 1
                if decision.conflict_type is not None and decision.resolution is not None:
                    outcome.conflicts.append(
                        build_conflict_record(
                            candidate=candidate,
                            existing_state=existing_state,
                            conflict_type=decision.conflict_type,
                            resolution=decision.resolution,
                        )
                    )
        if insert_values_by_key:
            await self.session.execute(insert(Candle), list(insert_values_by_key.values()))
        for update_values in update_values_by_key.values():
            candle_id = update_values.pop("id")
            await self.session.execute(
                update(Candle).where(Candle.id == candle_id).values(**update_values)
            )
        if outcome.conflicts:
            await self.add_conflicts(performance_run_id, outcome.conflicts)
        await self.session.flush()
        return outcome

    async def fetch_existing_by_key(
        self,
        candidates: list[CandleIngestionCandidate],
    ) -> dict[CandleIdentity, Candle]:
        keys = list({candle_identity(candidate.candle) for candidate in candidates})
        statement: Select[tuple[Candle]] = select(Candle).where(
            tuple_(
                Candle.workspace_id,
                Candle.symbol_id,
                Candle.source_id,
                Candle.timeframe,
                Candle.timestamp,
            ).in_(keys)
        )
        result = await self.session.execute(statement)
        return {model_identity(candle): candle for candle in result.scalars().all()}

    async def add_conflicts(
        self,
        performance_run_id: UUID,
        conflicts: list[CandleIngestionConflictRecord],
    ) -> None:
        self.session.add_all(
            [
                CandleIngestionConflict(
                    workspace_id=conflict.workspace_id,
                    performance_run_id=performance_run_id,
                    symbol_id=conflict.symbol_id,
                    source_id=conflict.source_id,
                    timeframe=conflict.timeframe,
                    timestamp=conflict.timestamp,
                    conflict_type=conflict.conflict_type.value,
                    existing_candle_json=conflict.existing_candle_json,
                    incoming_candle_json=conflict.incoming_candle_json,
                    resolution=conflict.resolution.value,
                )
                for conflict in conflicts
            ]
        )


def resolve_candle_write_decision(
    existing_state: CandleWriteState | None,
    incoming: NormalizedCandleInput,
) -> CandleWriteDecision:
    if existing_state is None:
        return CandleWriteDecision(CandleIngestionRowOutcome.INSERTED)
    if existing_state.is_final and not incoming.is_final:
        return CandleWriteDecision(
            outcome=CandleIngestionRowOutcome.SKIPPED_DUPLICATE,
            conflict_type=CandleIngestionConflictType.PARTIAL_AFTER_FINAL,
            resolution=CandleIngestionConflictResolution.KEPT_EXISTING,
        )
    if existing_state.is_final and incoming.is_final:
        if has_conflicting_final_values(existing_state, incoming):
            return CandleWriteDecision(
                outcome=CandleIngestionRowOutcome.CONFLICTED,
                conflict_type=CandleIngestionConflictType.FINAL_CONFLICT,
                resolution=CandleIngestionConflictResolution.KEPT_EXISTING,
            )
        return CandleWriteDecision(
            outcome=CandleIngestionRowOutcome.SKIPPED_DUPLICATE,
            conflict_type=CandleIngestionConflictType.DUPLICATE_FINAL,
            resolution=CandleIngestionConflictResolution.SKIPPED,
        )
    return CandleWriteDecision(CandleIngestionRowOutcome.UPDATED)


def has_conflicting_final_values(
    existing_state: CandleWriteState,
    incoming: NormalizedCandleInput,
) -> bool:
    return (
        existing_state.open != incoming.open
        or existing_state.high != incoming.high
        or existing_state.low != incoming.low
        or existing_state.close != incoming.close
        or existing_state.volume != incoming.volume
    )


def build_conflict_record(
    candidate: CandleIngestionCandidate,
    existing_state: CandleWriteState | None,
    conflict_type: CandleIngestionConflictType,
    resolution: CandleIngestionConflictResolution,
) -> CandleIngestionConflictRecord:
    return CandleIngestionConflictRecord(
        workspace_id=candidate.candle.workspace_id,
        symbol_id=candidate.candle.symbol_id,
        source_id=candidate.candle.source_id,
        timeframe=candidate.candle.timeframe.value,
        timestamp=candidate.candle.timestamp,
        conflict_type=conflict_type,
        existing_candle_json=serialize_state(existing_state),
        incoming_candle_json=serialize_incoming_candle(candidate.candle),
        resolution=resolution,
        row_reference=candidate.row_reference,
    )


def candle_identity(candle: NormalizedCandleInput) -> CandleIdentity:
    return (
        candle.workspace_id,
        candle.symbol_id,
        candle.source_id,
        candle.timeframe.value,
        candle.timestamp,
    )


def model_identity(candle: Candle) -> CandleIdentity:
    return (
        candle.workspace_id,
        candle.symbol_id,
        candle.source_id,
        candle.timeframe,
        candle.timestamp,
    )


def candle_state_from_model(candle: Candle) -> CandleWriteState:
    return CandleWriteState(
        candle_id=candle.id,
        workspace_id=candle.workspace_id,
        symbol_id=candle.symbol_id,
        source_id=candle.source_id,
        timeframe=candle.timeframe,
        timestamp=candle.timestamp,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        is_final=candle.is_final,
        exists_in_database=True,
    )


def candle_state_from_input(
    candle: NormalizedCandleInput,
    candle_id: UUID | None = None,
    exists_in_database: bool = False,
) -> CandleWriteState:
    return CandleWriteState(
        candle_id=candle_id,
        workspace_id=candle.workspace_id,
        symbol_id=candle.symbol_id,
        source_id=candle.source_id,
        timeframe=candle.timeframe.value,
        timestamp=candle.timestamp,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        is_final=candle.is_final,
        exists_in_database=exists_in_database,
    )


def insert_values_for_candle(candle: NormalizedCandleInput) -> dict[str, object]:
    import_batch_id = (
        candle.origin_reference_id
        if candle.origin_type in {CandleOriginType.CSV_IMPORT, CandleOriginType.JSON_IMPORT}
        else None
    )
    live_feed_event_id = (
        candle.origin_reference_id if candle.origin_type == CandleOriginType.LIVE_FEED else None
    )
    chart_screenshot_run_id = (
        candle.origin_reference_id
        if candle.origin_type == CandleOriginType.CHART_SCREENSHOT
        else None
    )
    return {
        "workspace_id": candle.workspace_id,
        "symbol_id": candle.symbol_id,
        "source_id": candle.source_id,
        "import_batch_id": import_batch_id,
        "live_feed_event_id": live_feed_event_id,
        "chart_screenshot_run_id": chart_screenshot_run_id,
        "timeframe": candle.timeframe.value,
        "timestamp": candle.timestamp,
        **insert_mutable_values(candle),
    }


def insert_mutable_values(candle: NormalizedCandleInput) -> dict[str, object]:
    return {
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "is_final": candle.is_final,
    }


def update_values_for_candle(candle: NormalizedCandleInput) -> dict[str, object]:
    values = insert_mutable_values(candle)
    if candle.origin_type == CandleOriginType.LIVE_FEED:
        values["live_feed_event_id"] = candle.origin_reference_id
    if candle.origin_type == CandleOriginType.CHART_SCREENSHOT:
        values["chart_screenshot_run_id"] = candle.origin_reference_id
    return values


def serialize_state(state: CandleWriteState | None) -> dict[str, object]:
    if state is None:
        return {}
    return {
        "id": str(state.candle_id) if state.candle_id is not None else None,
        "workspaceId": str(state.workspace_id),
        "symbolId": str(state.symbol_id),
        "sourceId": str(state.source_id),
        "timeframe": state.timeframe,
        "timestamp": state.timestamp.isoformat(),
        "open": decimal_to_json(state.open),
        "high": decimal_to_json(state.high),
        "low": decimal_to_json(state.low),
        "close": decimal_to_json(state.close),
        "volume": decimal_to_json(state.volume),
        "isFinal": state.is_final,
        "existsInDatabase": state.exists_in_database,
    }
