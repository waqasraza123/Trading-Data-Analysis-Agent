from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class EquitySwingScanTarget:
    symbol_id: UUID
    ticker: str
    timeframe: str
    average_volume: Decimal | None = None
    source_id: UUID | None = None
    member_id: UUID | None = None
    watchlist_item_id: UUID | None = None
