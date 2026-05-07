package candles

import "time"

type Conflict struct {
	Type     string
	Resolution string
	Existing map[string]any
	Incoming map[string]any
	Candle   Candle
}

func SerializeCandle(c Candle) map[string]any {
	payload := map[string]any{
		"workspaceId": c.WorkspaceID.String(),
		"symbolId":    c.SymbolID.String(),
		"sourceId":    c.SourceID.String(),
		"timeframe":   c.Timeframe,
		"timestamp":   c.Timestamp.Format(time.RFC3339),
		"open":        c.Open.String(),
		"high":        c.High.String(),
		"low":         c.Low.String(),
		"close":       c.Close.String(),
		"isFinal":     c.IsFinal,
	}
	if c.Volume != nil {
		payload["volume"] = c.Volume.String()
	} else {
		payload["volume"] = nil
	}
	return payload
}
