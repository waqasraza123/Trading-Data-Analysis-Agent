package providers

import (
	"context"
	"time"

	"github.com/google/uuid"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
)

type FetchCandlesRequest struct {
	WorkspaceID     uuid.UUID
	SourceID        uuid.UUID
	SymbolID        uuid.UUID
	Provider        string
	ProviderSymbol  string
	Timeframe       string
	StartTime       *time.Time
	EndTime         *time.Time
	Limit           int
	Timeout         time.Duration
	BaseURL         string
	Metadata        map[string]any
}

type FetchCandlesResult struct {
	Candles          []candles.ProviderCandleInput
	ProviderMetadata map[string]any
	Warnings         []ProviderMessage
	Errors           []ProviderMessage
}

type ProviderMessage struct {
	Code    string
	Message string
	RawItem map[string]any
}

type Provider interface {
	Key() string
	FetchCandles(ctx context.Context, request FetchCandlesRequest) (FetchCandlesResult, error)
}

type Registry struct {
	providers map[string]Provider
}

func NewRegistry(items ...Provider) *Registry {
	registry := &Registry{providers: map[string]Provider{}}
	for _, item := range items {
		if item != nil {
			registry.providers[item.Key()] = item
		}
	}
	return registry
}

func (r *Registry) Get(key string) (Provider, bool) {
	provider, ok := r.providers[key]
	return provider, ok
}

func (r *Registry) Keys() []string {
	keys := make([]string, 0, len(r.providers))
	for key := range r.providers {
		keys = append(keys, key)
	}
	return keys
}
