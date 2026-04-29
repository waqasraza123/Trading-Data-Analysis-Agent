from decimal import Decimal

from app.modules.symbols.models import MarketType
from app.modules.symbols.schemas import SymbolCreate

DEFAULT_SYMBOLS: tuple[SymbolCreate, ...] = (
    SymbolCreate(
        symbol="EURUSD",
        display_name="EUR/USD",
        market_type=MarketType.FOREX,
        base_asset="EUR",
        quote_asset="USD",
        pip_size=Decimal("0.0001"),
    ),
    SymbolCreate(
        symbol="GBPUSD",
        display_name="GBP/USD",
        market_type=MarketType.FOREX,
        base_asset="GBP",
        quote_asset="USD",
        pip_size=Decimal("0.0001"),
    ),
    SymbolCreate(
        symbol="USDJPY",
        display_name="USD/JPY",
        market_type=MarketType.FOREX,
        base_asset="USD",
        quote_asset="JPY",
        pip_size=Decimal("0.01"),
    ),
    SymbolCreate(
        symbol="XAUUSD",
        display_name="Gold/USD",
        market_type=MarketType.COMMODITY,
        base_asset="XAU",
        quote_asset="USD",
        pip_size=Decimal("0.01"),
    ),
    SymbolCreate(
        symbol="BTCUSDT",
        display_name="BTC/USDT",
        market_type=MarketType.CRYPTO,
        base_asset="BTC",
        quote_asset="USDT",
        tick_size=Decimal("0.01"),
    ),
    SymbolCreate(
        symbol="ETHUSDT",
        display_name="ETH/USDT",
        market_type=MarketType.CRYPTO,
        base_asset="ETH",
        quote_asset="USDT",
        tick_size=Decimal("0.01"),
    ),
)
