package providers

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
)

type BinancePublicRESTProvider struct {
	client *http.Client
}

func NewBinancePublicRESTProvider() *BinancePublicRESTProvider {
	return &BinancePublicRESTProvider{client: &http.Client{}}
}

func (p *BinancePublicRESTProvider) Key() string {
	return "binance_public_rest"
}

func (p *BinancePublicRESTProvider) FetchCandles(ctx context.Context, request FetchCandlesRequest) (FetchCandlesResult, error) {
	if _, err := candles.ParseTimeframe(request.Timeframe); err != nil {
		return FetchCandlesResult{}, NewProviderError("unsupported_timeframe", "Unsupported timeframe")
	}
	endpoint, err := buildBinanceURL(request)
	if err != nil {
		return FetchCandlesResult{}, err
	}
	timeoutCtx, cancel := context.WithTimeout(ctx, request.Timeout)
	defer cancel()
	httpRequest, err := http.NewRequestWithContext(timeoutCtx, http.MethodGet, endpoint, nil)
	if err != nil {
		return FetchCandlesResult{}, err
	}
	httpRequest.Header.Set("User-Agent", "trading-intelligence-go-market-worker/0.1")
	response, err := p.client.Do(httpRequest)
	if err != nil {
		return FetchCandlesResult{}, NewProviderError("binance_network_error", "Binance request failed before a response was received")
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return FetchCandlesResult{}, NewProviderError("binance_http_error", fmt.Sprintf("Binance request failed with HTTP status %d", response.StatusCode))
	}
	var payload []any
	if err := json.NewDecoder(response.Body).Decode(&payload); err != nil {
		return FetchCandlesResult{}, NewProviderError("invalid_binance_json", "Binance response was not valid JSON")
	}
	nowMs := time.Now().UTC().UnixMilli()
	result := FetchCandlesResult{
		Candles: make([]candles.ProviderCandleInput, 0, len(payload)),
		ProviderMetadata: map[string]any{
			"provider":      p.Key(),
			"requested_url": endpoint,
			"responseCount": len(payload),
		},
	}
	for index, item := range payload {
		candle, err := parseBinanceKline(item, request, nowMs)
		if err != nil {
			result.Errors = append(result.Errors, ProviderMessage{
				Code:    "invalid_binance_kline",
				Message: fmt.Sprintf("Binance kline at position %d could not be parsed", index+1),
				RawItem: map[string]any{
					"item":  fmt.Sprint(item),
					"error": err.Error(),
				},
			})
			continue
		}
		result.Candles = append(result.Candles, candle)
	}
	return result, nil
}

func buildBinanceURL(request FetchCandlesRequest) (string, error) {
	baseURL := strings.TrimRight(request.BaseURL, "/")
	if baseURL == "" {
		baseURL = "https://api.binance.com"
	}
	values := url.Values{}
	values.Set("symbol", strings.ToUpper(request.ProviderSymbol))
	values.Set("interval", request.Timeframe)
	values.Set("limit", strconv.Itoa(request.Limit))
	if request.StartTime != nil {
		values.Set("startTime", strconv.FormatInt(request.StartTime.UTC().UnixMilli(), 10))
	}
	if request.EndTime != nil {
		values.Set("endTime", strconv.FormatInt(request.EndTime.UTC().UnixMilli(), 10))
	}
	return baseURL + "/api/v3/klines?" + values.Encode(), nil
}

func parseBinanceKline(item any, request FetchCandlesRequest, nowMs int64) (candles.ProviderCandleInput, error) {
	values, ok := item.([]any)
	if !ok || len(values) < 7 {
		return candles.ProviderCandleInput{}, fmt.Errorf("kline item must be an array")
	}
	openTime, err := numericMilliseconds(values[0])
	if err != nil {
		return candles.ProviderCandleInput{}, err
	}
	closeTime, err := numericMilliseconds(values[6])
	if err != nil {
		return candles.ProviderCandleInput{}, err
	}
	volume := stringValue(values[5])
	return candles.ProviderCandleInput{
		Timestamp: time.UnixMilli(openTime).UTC(),
		Open:      stringValue(values[1]),
		High:      stringValue(values[2]),
		Low:       stringValue(values[3]),
		Close:     stringValue(values[4]),
		Volume:    &volume,
		IsFinal:   closeTime <= nowMs,
		ProviderMetadata: map[string]any{
			"provider":       "binance_public_rest",
			"providerSymbol": strings.ToUpper(request.ProviderSymbol),
		},
		RawItem: map[string]any{
			"openTime":  openTime,
			"open":      stringValue(values[1]),
			"high":      stringValue(values[2]),
			"low":       stringValue(values[3]),
			"close":     stringValue(values[4]),
			"volume":    volume,
			"closeTime": closeTime,
		},
	}, nil
}

func numericMilliseconds(value any) (int64, error) {
	switch typed := value.(type) {
	case float64:
		return int64(typed), nil
	case string:
		return strconv.ParseInt(typed, 10, 64)
	default:
		return 0, fmt.Errorf("timestamp must be numeric")
	}
}

func stringValue(value any) string {
	switch typed := value.(type) {
	case string:
		return typed
	case float64:
		return strconv.FormatFloat(typed, 'f', -1, 64)
	default:
		return fmt.Sprint(typed)
	}
}
