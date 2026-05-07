package polling

import (
	"github.com/google/uuid"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/providers"
)

func NormalizeProviderCandles(items []candles.ProviderCandleInput, workspaceID uuid.UUID, sourceID uuid.UUID, symbolID uuid.UUID, timeframe string, requestID *uuid.UUID) ([]candles.Candle, []candles.ValidationIssue) {
	normalized := make([]candles.Candle, 0, len(items))
	invalid := make([]candles.ValidationIssue, 0)
	for _, item := range items {
		candle, err := candles.NormalizeProviderCandle(item, workspaceID, sourceID, symbolID, timeframe, requestID)
		if err != nil {
			invalid = append(invalid, candles.ValidationIssue{
				Code:    err.Error(),
				Message: "Provider candle could not be normalized",
				RawItem: item.RawItem,
			})
			continue
		}
		normalized = append(normalized, candle)
	}
	return normalized, invalid
}

func ProviderMessagesToMetadata(warnings []providers.ProviderMessage, errors []providers.ProviderMessage) map[string]any {
	return map[string]any{
		"warningCount":       len(warnings),
		"providerErrorCount": len(errors),
	}
}
