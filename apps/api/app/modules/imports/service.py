from collections import Counter
from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.candles.normalizer import normalize_candle_payload
from app.modules.candles.repository import CandleRepository
from app.modules.candles.schemas import (
    CandleOriginType,
    CandleUpsertStatus,
    NormalizedCandleInput,
)
from app.modules.candles.timeframes import Timeframe, expected_timestamps
from app.modules.candles.validator import validate_candle
from app.modules.data_sources.models import DataSource
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.imports.models import ImportBatch, ImportBatchStatus, ImportError
from app.modules.imports.parser import ParsedCandleRow, ParsedRowError, parse_csv_candles
from app.modules.imports.repository import ImportRepository
from app.modules.imports.schemas import CsvCandleImportRequest, JsonCandleImportRequest
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository


class ImportProcessingResult:
    def __init__(
        self,
        batch: ImportBatch,
        normalized_valid_candles: list[NormalizedCandleInput],
    ) -> None:
        self.batch = batch
        self.normalized_valid_candles = normalized_valid_candles


class ImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.import_repository = ImportRepository(session)
        self.candle_repository = CandleRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def process_json_import(self, payload: JsonCandleImportRequest) -> ImportBatch:
        try:
            symbol, data_source = await self.resolve_symbol_and_source(
                symbol_id=payload.symbol_id,
                source_id=payload.source_id,
                workspace_id=payload.workspace_id,
            )
            batch = await self.create_processing_batch(
                workspace_id=payload.workspace_id,
                user_id=payload.user_id,
                source_id=payload.source_id,
                symbol_id=payload.symbol_id,
                timeframe=payload.timeframe,
                rows_received=len(payload.candles),
                file_name=None,
            )
            rows = [
                ParsedCandleRow(
                    row_number=index,
                    payload=candle,
                    raw_row=candle.model_dump(mode="json"),
                )
                for index, candle in enumerate(payload.candles, start=1)
            ]
            result = await self.process_rows(
                batch=batch,
                rows=rows,
                parse_errors=[],
                symbol=symbol,
                data_source=data_source,
                timeframe=payload.timeframe,
                origin_type=CandleOriginType.JSON_IMPORT,
            )
            await self.session.commit()
            return result.batch
        except Exception:
            await self.session.rollback()
            raise

    async def process_csv_import(
        self,
        payload: CsvCandleImportRequest,
        csv_text: str,
    ) -> ImportBatch:
        try:
            symbol, data_source = await self.resolve_symbol_and_source(
                symbol_id=payload.symbol_id,
                source_id=payload.source_id,
                workspace_id=payload.workspace_id,
            )
            parse_result = parse_csv_candles(csv_text)
            batch = await self.create_processing_batch(
                workspace_id=payload.workspace_id,
                user_id=payload.user_id,
                source_id=payload.source_id,
                symbol_id=payload.symbol_id,
                timeframe=payload.timeframe,
                rows_received=len(parse_result.rows) + len(parse_result.errors),
                file_name=payload.file_name,
            )
            result = await self.process_rows(
                batch=batch,
                rows=parse_result.rows,
                parse_errors=parse_result.errors,
                symbol=symbol,
                data_source=data_source,
                timeframe=payload.timeframe,
                origin_type=CandleOriginType.CSV_IMPORT,
            )
            await self.session.commit()
            return result.batch
        except Exception:
            await self.session.rollback()
            raise

    async def get_import_batch(self, import_batch_id: UUID) -> ImportBatch:
        batch = await self.import_repository.get_batch(import_batch_id)
        if batch is None:
            raise AppError(404, "import_batch_not_found", "Import batch not found")
        return batch

    async def list_import_errors(
        self,
        import_batch_id: UUID,
        limit: int,
        offset: int,
    ) -> list[ImportError]:
        await self.get_import_batch(import_batch_id)
        return await self.import_repository.list_errors(
            import_batch_id=import_batch_id,
            limit=limit,
            offset=offset,
        )

    async def resolve_symbol_and_source(
        self,
        symbol_id: UUID,
        source_id: UUID,
        workspace_id: UUID,
    ) -> tuple[Symbol, DataSource]:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        data_source = await self.data_source_repository.get_by_id(source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if data_source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
        return symbol, data_source

    async def create_processing_batch(
        self,
        workspace_id: UUID,
        user_id: UUID | None,
        source_id: UUID,
        symbol_id: UUID,
        timeframe: Timeframe,
        rows_received: int,
        file_name: str | None,
    ) -> ImportBatch:
        now = utc_now()
        return await self.import_repository.create_batch(
            ImportBatch(
                workspace_id=workspace_id,
                user_id=user_id,
                source_id=source_id,
                symbol_id=symbol_id,
                timeframe=timeframe.value,
                file_name=file_name,
                status=ImportBatchStatus.PROCESSING,
                rows_received=rows_received,
                rows_valid=0,
                rows_invalid=0,
                duplicates_skipped=0,
                missing_candles_detected=0,
                started_at=now,
            )
        )

    async def process_rows(
        self,
        batch: ImportBatch,
        rows: list[ParsedCandleRow],
        parse_errors: list[ParsedRowError],
        symbol: Symbol,
        data_source: DataSource,
        timeframe: Timeframe,
        origin_type: CandleOriginType,
    ) -> ImportProcessingResult:
        normalized_valid_candles: list[NormalizedCandleInput] = []
        error_codes: list[str] = []
        invalid_row_count = 0
        for parse_error in parse_errors:
            await self.record_import_error(batch.id, parse_error)
            error_codes.append(parse_error.error_code)
            invalid_row_count += 1
        duplicate_count = 0
        for row in rows:
            normalized_candle = await self.normalize_row(
                batch=batch,
                row=row,
                timeframe=timeframe,
                origin_type=origin_type,
            )
            if normalized_candle is None:
                invalid_row_count += 1
                continue
            validation_result = validate_candle(
                candle=normalized_candle,
                symbol=symbol,
                data_source=data_source,
            )
            if not validation_result.is_valid:
                for issue in validation_result.issues:
                    await self.import_repository.add_error(
                        ImportError(
                            import_batch_id=batch.id,
                            row_number=row.row_number,
                            error_code=issue.code.value,
                            error_message=issue.message,
                            raw_row_json=row.raw_row,
                        )
                    )
                    error_codes.append(issue.code.value)
                invalid_row_count += 1
                continue
            upsert_result = await self.candle_repository.upsert_normalized_candle(normalized_candle)
            if upsert_result.status in {
                CandleUpsertStatus.DUPLICATE_FINAL,
                CandleUpsertStatus.IGNORED_LATE_PARTIAL,
            }:
                duplicate_count += 1
                continue
            if upsert_result.status == CandleUpsertStatus.CONFLICTING_FINAL:
                await self.import_repository.add_error(
                    ImportError(
                        import_batch_id=batch.id,
                        row_number=row.row_number,
                        error_code="conflicting_final_candle",
                        error_message=upsert_result.message,
                        raw_row_json=row.raw_row,
                    )
                )
                error_codes.append("conflicting_final_candle")
                invalid_row_count += 1
                continue
            normalized_valid_candles.append(normalized_candle)
        self.finalize_batch(
            batch=batch,
            rows_valid=len(normalized_valid_candles),
            rows_invalid=invalid_row_count,
            duplicates_skipped=duplicate_count,
            missing_candles_detected=self.count_missing_candles(
                normalized_valid_candles,
                timeframe,
            ),
            error_codes=error_codes,
        )
        return ImportProcessingResult(
            batch=batch,
            normalized_valid_candles=normalized_valid_candles,
        )

    async def normalize_row(
        self,
        batch: ImportBatch,
        row: ParsedCandleRow,
        timeframe: Timeframe,
        origin_type: CandleOriginType,
    ) -> NormalizedCandleInput | None:
        try:
            return normalize_candle_payload(
                payload=row.payload,
                workspace_id=batch.workspace_id,
                symbol_id=batch.symbol_id,
                source_id=batch.source_id,
                timeframe=timeframe,
                is_final=True,
                origin_type=origin_type,
                origin_reference_id=batch.id,
            )
        except AppError as error:
            await self.import_repository.add_error(
                ImportError(
                    import_batch_id=batch.id,
                    row_number=row.row_number,
                    error_code=error.code,
                    error_message=error.message,
                    raw_row_json=row.raw_row,
                )
            )
            return None
        except ValidationError as error:
            await self.import_repository.add_error(
                ImportError(
                    import_batch_id=batch.id,
                    row_number=row.row_number,
                    error_code="invalid_row",
                    error_message=error.errors()[0]["msg"],
                    raw_row_json=row.raw_row,
                )
            )
            return None

    async def record_import_error(self, import_batch_id: UUID, parse_error: ParsedRowError) -> None:
        await self.import_repository.add_error(
            ImportError(
                import_batch_id=import_batch_id,
                row_number=parse_error.row_number,
                error_code=parse_error.error_code,
                error_message=parse_error.error_message,
                raw_row_json=parse_error.raw_row,
            )
        )

    def finalize_batch(
        self,
        batch: ImportBatch,
        rows_valid: int,
        rows_invalid: int,
        duplicates_skipped: int,
        missing_candles_detected: int,
        error_codes: list[str],
    ) -> None:
        batch.rows_valid = rows_valid
        batch.rows_invalid = rows_invalid
        batch.duplicates_skipped = duplicates_skipped
        batch.missing_candles_detected = missing_candles_detected
        batch.data_quality_score = self.calculate_import_quality_score(
            rows_received=batch.rows_received,
            rows_valid=rows_valid,
            rows_invalid=rows_invalid,
            duplicates_skipped=duplicates_skipped,
            missing_candles_detected=missing_candles_detected,
        )
        batch.error_summary_json = dict(Counter(error_codes)) if error_codes else None
        batch.status = self.resolve_final_status(
            rows_valid=rows_valid,
            rows_invalid=rows_invalid,
            duplicates_skipped=duplicates_skipped,
            missing_candles_detected=missing_candles_detected,
        )
        batch.completed_at = utc_now()

    def resolve_final_status(
        self,
        rows_valid: int,
        rows_invalid: int,
        duplicates_skipped: int,
        missing_candles_detected: int,
    ) -> ImportBatchStatus:
        if rows_valid == 0:
            return ImportBatchStatus.FAILED
        if rows_invalid > 0 or duplicates_skipped > 0 or missing_candles_detected > 0:
            return ImportBatchStatus.COMPLETED_WITH_WARNINGS
        return ImportBatchStatus.COMPLETED

    def count_missing_candles(
        self,
        normalized_candles: list[NormalizedCandleInput],
        timeframe: Timeframe,
    ) -> int:
        if len(normalized_candles) < 2:
            return 0
        timestamps = sorted({candle.timestamp for candle in normalized_candles})
        expected = expected_timestamps(timestamps[0], timestamps[-1], timeframe)
        return max(len(set(expected) - set(timestamps)), 0)

    def calculate_import_quality_score(
        self,
        rows_received: int,
        rows_valid: int,
        rows_invalid: int,
        duplicates_skipped: int,
        missing_candles_detected: int,
    ) -> Decimal:
        if rows_received <= 0:
            return Decimal("0")
        penalty_count = rows_invalid + duplicates_skipped + missing_candles_detected
        score = Decimal(rows_valid) / Decimal(rows_received + missing_candles_detected)
        penalty = Decimal(penalty_count) / Decimal(rows_received + missing_candles_detected)
        adjusted_score = max(Decimal("0"), score - (penalty * Decimal("0.25")))
        return min(Decimal("1"), adjusted_score).quantize(Decimal("0.00001"))
