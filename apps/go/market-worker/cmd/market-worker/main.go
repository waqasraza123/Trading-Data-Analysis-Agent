package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"time"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/config"
	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/health"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/logging"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/polling"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/providers"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/live"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/safety"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/worker"
)

func main() {
	if err := run(); err != nil {
		slog.Error("market_worker_exit", "error", err)
		os.Exit(1)
	}
}

func run() error {
	cfg, err := config.Load()
	if err != nil {
		return err
	}
	logger := logging.New(cfg.LogLevel)
	slog.SetDefault(logger)
	ctx, stop := worker.SignalContext(context.Background())
	defer stop()
	pool, err := workerdb.NewPool(ctx, cfg.DatabaseURL)
	if err != nil {
		return err
	}
	defer pool.Close()
	capabilities, err := workerdb.DetectCapabilities(ctx, pool)
	if err != nil {
		return err
	}
	readyErr := capabilities.Validate(cfg.Mode)
	registry := providerRegistry(cfg)
	metrics := health.NewMetrics()
	if cfg.RunMode == "inspect" {
		return writeInspection(cfg, capabilities, registry.Keys(), readyErr)
	}
	logger.Info(
		"market_worker_started",
		"workerId", cfg.WorkerID,
		"queueName", cfg.QueueName,
		"mode", cfg.Mode,
		"runMode", cfg.RunMode,
		"maxConcurrency", cfg.MaxConcurrency,
		"providerMaxConcurrency", cfg.ProviderMaxConcurrency,
		"providerMinIntervalMs", cfg.ProviderMinInterval.Milliseconds(),
		"providerFailureThreshold", cfg.ProviderFailureThreshold,
		"providerCooldownSeconds", int(cfg.ProviderCooldown.Seconds()),
		"jobTimeoutSeconds", int(cfg.JobTimeout.Seconds()),
		"dbWriteTimeoutSeconds", int(cfg.DBWriteTimeout.Seconds()),
		"providerRequestStaleSeconds", int(cfg.ProviderRequestStaleAfter.Seconds()),
		"databaseUrl", safety.RedactDatabaseURL(cfg.DatabaseURL),
		"healthAddr", cfg.HealthAddr,
	)
	if readyErr != nil {
		return readyErr
	}
	pollingService := polling.NewService(
		pool,
		capabilities,
		registry,
		cfg.MaxCandlesPerRequest,
		cfg.ProviderTimeout,
		cfg.BinancePublicRESTBaseURL,
		cfg.ProviderMaxConcurrency,
		cfg.ProviderMinInterval,
		cfg.ProviderFailureThreshold,
		cfg.ProviderCooldown,
		metrics,
		logger,
	)
	liveService := live.NewService(pool, capabilities, cfg, logger, metrics)
	runner := worker.NewRunner(cfg, pool, capabilities, pollingService, liveService, metrics, logger)
	if cfg.RunMode == "once" {
		claimed, err := runner.RunOnce(ctx)
		logger.Info("market_worker_once_completed", "claimedCount", claimed)
		return err
	}
	healthServer := health.NewServer(cfg.HealthAddr, pool, cfg.WorkerID, cfg.Mode, registry.Keys(), capabilities, metrics, readyErr)
	go func() {
		if err := healthServer.ListenAndServe(); err != nil {
			logger.Error("market_worker_health_server_failed", "error", err)
			stop()
		}
	}()
	runErr := runner.Run(ctx)
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := healthServer.Shutdown(shutdownCtx); err != nil {
		logger.Warn("market_worker_health_shutdown_failed", "error", err)
	}
	return runErr
}

func writeInspection(cfg config.Config, capabilities workerdb.Capabilities, providers []string, readyErr error) error {
	payload := map[string]any{
		"workerId":                 cfg.WorkerID,
		"queueName":                cfg.QueueName,
		"mode":                     cfg.Mode,
		"runMode":                  cfg.RunMode,
		"batchSize":                cfg.BatchSize,
		"maxConcurrency":           cfg.MaxConcurrency,
		"providerMaxConcurrency":   cfg.ProviderMaxConcurrency,
		"providerMinIntervalMs":    cfg.ProviderMinInterval.Milliseconds(),
		"providerFailureThreshold": cfg.ProviderFailureThreshold,
		"providerCooldownSeconds":     int(cfg.ProviderCooldown.Seconds()),
		"jobTimeoutSeconds":           int(cfg.JobTimeout.Seconds()),
		"dbWriteTimeoutSeconds":       int(cfg.DBWriteTimeout.Seconds()),
		"providerRequestStaleSeconds": int(cfg.ProviderRequestStaleAfter.Seconds()),
		"enableLiveStream":            cfg.EnableLiveStream,
		"liveStreamEnabled":           cfg.Mode == "jobs" && cfg.EnableLiveStream && cfg.EnableLiveBinance,
		"liveStreamClaimIntervalSeconds":  int(cfg.LiveStreamClaimInterval.Seconds()),
		"liveStreamClaimBatchSize":       cfg.LiveStreamClaimBatchSize,
		"liveStreamLeaseSeconds":         int(cfg.LiveStreamLeaseDuration.Seconds()),
		"liveStreamReconnectSeconds":      int(cfg.LiveStreamReconnectDelay.Seconds()),
		"liveStreamMaxReconnectSeconds":  int(cfg.LiveStreamMaxReconnectDelay.Seconds()),
		"liveStreamMaxReconnectAttempts":  cfg.LiveStreamMaxReconnectAttempts,
		"liveStreamReconnectJitterPercent": cfg.LiveStreamReconnectJitterPercent,
		"liveStreamReadTimeoutSeconds":    int(cfg.LiveStreamReadTimeout.Seconds()),
		"liveStreamMessageBuffer":         cfg.LiveStreamMessageBuffer,
		"liveStreamGapRecoveryEnabled":    cfg.LiveStreamGapRecovery,
		"liveStreamStaleAfterSeconds":     int(cfg.LiveStreamStaleAfter.Seconds()),
		"liveStreamGapAfterSeconds":       int(cfg.LiveStreamGapAfter.Seconds()),
		"liveStreamGapRequestLimit":       cfg.LiveStreamGapRequestLimit,
		"providers":                   providers,
		"dbCapabilities":              capabilities,
		"requiredColumnProblems":      capabilities.RequiredColumnProblems(cfg.Mode),
		"optionalColumnProblems":      capabilities.OptionalColumnProblems(),
		"ready":                       readyErr == nil,
	}
	if readyErr != nil {
		payload["error"] = readyErr.Error()
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	return encoder.Encode(payload)
}

func providerRegistry(cfg config.Config) *providers.Registry {
	registered := []providers.Provider{providers.GenericOHLCHTTPProvider{}}
	if cfg.EnableMockProvider {
		registered = append(registered, providers.MockProvider{})
	}
	if cfg.EnableBinancePublic {
		registered = append(registered, providers.NewBinancePublicRESTProvider())
	}
	return providers.NewRegistry(registered...)
}
