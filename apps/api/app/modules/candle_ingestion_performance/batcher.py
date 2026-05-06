from collections.abc import Iterable, Iterator, Sequence

from app.core.errors import AppError


def validate_ingestion_batch_size(batch_size: int) -> int:
    if batch_size < 1:
        raise AppError(
            500,
            "invalid_candle_ingestion_batch_size",
            "Candle ingestion batch size must be positive",
        )
    return batch_size


def validate_ingestion_request_size(row_count: int, max_rows: int) -> None:
    if row_count > max_rows:
        raise AppError(
            413,
            "candle_ingestion_row_limit_exceeded",
            "Candle ingestion request exceeds the configured row limit",
        )


def iter_chunks[Item](items: Iterable[Item], batch_size: int) -> Iterator[list[Item]]:
    resolved_batch_size = validate_ingestion_batch_size(batch_size)
    chunk: list[Item] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= resolved_batch_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def chunk_sequence[Item](items: Sequence[Item], batch_size: int) -> Iterator[Sequence[Item]]:
    resolved_batch_size = validate_ingestion_batch_size(batch_size)
    for start_index in range(0, len(items), resolved_batch_size):
        yield items[start_index : start_index + resolved_batch_size]
