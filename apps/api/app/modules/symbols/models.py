from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class MarketType(StrEnum):
    FOREX = "forex"
    CRYPTO = "crypto"
    STOCK = "stock"
    INDEX = "index"
    COMMODITY = "commodity"


class Symbol(Base):
    __tablename__ = "symbols"
    __table_args__ = (
        CheckConstraint(
            "market_type in ('forex', 'crypto', 'stock', 'index', 'commodity')",
            name="market_type_allowed",
        ),
        CheckConstraint("pip_size is null or pip_size > 0", name="pip_size_positive"),
        CheckConstraint("tick_size is null or tick_size > 0", name="tick_size_positive"),
        CheckConstraint("price_precision >= 0", name="price_precision_non_negative"),
        CheckConstraint("quantity_precision >= 0", name="quantity_precision_non_negative"),
        Index("ix_symbols_symbol", "symbol", unique=True),
        Index("ix_symbols_market_type", "market_type"),
    )

    id = uuid_primary_key()
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    market_type: Mapped[str] = mapped_column(String(32), nullable=False)
    base_asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quote_asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pip_size: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    tick_size: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    price_precision: Mapped[int] = mapped_column(nullable=False, default=10, server_default="10")
    quantity_precision: Mapped[int] = mapped_column(nullable=False, default=10, server_default="10")
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
