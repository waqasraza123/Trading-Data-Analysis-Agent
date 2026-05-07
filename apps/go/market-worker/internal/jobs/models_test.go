package jobs

import (
	"testing"

	"github.com/google/uuid"
)

func TestDecodePayload(t *testing.T) {
	workspaceID := uuid.New()
	sourceID := uuid.New()
	symbolID := uuid.New()
	request, err := DecodePayload(map[string]any{
		"workspaceId":    workspaceID.String(),
		"sourceId":       sourceID.String(),
		"symbolId":       symbolID.String(),
		"provider":       "mock_polling",
		"providerSymbol": "BTCUSDT",
		"timeframe":      "1m",
		"limit":          float64(25),
	}, nil, 1000)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if request.WorkspaceID != workspaceID || request.Limit != 25 {
		t.Fatalf("unexpected request: %#v", request)
	}
}
