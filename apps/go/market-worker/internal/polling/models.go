package polling

import (
	"time"

	"github.com/google/uuid"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
)

type Result struct {
	WorkspaceID       uuid.UUID          `json:"workspaceId"`
	Provider          string             `json:"provider"`
	ProviderSymbol    string             `json:"providerSymbol"`
	Timeframe         string             `json:"timeframe"`
	Received          int                `json:"received"`
	Stored            int                `json:"stored"`
	Skipped           int                `json:"skipped"`
	Conflicted        int                `json:"conflicted"`
	Invalid           int                `json:"invalid"`
	Warnings          int                `json:"warnings"`
	ProviderErrors    int                `json:"providerErrors"`
	CompletedAt       time.Time          `json:"completedAt"`
	Counts            candles.WriteCounts `json:"counts"`
	ProviderMetadata  map[string]any     `json:"providerMetadata"`
}
