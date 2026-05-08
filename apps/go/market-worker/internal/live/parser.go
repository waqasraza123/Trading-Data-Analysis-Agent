package live

import (
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/shopspring/decimal"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
)

func ParseBinanceMessage(raw []byte, subscription Subscription) (ParsedEvent, error) {
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return ParsedEvent{
			Type:       EventTypeError,
			ErrorMessage: "invalid_live_message_json",
			RawMessage: raw,
			Payload: map[string]any{
				"raw": string(raw),
			},
		}, err
	}
	if streamPayload, ok := payload["data"]; ok {
		if nested, nestedOk := streamPayload.(map[string]any); nestedOk {
			payload = nested
		}
	}
	providerTimestamp := timestampFromValue(payload["E"])
	eventType := eventTypeFromPayload(payload)
	switch eventType {
	case EventTypeHeartbeat:
		fallthrough
	case EventTypeReconnect:
		fallthrough
	case EventTypeSnapshot:
		return ParsedEvent{
			Type:              eventType,
			ProviderTimestamp: providerTimestamp,
			Payload:           payload,
			RawMessage:        raw,
		}, nil
	case EventTypeError:
		errorMessage := "provider_error"
		if message, ok := payload["m"]; ok {
			errorMessage = strings.TrimSpace(fmt.Sprint(message))
		} else if message, ok := payload["msg"]; ok {
			errorMessage = strings.TrimSpace(fmt.Sprint(message))
		}
		return ParsedEvent{
			Type:              eventType,
			ErrorMessage:       errorMessage,
			ProviderTimestamp:  providerTimestamp,
			Payload:           payload,
			RawMessage:        raw,
		}, nil
	case EventTypeCandlePartial, EventTypeCandleFinal:
		candle, err := parseBinanceKline(payload, subscription, providerTimestamp)
		if err != nil {
			return ParsedEvent{
				Type:       EventTypeError,
				ErrorMessage: err.Error(),
				Payload:    payload,
				RawMessage: raw,
			}, err
		}
		return ParsedEvent{
			Type:              eventType,
			ProviderTimestamp: providerTimestamp,
			Candle:            candle,
			Payload:           payload,
			RawMessage:        raw,
		}, nil
	}
	return ParsedEvent{
		Type:       EventTypeError,
		ErrorMessage: fmt.Sprintf("unsupported_live_event_type_%v", payload["e"]),
		Payload:    payload,
		RawMessage: raw,
	}, errors.New("unsupported_live_event_type")
}

func eventTypeFromPayload(payload map[string]any) EventType {
	if rawEvent, ok := payload["e"]; ok {
		switch strings.ToLower(fmt.Sprint(rawEvent)) {
		case "kline":
			return eventTypeFromKline(payload)
		case "heartbeat":
			return EventTypeHeartbeat
		case "reconnect":
			return EventTypeReconnect
		case "error":
			return EventTypeError
		case "snapshot":
			return EventTypeSnapshot
		}
	}
	return EventTypeError
}

func eventTypeFromKline(payload map[string]any) EventType {
	klinePayload, ok := payload["k"].(map[string]any)
	if !ok {
		return EventTypeError
	}
	finalValue, ok := klinePayload["x"]
	if !ok {
		return EventTypeError
	}
	isFinal, ok := asBool(finalValue)
	if !ok {
		return EventTypeError
	}
	if isFinal {
		return EventTypeCandleFinal
	}
	return EventTypeCandlePartial
}

func parseBinanceKline(payload map[string]any, subscription Subscription, providerTimestamp *time.Time) (*candles.Candle, error) {
	rawKline, ok := payload["k"].(map[string]any)
	if !ok {
		return nil, errors.New("missing_kline_payload")
	}
	openMs, err := asInt64(rawKline["t"])
	if err != nil {
		return nil, errors.New("missing_open_time")
	}
	open, err := asDecimal(rawKline["o"])
	if err != nil {
		return nil, errors.New("invalid_open")
	}
	high, err := asDecimal(rawKline["h"])
	if err != nil {
		return nil, errors.New("invalid_high")
	}
	low, err := asDecimal(rawKline["l"])
	if err != nil {
		return nil, errors.New("invalid_low")
	}
	close, err := asDecimal(rawKline["c"])
	if err != nil {
		return nil, errors.New("invalid_close")
	}
	volume, _ := asDecimal(rawKline["v"])
	finalFlag, ok := asBool(rawKline["x"])
	if !ok {
		return nil, errors.New("invalid_final_flag")
	}
	openTime := time.UnixMilli(openMs).UTC()
	providerTimestampValue := providerTimestamp
	if providerTimestampValue == nil {
		providerTimestampValue = &openTime
	}
	return &candles.Candle{
		WorkspaceID:      subscription.WorkspaceID,
		SymbolID:         subscription.SymbolID,
		SourceID:         subscription.SourceID,
		Timeframe:        subscription.Timeframe,
		Timestamp:        openTime,
		Open:             open,
		High:             high,
		Low:              low,
		Close:            close,
		Volume:           &volume,
		IsFinal:          finalFlag,
		OriginType:       "live_feed",
		OriginReferenceID: &subscription.ID,
		ProviderMetadata: map[string]any{
			"provider":         "binance",
			"providerTimestamp": timestampToRFC3339(providerTimestampValue),
			"subscriptionId":    subscription.ID.String(),
		},
		RawItem: rawKline,
	}, nil
}

func timestampToRFC3339(timestamp *time.Time) string {
	if timestamp == nil {
		return ""
	}
	return timestamp.UTC().Format(time.RFC3339Nano)
}

func asBool(value any) (bool, bool) {
	switch typed := value.(type) {
	case bool:
		return typed, true
	case string:
		parsed, err := strconv.ParseBool(typed)
		return parsed, err == nil
	case float64:
		return typed == 1, true
	case int:
		return typed == 1, true
	default:
		return false, false
	}
}

func asInt64(value any) (int64, error) {
	switch typed := value.(type) {
	case float64:
		return int64(typed), nil
	case int:
		return int64(typed), nil
	case int64:
		return typed, nil
	case string:
		parsed, err := strconv.ParseInt(typed, 10, 64)
		if err != nil {
			return 0, err
		}
		return parsed, nil
	default:
		return 0, errors.New("invalid_number")
	}
}

func asDecimal(value any) (decimal.Decimal, error) {
	switch typed := value.(type) {
	case string:
		return decimal.NewFromString(typed)
	case float64:
		return decimal.NewFromString(strconv.FormatFloat(typed, 'f', -1, 64))
	case int:
		return decimal.NewFromString(strconv.Itoa(typed))
	case int64:
		return decimal.NewFromString(strconv.FormatInt(typed, 10))
	case nil:
		return decimal.Zero, nil
	default:
		return decimal.Zero, errors.New("invalid_decimal")
	}
}

func timestampFromValue(value any) *time.Time {
	raw, err := asInt64(value)
	if err != nil {
		return nil
	}
	timestamp := time.UnixMilli(raw).UTC()
	return &timestamp
}

func parseProviderSymbol(config map[string]any) string {
	keys := []string{"providerSymbol", "provider_symbol", "symbol"}
	for _, key := range keys {
		if value, ok := config[key]; ok {
			if text := strings.TrimSpace(fmt.Sprint(value)); text != "" && text != "<nil>" {
				return text
			}
		}
	}
	if len(config) > 0 {
		return ""
	}
	return ""
}

func normalizeProviderSymbol(subscription Subscription, override string, symbol string) (string, error) {
	if strings.TrimSpace(override) != "" {
		return override, nil
	}
	if strings.TrimSpace(symbol) != "" {
		return strings.ToLower(strings.TrimSpace(symbol)), nil
	}
	return "", fmt.Errorf("missing_provider_symbol")
}

func parseProviderSymbolOrDefault(config map[string]any, subscriptionSymbol string) (string, error) {
	return normalizeProviderSymbol(Subscription{}, parseProviderSymbol(config), subscriptionSymbol)
}

func uniqueID(value any) uuid.UUID {
	if parsed, ok := value.(string); ok {
		if parsedID, err := uuid.Parse(parsed); err == nil {
			return parsedID
		}
	}
	return uuid.Nil
}
