package main

import (
	"context"
	"log/slog"
	"os"
	"time"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/config"
	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/health"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/logging"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/polling"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/providers"
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
	healthServer := health.NewServer(cfg.HealthAddr, pool, cfg.WorkerID, registry.Keys(), capabilities, metrics, readyErr)
	go func() {
		if err := healthServer.ListenAndServe(); err != nil {
			logger.Error("market_worker_health_server_failed", "error", err)
			stop()
		}
	}()
	logger.Info(
		"market_worker_started",
		"workerId", cfg.WorkerID,
		"queueName", cfg.QueueName,
		"mode", cfg.Mode,
		"databaseUrl", safety.RedactDatabaseURL(cfg.DatabaseURL),
		"healthAddr", cfg.HealthAddr,
	)
	if readyErr != nil {
		return readyErr
	}
	pollingService := polling.NewService(pool, capabilities, registry, cfg.MaxCandlesPerRequest, cfg.ProviderTimeout, cfg.BinancePublicRESTBaseURL, logger)
	runner := worker.NewRunner(cfg, pool, capabilities, pollingService, metrics, logger)
	runErr := runner.Run(ctx)
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := healthServer.Shutdown(shutdownCtx); err != nil {
		logger.Warn("market_worker_health_shutdown_failed", "error", err)
	}
	return runErr
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
