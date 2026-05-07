package candles

import (
	"fmt"
	"time"
)

type Timeframe struct {
	Value    string
	Seconds int64
}

func ParseTimeframe(value string) (Timeframe, error) {
	switch value {
	case "1m":
		return Timeframe{Value: value, Seconds: 60}, nil
	case "3m":
		return Timeframe{Value: value, Seconds: 180}, nil
	case "5m":
		return Timeframe{Value: value, Seconds: 300}, nil
	case "15m":
		return Timeframe{Value: value, Seconds: 900}, nil
	case "30m":
		return Timeframe{Value: value, Seconds: 1800}, nil
	case "1h":
		return Timeframe{Value: value, Seconds: 3600}, nil
	case "4h":
		return Timeframe{Value: value, Seconds: 14400}, nil
	case "1d":
		return Timeframe{Value: value, Seconds: 86400}, nil
	default:
		return Timeframe{}, fmt.Errorf("unsupported_timeframe")
	}
}

func (t Timeframe) Duration() time.Duration {
	return time.Duration(t.Seconds) * time.Second
}

func NormalizeTimestamp(value time.Time) time.Time {
	return value.UTC()
}

func TimestampAligns(value time.Time, timeframe Timeframe) bool {
	normalized := NormalizeTimestamp(value)
	if normalized.Nanosecond() != 0 {
		return false
	}
	secondsSinceDayStart := int64(normalized.Hour()*3600 + normalized.Minute()*60 + normalized.Second())
	return secondsSinceDayStart%timeframe.Seconds == 0
}
