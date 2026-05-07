package providers

import "context"

type GenericOHLCHTTPProvider struct{}

func (GenericOHLCHTTPProvider) Key() string {
	return "generic_ohlc_http"
}

func (GenericOHLCHTTPProvider) FetchCandles(ctx context.Context, request FetchCandlesRequest) (FetchCandlesResult, error) {
	return FetchCandlesResult{
		ProviderMetadata: map[string]any{
			"provider":   "generic_ohlc_http",
			"configured": false,
		},
		Warnings: []ProviderMessage{{
			Code:    "generic_adapter_stub",
			Message: "Generic OHLC HTTP polling requires provider-specific mapping before use",
		}},
		Errors: []ProviderMessage{{
			Code:    "generic_adapter_not_configured",
			Message: "Generic OHLC HTTP adapter is a safe stub and did not fetch candles",
		}},
	}, nil
}
