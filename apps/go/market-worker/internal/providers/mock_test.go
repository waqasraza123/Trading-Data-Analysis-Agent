package providers

import (
	"context"
	"testing"
	"time"
)

func TestMockProviderDeterministicCandles(t *testing.T) {
	start := time.Date(2026, 5, 6, 10, 0, 0, 0, time.UTC)
	result, err := MockProvider{}.FetchCandles(context.Background(), FetchCandlesRequest{
		ProviderSymbol: "BTCUSDT",
		Timeframe:      "1m",
		StartTime:      &start,
		Limit:          2,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(result.Candles) != 2 {
		t.Fatalf("expected 2 candles, got %d", len(result.Candles))
	}
	if result.Candles[0].Open != "65000.00" || result.Candles[1].Open != "65001.00" {
		t.Fatalf("unexpected opens: %#v", result.Candles)
	}
}
