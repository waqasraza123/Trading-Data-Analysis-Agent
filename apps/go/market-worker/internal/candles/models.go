package candles

import (
	"time"

	"github.com/google/uuid"
	"github.com/shopspring/decimal"
)

type Candle struct {
	WorkspaceID       uuid.UUID
	SymbolID          uuid.UUID
	SourceID          uuid.UUID
	Timeframe         string
	Timestamp         time.Time
	Open              decimal.Decimal
	High              decimal.Decimal
	Low               decimal.Decimal
	Close             decimal.Decimal
	Volume            *decimal.Decimal
	IsFinal           bool
	OriginType        string
	OriginReferenceID *uuid.UUID
	ProviderMetadata  map[string]any
	RawItem           map[string]any
}

type ExistingCandle struct {
	ID        uuid.UUID
	Candle    Candle
	IsFinal   bool
	Exists    bool
	CreatedAt time.Time
}

type Identity struct {
	WorkspaceID uuid.UUID
	SymbolID    uuid.UUID
	SourceID    uuid.UUID
	Timeframe   string
	Timestamp   time.Time
}

type ValidationIssue struct {
	Code    string
	Message string
	RawItem map[string]any
}

type ValidationResult struct {
	Valid  []Candle
	Invalid []ValidationIssue
}

type WriteCounts struct {
	Received          int `json:"received"`
	Valid             int `json:"valid"`
	Inserted          int `json:"inserted"`
	Updated           int `json:"updated"`
	DuplicateSkipped  int `json:"duplicateSkipped"`
	Conflicted        int `json:"conflicted"`
	Invalid           int `json:"invalid"`
	Failed            int `json:"failed"`
	Batches           int `json:"batches"`
}

func (c Candle) Identity() Identity {
	return Identity{
		WorkspaceID: c.WorkspaceID,
		SymbolID:    c.SymbolID,
		SourceID:    c.SourceID,
		Timeframe:   c.Timeframe,
		Timestamp:   c.Timestamp,
	}
}
