from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.symbols.models import MarketType


class SymbolBase(ApiSchema):
    symbol: str = Field(min_length=1, max_length=32)
    display_name: str = Field(min_length=1, max_length=120)
    market_type: MarketType
    base_asset: str | None = Field(default=None, max_length=32)
    quote_asset: str | None = Field(default=None, max_length=32)
    pip_size: Decimal | None = Field(default=None, gt=0)
    tick_size: Decimal | None = Field(default=None, gt=0)
    price_precision: int = Field(default=10, ge=0)
    quantity_precision: int = Field(default=10, ge=0)
    is_active: bool = True

    @field_validator("symbol", "base_asset", "quote_asset")
    @classmethod
    def normalize_market_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_market_size_requirements(self) -> "SymbolBase":
        if self.market_type == MarketType.FOREX and self.pip_size is None:
            msg = "Forex symbols require pip_size"
            raise ValueError(msg)
        if self.market_type == MarketType.CRYPTO and self.tick_size is None:
            msg = "Crypto symbols require tick_size"
            raise ValueError(msg)
        return self


class SymbolCreate(SymbolBase):
    pass


class SymbolUpdate(ApiSchema):
    symbol: str | None = Field(default=None, min_length=1, max_length=32)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    market_type: MarketType | None = None
    base_asset: str | None = Field(default=None, max_length=32)
    quote_asset: str | None = Field(default=None, max_length=32)
    pip_size: Decimal | None = Field(default=None, gt=0)
    tick_size: Decimal | None = Field(default=None, gt=0)
    price_precision: int | None = Field(default=None, ge=0)
    quantity_precision: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("symbol", "base_asset", "quote_asset")
    @classmethod
    def normalize_market_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class SymbolRead(ApiReadSchema):
    id: UUID
    symbol: str
    display_name: str
    market_type: MarketType
    base_asset: str | None
    quote_asset: str | None
    pip_size: Decimal | None
    tick_size: Decimal | None
    price_precision: int
    quantity_precision: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
