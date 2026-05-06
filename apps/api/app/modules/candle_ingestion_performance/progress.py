from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.modules.candle_ingestion_performance.diagnostics import (
    build_diagnostics_json,
    resolve_performance_status,
)
from app.modules.candle_ingestion_performance.models import (
    CandleIngestionMode,
    CandleIngestionPerformanceRun,
    CandleIngestionPerformanceStatus,
)
from app.modules.candle_ingestion_performance.schemas import CandleIngestionCounters


class CandleIngestionProgressTracker:
    def __init__(
        self,
        session: AsyncSession,
        run: CandleIngestionPerformanceRun,
        batch_size: int,
        progress_every_rows: int,
        copy_path_enabled: bool,
    ) -> None:
        self.session = session
        self.run = run
        self.batch_size = batch_size
        self.progress_every_rows = progress_every_rows
        self.copy_path_enabled = copy_path_enabled
        self.counters = CandleIngestionCounters()
        self.started_at = perf_counter()
        self.next_progress_row = progress_every_rows

    @classmethod
    async def start(
        cls,
        session: AsyncSession,
        workspace_id: UUID,
        ingestion_mode: CandleIngestionMode,
        batch_size: int,
        progress_every_rows: int,
        copy_path_enabled: bool,
        import_batch_id: UUID | None = None,
        provider_polling_request_id: UUID | None = None,
        source_id: UUID | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
    ) -> "CandleIngestionProgressTracker":
        run = CandleIngestionPerformanceRun(
            workspace_id=workspace_id,
            import_batch_id=import_batch_id,
            provider_polling_request_id=provider_polling_request_id,
            source_id=source_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            status=CandleIngestionPerformanceStatus.RUNNING.value,
            ingestion_mode=ingestion_mode.value,
            diagnostics_json={},
        )
        session.add(run)
        await session.flush()
        await session.refresh(run)
        return cls(
            session=session,
            run=run,
            batch_size=batch_size,
            progress_every_rows=progress_every_rows,
            copy_path_enabled=copy_path_enabled,
        )

    async def record(self, counters: CandleIngestionCounters) -> None:
        self.counters.add(counters)
        self.apply_counters(elapsed_ms=None)
        if self.counters.rows_received >= self.next_progress_row:
            await self.session.flush()
            while self.counters.rows_received >= self.next_progress_row:
                self.next_progress_row += self.progress_every_rows

    async def finish(self) -> None:
        elapsed_ms = int((perf_counter() - self.started_at) * 1000)
        self.run.status = resolve_performance_status(self.counters).value
        self.apply_counters(elapsed_ms=elapsed_ms)
        await self.session.flush()

    async def fail(self, error_message: str) -> None:
        elapsed_ms = int((perf_counter() - self.started_at) * 1000)
        self.run.status = CandleIngestionPerformanceStatus.FAILED.value
        self.apply_counters(elapsed_ms=elapsed_ms)
        self.run.diagnostics_json = {
            **self.run.diagnostics_json,
            "errorMessage": error_message,
        }
        await self.session.flush()

    def apply_counters(self, elapsed_ms: int | None) -> None:
        self.run.rows_received = self.counters.rows_received
        self.run.rows_validated = self.counters.rows_validated
        self.run.rows_inserted = self.counters.rows_inserted
        self.run.rows_updated = self.counters.rows_updated
        self.run.rows_skipped_duplicate = self.counters.rows_skipped_duplicate
        self.run.rows_conflicted = self.counters.rows_conflicted
        self.run.rows_failed = self.counters.rows_failed
        self.run.batch_count = self.counters.batch_count
        self.run.elapsed_ms = elapsed_ms
        self.run.updated_at = utc_now()
        self.run.diagnostics_json = build_diagnostics_json(
            counters=self.counters,
            batch_size=self.batch_size,
            progress_every_rows=self.progress_every_rows,
            copy_path_enabled=self.copy_path_enabled,
            elapsed_ms=elapsed_ms,
        )
