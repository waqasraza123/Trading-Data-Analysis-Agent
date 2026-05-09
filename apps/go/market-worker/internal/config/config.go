package config

import (
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/google/uuid"
)

type Config struct {
	DatabaseURL              string
	WorkerID                 string
	QueueName                string
	PollInterval             time.Duration
	BatchSize                int
	MaxConcurrency           int
	ProviderMaxConcurrency   int
	ProviderMinInterval      time.Duration
	ProviderFailureThreshold int
	ProviderCooldown         time.Duration
	JobLockDuration          time.Duration
	JobTimeout               time.Duration
	DBWriteTimeout            time.Duration
	ProviderRequestStaleAfter time.Duration
	ProviderTimeout          time.Duration
	MaxCandlesPerRequest     int
	HealthAddr               string
	LogLevel                 string
	Mode                     string
	RunMode                  string
	RetryBackoff             time.Duration
	BinancePublicRESTBaseURL string
	EnableBinancePublic      bool
	EnableMockProvider       bool
	EnableLiveStream         bool
	LiveStreamClaimInterval  time.Duration
	LiveStreamClaimBatchSize int
	LiveStreamLeaseDuration  time.Duration
	LiveStreamReconnectDelay time.Duration
	LiveStreamMaxReconnectDelay time.Duration
	LiveStreamReadTimeout    time.Duration
	LiveStreamMessageBuffer  int
	LiveStreamStaleAfter     time.Duration
	LiveStreamGapAfter       time.Duration
	LiveStreamGapRecovery    bool
	LiveStreamGapRequestLimit int
	BinanceLiveWebSocketBaseURL string
	EnableLiveBinance        bool
}

func Load() (Config, error) {
	batchSize := envInt("MARKET_WORKER_BATCH_SIZE", 10)
	cfg := Config{
		DatabaseURL:              strings.TrimSpace(os.Getenv("DATABASE_URL")),
		WorkerID:                 envString("MARKET_WORKER_ID", "market-worker-"+uuid.NewString()),
		QueueName:                envString("MARKET_WORKER_QUEUE_NAME", "market-data"),
		PollInterval:             time.Duration(envInt("MARKET_WORKER_POLL_SECONDS", 5)) * time.Second,
		BatchSize:                batchSize,
		MaxConcurrency:           envInt("MARKET_WORKER_MAX_CONCURRENCY", batchSize),
		ProviderMaxConcurrency:   envInt("MARKET_WORKER_PROVIDER_MAX_CONCURRENCY", batchSize),
		ProviderMinInterval:      time.Duration(envInt("MARKET_WORKER_PROVIDER_MIN_INTERVAL_MS", 0)) * time.Millisecond,
		ProviderFailureThreshold: envInt("MARKET_WORKER_PROVIDER_FAILURE_THRESHOLD", 5),
		ProviderCooldown:         time.Duration(envInt("MARKET_WORKER_PROVIDER_COOLDOWN_SECONDS", 60)) * time.Second,
		JobLockDuration:          time.Duration(envInt("MARKET_WORKER_JOB_LOCK_SECONDS", 120)) * time.Second,
		JobTimeout:               time.Duration(envInt("MARKET_WORKER_JOB_TIMEOUT_SECONDS", 300)) * time.Second,
		DBWriteTimeout:            time.Duration(envInt("MARKET_WORKER_DB_WRITE_TIMEOUT_SECONDS", 15)) * time.Second,
		ProviderRequestStaleAfter: time.Duration(envInt("MARKET_WORKER_PROVIDER_REQUEST_STALE_SECONDS", envInt("MARKET_WORKER_JOB_TIMEOUT_SECONDS", 300))) * time.Second,
		ProviderTimeout:          time.Duration(envInt("MARKET_WORKER_PROVIDER_TIMEOUT_SECONDS", 20)) * time.Second,
		MaxCandlesPerRequest:     envInt("MARKET_WORKER_MAX_CANDLES_PER_REQUEST", 1000),
		HealthAddr:               envString("MARKET_WORKER_HEALTH_ADDR", ":8091"),
		LogLevel:                 strings.ToLower(envString("MARKET_WORKER_LOG_LEVEL", "info")),
		Mode:                     strings.ToLower(envString("MARKET_WORKER_MODE", "jobs")),
		RunMode:                  strings.ToLower(envString("MARKET_WORKER_RUN_MODE", "serve")),
		RetryBackoff:             time.Duration(envInt("MARKET_WORKER_RETRY_BACKOFF_SECONDS", 60)) * time.Second,
		BinancePublicRESTBaseURL: envString("BINANCE_PUBLIC_REST_BASE_URL", "https://api.binance.com"),
		EnableBinancePublic:      envBool("MARKET_WORKER_ENABLE_BINANCE_PUBLIC", true),
		EnableMockProvider:       envBool("MARKET_WORKER_ENABLE_MOCK_PROVIDER", true),
		EnableLiveStream:         envBool("MARKET_WORKER_ENABLE_LIVE_STREAM", true),
		LiveStreamClaimInterval:  time.Duration(envInt("MARKET_WORKER_LIVE_STREAM_CLAIM_INTERVAL_SECONDS", 5)) * time.Second,
		LiveStreamClaimBatchSize: envInt("MARKET_WORKER_LIVE_STREAM_CLAIM_BATCH_SIZE", batchSize),
		LiveStreamLeaseDuration:  time.Duration(envInt("MARKET_WORKER_LIVE_STREAM_LEASE_SECONDS", 90)) * time.Second,
		LiveStreamReconnectDelay: time.Duration(envInt("MARKET_WORKER_LIVE_STREAM_RECONNECT_SECONDS", 5)) * time.Second,
		LiveStreamMaxReconnectDelay: time.Duration(envInt("MARKET_WORKER_LIVE_STREAM_MAX_RECONNECT_SECONDS", 60)) * time.Second,
		LiveStreamReadTimeout:    time.Duration(envInt("MARKET_WORKER_LIVE_STREAM_READ_TIMEOUT_SECONDS", 30)) * time.Second,
		LiveStreamMessageBuffer:  envInt("MARKET_WORKER_LIVE_STREAM_MESSAGE_BUFFER", 64),
		LiveStreamStaleAfter:     time.Duration(envInt("MARKET_WORKER_LIVE_STREAM_MESSAGE_STALE_SECONDS", 180)) * time.Second,
		LiveStreamGapAfter:       time.Duration(envInt("MARKET_WORKER_LIVE_STREAM_FINAL_STALE_SECONDS", 300)) * time.Second,
		LiveStreamGapRecovery:    envBool("MARKET_WORKER_LIVE_STREAM_GAP_RECOVERY", true),
		LiveStreamGapRequestLimit: envInt("MARKET_WORKER_LIVE_STREAM_GAP_REQUEST_LIMIT", 1000),
		BinanceLiveWebSocketBaseURL: envString("MARKET_WORKER_BINANCE_LIVE_WS_BASE_URL", "wss://stream.binance.com:9443/ws"),
		EnableLiveBinance:        envBool("MARKET_WORKER_ENABLE_LIVE_BINANCE", true),
	}
	if cfg.DatabaseURL == "" {
		return Config{}, errors.New("DATABASE_URL is required")
	}
	if cfg.BatchSize <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_BATCH_SIZE must be positive")
	}
	if cfg.MaxConcurrency <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_MAX_CONCURRENCY must be positive")
	}
	if cfg.ProviderMaxConcurrency <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_PROVIDER_MAX_CONCURRENCY must be positive")
	}
	if cfg.ProviderMinInterval < 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_PROVIDER_MIN_INTERVAL_MS must be zero or positive")
	}
	if cfg.ProviderFailureThreshold < 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_PROVIDER_FAILURE_THRESHOLD must be zero or positive")
	}
	if cfg.ProviderCooldown < 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_PROVIDER_COOLDOWN_SECONDS must be zero or positive")
	}
	if cfg.JobTimeout < 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_JOB_TIMEOUT_SECONDS must be zero or positive")
	}
	if cfg.DBWriteTimeout <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_DB_WRITE_TIMEOUT_SECONDS must be positive")
	}
	if cfg.ProviderRequestStaleAfter < 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_PROVIDER_REQUEST_STALE_SECONDS must be zero or positive")
	}
	if cfg.LiveStreamClaimInterval <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_CLAIM_INTERVAL_SECONDS must be positive")
	}
	if cfg.LiveStreamClaimBatchSize <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_CLAIM_BATCH_SIZE must be positive")
	}
	if cfg.LiveStreamLeaseDuration <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_LEASE_SECONDS must be positive")
	}
	if cfg.LiveStreamReconnectDelay <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_RECONNECT_SECONDS must be positive")
	}
	if cfg.LiveStreamMaxReconnectDelay <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_MAX_RECONNECT_SECONDS must be positive")
	}
	if cfg.LiveStreamMaxReconnectDelay < cfg.LiveStreamReconnectDelay {
		cfg.LiveStreamMaxReconnectDelay = cfg.LiveStreamReconnectDelay
	}
	if cfg.LiveStreamReadTimeout <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_READ_TIMEOUT_SECONDS must be positive")
	}
	if cfg.LiveStreamMessageBuffer <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_MESSAGE_BUFFER must be positive")
	}
	if cfg.LiveStreamStaleAfter < 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_MESSAGE_STALE_SECONDS must be zero or positive")
	}
	if cfg.LiveStreamGapAfter < 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_FINAL_STALE_SECONDS must be zero or positive")
	}
	if cfg.LiveStreamGapRequestLimit <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_LIVE_STREAM_GAP_REQUEST_LIMIT must be positive")
	}
	if cfg.MaxCandlesPerRequest <= 0 {
		return Config{}, fmt.Errorf("MARKET_WORKER_MAX_CANDLES_PER_REQUEST must be positive")
	}
	if cfg.Mode != "jobs" && cfg.Mode != "provider_polling_requests" {
		return Config{}, fmt.Errorf("MARKET_WORKER_MODE must be jobs or provider_polling_requests")
	}
	if cfg.RunMode != "serve" && cfg.RunMode != "once" && cfg.RunMode != "inspect" {
		return Config{}, fmt.Errorf("MARKET_WORKER_RUN_MODE must be serve, once, or inspect")
	}
	return cfg, nil
}

func envString(key string, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}

func envInt(key string, fallback int) int {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func envBool(key string, fallback bool) bool {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return fallback
	}
	return parsed
}
