package candles

import (
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/shopspring/decimal"
)

func TestValidateRejectsInvalidOHLC(t *testing.T) {
	workspaceID := uuid.New()
	candle := Candle{
		WorkspaceID: workspaceID,
		SourceID:    uuid.New(),
		SymbolID:    uuid.New(),
		Timeframe:   "1m",
		Timestamp:   time.Date(2026, 5, 6, 10, 0, 0, 0, time.UTC),
		Open:        decimal.NewFromInt(100),
		High:        decimal.NewFromInt(90),
		Low:         decimal.NewFromInt(80),
		Close:       decimal.NewFromInt(95),
		IsFinal:     true,
	}
	issue := Validate(candle, SymbolSourceState{
		WorkspaceID:     workspaceID,
		SourceWorkspace: workspaceID,
		SymbolActive:    true,
		SourceActive:    true,
		SourceType:      "api_polling",
	})
	if issue == nil || issue.Code != "invalid_ohlc_relationship" {
		t.Fatalf("expected invalid OHLC issue, got %#v", issue)
	}
}
