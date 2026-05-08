package live

import (
	"errors"
	"time"

	"github.com/google/uuid"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
)

type EventType string

const (
	EventTypeCandlePartial EventType = "candle_partial"
	EventTypeCandleFinal   EventType = "candle_final"
	EventTypeHeartbeat     EventType = "heartbeat"
	EventTypeReconnect     EventType = "reconnect"
	EventTypeError         EventType = "error"
	EventTypeSnapshot      EventType = "snapshot"
	EventTypeIgnored       EventType = "ignored"
)

type EventProcessingStatus string

const (
	EventStatusReceived  EventProcessingStatus = "received"
	EventStatusProcessed EventProcessingStatus = "processed"
	EventStatusIgnored   EventProcessingStatus = "ignored"
	EventStatusFailed    EventProcessingStatus = "failed"
)

var ErrSubscriptionDisabled = errors.New("live stream disabled for this subscription")

type Subscription struct {
	ID              uuid.UUID
	WorkspaceID     uuid.UUID
	SourceID        uuid.UUID
	SymbolID        uuid.UUID
	Symbol          string
	Status          string
	Timeframe       string
	Provider        string
	ConfigJSON      map[string]any
	LastMessageAt   *time.Time
	LastFinalCandle *time.Time
	LeaseExpiresAt  *time.Time
	WorkerID        *string
	CreatedAt       time.Time
}

type ParsedEvent struct {
	Type              EventType
	ProviderTimestamp *time.Time
	Candle            *candles.Candle
	ErrorMessage      string
	Payload           map[string]any
	RawMessage        []byte
}
