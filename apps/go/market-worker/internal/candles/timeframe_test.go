package candles

import (
	"testing"
	"time"
)

func TestParseTimeframeAndAlignment(t *testing.T) {
	timeframe, err := ParseTimeframe("15m")
	if err != nil {
		t.Fatalf("expected timeframe: %v", err)
	}
	if timeframe.Seconds != 900 {
		t.Fatalf("expected 900 seconds, got %d", timeframe.Seconds)
	}
	if !TimestampAligns(time.Date(2026, 5, 6, 10, 15, 0, 0, time.UTC), timeframe) {
		t.Fatal("expected aligned timestamp")
	}
	if TimestampAligns(time.Date(2026, 5, 6, 10, 16, 0, 0, time.UTC), timeframe) {
		t.Fatal("expected misaligned timestamp")
	}
}

func TestUnsupportedTimeframe(t *testing.T) {
	if _, err := ParseTimeframe("2m"); err == nil {
		t.Fatal("expected unsupported timeframe error")
	}
}
