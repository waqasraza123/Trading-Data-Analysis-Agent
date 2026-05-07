package jobs

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
)

var SupportedJobTypes = map[string]bool{
	"provider_polling.fetch": true,
	"market_data.poll":       true,
	"candles.fetch_provider": true,
	"provider_polling.run":   true,
}

type Job struct {
	ID          uuid.UUID
	WorkspaceID *uuid.UUID
	QueueName   string
	JobType     string
	Attempts    int
	MaxAttempts int
	LockedBy    string
	Payload     map[string]any
}

type PollingRequest struct {
	ID             *uuid.UUID
	WorkspaceID    uuid.UUID
	SourceID       uuid.UUID
	SymbolID       uuid.UUID
	Provider       string
	ProviderSymbol string
	Timeframe      string
	StartTime      *time.Time
	EndTime        *time.Time
	Limit          int
	Metadata       map[string]any
}

func DecodePayload(payload map[string]any, fallbackWorkspaceID *uuid.UUID, maxLimit int) (PollingRequest, error) {
	if requestIDText, ok := stringField(payload, "providerPollingRequestId", "provider_polling_request_id"); ok {
		requestID, err := uuid.Parse(requestIDText)
		if err != nil {
			return PollingRequest{}, fmt.Errorf("invalid_provider_polling_request_id")
		}
		return PollingRequest{ID: &requestID, Limit: maxLimit, Metadata: payload}, nil
	}
	workspaceID, err := uuidField(payload, fallbackWorkspaceID, "workspaceId", "workspace_id")
	if err != nil {
		return PollingRequest{}, err
	}
	sourceID, err := requiredUUIDField(payload, "sourceId", "source_id")
	if err != nil {
		return PollingRequest{}, err
	}
	symbolID, err := requiredUUIDField(payload, "symbolId", "symbol_id")
	if err != nil {
		return PollingRequest{}, err
	}
	provider, ok := stringField(payload, "provider")
	if !ok {
		return PollingRequest{}, fmt.Errorf("missing_provider")
	}
	providerSymbol, ok := stringField(payload, "providerSymbol", "provider_symbol")
	if !ok {
		return PollingRequest{}, fmt.Errorf("missing_provider_symbol")
	}
	timeframe, ok := stringField(payload, "timeframe")
	if !ok {
		return PollingRequest{}, fmt.Errorf("missing_timeframe")
	}
	limit := intField(payload, "limit", maxLimit)
	if limit <= 0 || limit > maxLimit {
		limit = maxLimit
	}
	startTime, err := optionalTimeField(payload, "startTime", "start_time")
	if err != nil {
		return PollingRequest{}, err
	}
	endTime, err := optionalTimeField(payload, "endTime", "end_time")
	if err != nil {
		return PollingRequest{}, err
	}
	return PollingRequest{
		WorkspaceID:    workspaceID,
		SourceID:       sourceID,
		SymbolID:       symbolID,
		Provider:       provider,
		ProviderSymbol: providerSymbol,
		Timeframe:      timeframe,
		StartTime:      startTime,
		EndTime:        endTime,
		Limit:          limit,
		Metadata:       payload,
	}, nil
}

func PayloadFromJSON(text string) (map[string]any, error) {
	payload := map[string]any{}
	if text == "" {
		return payload, nil
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		return nil, err
	}
	return payload, nil
}

func stringField(payload map[string]any, names ...string) (string, bool) {
	for _, name := range names {
		if value, ok := payload[name]; ok {
			text := fmt.Sprint(value)
			if text != "" && text != "<nil>" {
				return text, true
			}
		}
	}
	return "", false
}

func uuidField(payload map[string]any, fallback *uuid.UUID, names ...string) (uuid.UUID, error) {
	if text, ok := stringField(payload, names...); ok {
		return uuid.Parse(text)
	}
	if fallback != nil {
		return *fallback, nil
	}
	return uuid.UUID{}, fmt.Errorf("missing_workspace_id")
}

func requiredUUIDField(payload map[string]any, names ...string) (uuid.UUID, error) {
	text, ok := stringField(payload, names...)
	if !ok {
		return uuid.UUID{}, fmt.Errorf("missing_%s", names[0])
	}
	parsed, err := uuid.Parse(text)
	if err != nil {
		return uuid.UUID{}, fmt.Errorf("invalid_%s", names[0])
	}
	return parsed, nil
}

func intField(payload map[string]any, name string, fallback int) int {
	value, ok := payload[name]
	if !ok {
		return fallback
	}
	switch typed := value.(type) {
	case float64:
		return int(typed)
	case int:
		return typed
	default:
		var parsed int
		if _, err := fmt.Sscanf(fmt.Sprint(value), "%d", &parsed); err == nil {
			return parsed
		}
	}
	return fallback
}

func optionalTimeField(payload map[string]any, names ...string) (*time.Time, error) {
	text, ok := stringField(payload, names...)
	if !ok {
		return nil, nil
	}
	parsed, err := time.Parse(time.RFC3339, text)
	if err != nil {
		return nil, fmt.Errorf("invalid_%s", names[0])
	}
	normalized := parsed.UTC()
	return &normalized, nil
}
