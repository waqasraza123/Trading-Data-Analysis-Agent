package candles

import (
	"time"

	"github.com/google/uuid"
	"github.com/shopspring/decimal"
)

type ProviderCandleInput struct {
	Timestamp        time.Time
	Open             string
	High             string
	Low              string
	Close            string
	Volume           *string
	IsFinal          bool
	ProviderMetadata map[string]any
	RawItem          map[string]any
}

func NormalizeProviderCandle(input ProviderCandleInput, workspaceID uuid.UUID, sourceID uuid.UUID, symbolID uuid.UUID, timeframe string, originReferenceID *uuid.UUID) (Candle, error) {
	openValue, err := ParseDecimal(input.Open, "open")
	if err != nil {
		return Candle{}, err
	}
	highValue, err := ParseDecimal(input.High, "high")
	if err != nil {
		return Candle{}, err
	}
	lowValue, err := ParseDecimal(input.Low, "low")
	if err != nil {
		return Candle{}, err
	}
	closeValue, err := ParseDecimal(input.Close, "close")
	if err != nil {
		return Candle{}, err
	}
	var volumeValue *decimal.Decimal
	if input.Volume != nil {
		parsed, err := ParseDecimal(*input.Volume, "volume")
		if err != nil {
			return Candle{}, err
		}
		volumeValue = &parsed
	}
	return Candle{
		WorkspaceID:       workspaceID,
		SourceID:          sourceID,
		SymbolID:          symbolID,
		Timeframe:         timeframe,
		Timestamp:         NormalizeTimestamp(input.Timestamp),
		Open:              openValue,
		High:              highValue,
		Low:               lowValue,
		Close:             closeValue,
		Volume:            volumeValue,
		IsFinal:           input.IsFinal,
		OriginType:        "api_polling",
		OriginReferenceID: originReferenceID,
		ProviderMetadata:  input.ProviderMetadata,
		RawItem:           input.RawItem,
	}, nil
}
