from app.modules.equity_data.adapters.alpaca import AlpacaEquityDataProvider
from app.modules.equity_data.adapters.base import EquityDataProvider
from app.modules.equity_data.adapters.csv_import import CsvEquityImportProvider
from app.modules.equity_data.adapters.generic_http import GenericHttpEquityDataProvider
from app.modules.equity_data.adapters.mock import MockEquityDataProvider
from app.modules.equity_data.adapters.polygon import PolygonEquityDataProvider

EQUITY_DATA_PROVIDERS: dict[str, EquityDataProvider] = {
    MockEquityDataProvider().key(): MockEquityDataProvider(),
    CsvEquityImportProvider().key(): CsvEquityImportProvider(),
    PolygonEquityDataProvider().key(): PolygonEquityDataProvider(),
    AlpacaEquityDataProvider().key(): AlpacaEquityDataProvider(),
    GenericHttpEquityDataProvider().key(): GenericHttpEquityDataProvider(),
}


def get_equity_data_provider(provider: str) -> EquityDataProvider:
    from app.core.errors import AppError
    from app.modules.equity_data.normalizer import normalize_provider

    key = normalize_provider(provider)
    adapter = EQUITY_DATA_PROVIDERS.get(key)
    if adapter is None:
        raise AppError(
            422, "equity_data_provider_unsupported", "Equity data provider is not supported"
        )
    return adapter
