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
	JobLockDuration          time.Duration
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
		JobLockDuration:          time.Duration(envInt("MARKET_WORKER_JOB_LOCK_SECONDS", 120)) * time.Second,
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
