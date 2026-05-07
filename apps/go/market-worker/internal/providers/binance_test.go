package providers

import "testing"

func TestParseBinanceKline(t *testing.T) {
	item := []any{
		float64(1714993200000),
		"64000.10",
		"64100.20",
		"63900.30",
		"64050.40",
		"12.5",
		float64(1714993259999),
	}
	candle, err := parseBinanceKline(item, FetchCandlesRequest{ProviderSymbol: "btcusdt", Timeframe: "1m"}, 1714993260000)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if candle.Open != "64000.10" || !candle.IsFinal {
		t.Fatalf("unexpected parsed candle: %#v", candle)
	}
}
