package providers

import (
	"context"
	"time"

	"github.com/shopspring/decimal"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
)

type MockProvider struct{}

func (MockProvider) Key() string {
	return "mock_polling"
}

func (MockProvider) FetchCandles(ctx context.Context, request FetchCandlesRequest) (FetchCandlesResult, error) {
	timeframe, err := candles.ParseTimeframe(request.Timeframe)
	if err != nil {
		return FetchCandlesResult{}, NewProviderError("unsupported_timeframe", "Unsupported timeframe")
	}
	start := time.Date(2026, 4, 29, 10, 0, 0, 0, time.UTC)
	if request.StartTime != nil {
		start = request.StartTime.UTC()
	}
	limit := request.Limit
	if limit <= 0 {
		limit = 100
	}
	items := make([]candles.ProviderCandleInput, 0, limit)
	for index := 0; index < limit; index++ {
		select {
		case <-ctx.Done():
			return FetchCandlesResult{}, ctx.Err()
		default:
		}
		timestamp := start.Add(time.Duration(index) * timeframe.Duration())
		if request.EndTime != nil && timestamp.After(request.EndTime.UTC()) {
			break
		}
		openValue := decimal.NewFromInt(65000 + int64(index))
		closeValue := openValue.Add(decimal.NewFromInt(5))
		highValue := closeValue.Add(decimal.NewFromInt(10))
		lowValue := openValue.Sub(decimal.NewFromInt(10))
		volumeValue := decimal.NewFromInt(10 + int64(index))
		volumeText := volumeValue.String()
		items = append(items, candles.ProviderCandleInput{
			Timestamp: timestamp,
			Open:      openValue.StringFixed(2),
			High:      highValue.StringFixed(2),
			Low:       lowValue.StringFixed(2),
			Close:     closeValue.StringFixed(2),
			Volume:    &volumeText,
			IsFinal:   true,
			ProviderMetadata: map[string]any{
				"provider":       "mock_polling",
				"providerSymbol": request.ProviderSymbol,
				"sequence":       index + 1,
			},
			RawItem: map[string]any{
				"provider":       "mock_polling",
				"sequence":       index + 1,
				"providerSymbol": request.ProviderSymbol,
			},
		})
	}
	return FetchCandlesResult{
		Candles: items,
		ProviderMetadata: map[string]any{
			"provider":  "mock_polling",
			"generated": true,
		},
	}, nil
}
