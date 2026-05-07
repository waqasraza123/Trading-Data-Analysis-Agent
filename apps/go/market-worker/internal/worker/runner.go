package worker

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/config"
	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/health"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/jobs"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/polling"
)

type Runner struct {
	config       config.Config
	pool         *pgxpool.Pool
	capabilities workerdb.Capabilities
	repository   *jobs.Repository
	polling      *polling.Service
	heartbeat    *jobs.Heartbeat
	metrics      *health.Metrics
	logger       *slog.Logger
}

func NewRunner(cfg config.Config, pool *pgxpool.Pool, capabilities workerdb.Capabilities, pollingService *polling.Service, metrics *health.Metrics, logger *slog.Logger) *Runner {
	return &Runner{
		config:       cfg,
		pool:         pool,
		capabilities: capabilities,
		repository:   jobs.NewRepository(pool, capabilities),
		polling:      pollingService,
		heartbeat:    jobs.NewHeartbeat(pool, capabilities, cfg.WorkerID),
		metrics:      metrics,
		logger:       logger,
	}
}

func (r *Runner) Run(ctx context.Context) error {
	_ = r.heartbeat.Starting(ctx, map[string]any{"queueName": r.config.QueueName})
	defer func() {
		_ = r.heartbeat.Stopped(context.Background(), map[string]any{"queueName": r.config.QueueName})
	}()
	ticker := time.NewTicker(r.config.PollInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		default:
		}
		claimed, err := r.pollOnce(ctx)
		if err != nil {
			r.logger.Error("market_worker_poll_failed", "error", err)
			_ = r.heartbeat.Failed(ctx, map[string]any{"error": err.Error()})
		} else {
			_ = r.heartbeat.Running(ctx, map[string]any{"claimedCount": claimed, "queueName": r.config.QueueName})
		}
		if claimed > 0 {
			continue
		}
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
		}
	}
}

func (r *Runner) pollOnce(ctx context.Context) (int, error) {
	if r.config.Mode == "provider_polling_requests" || !r.capabilities.HasTable("job_queue_items") {
		requests, err := r.repository.ClaimProviderPollingRequests(ctx, r.config.WorkerID, r.config.BatchSize)
		if err != nil {
			return 0, err
		}
		r.metrics.RecordClaimed(len(requests))
		return len(requests), r.processRequests(ctx, requests)
	}
	jobs, err := r.repository.ClaimJobQueueItems(ctx, r.config.QueueName, r.config.WorkerID, r.config.BatchSize, r.config.JobLockDuration)
	if err != nil {
		return 0, err
	}
	if len(jobs) == 0 && r.capabilities.HasTable("provider_polling_requests") {
		requests, err := r.repository.ClaimProviderPollingRequests(ctx, r.config.WorkerID, r.config.BatchSize)
		if err != nil {
			return 0, err
		}
		r.metrics.RecordClaimed(len(requests))
		return len(requests), r.processRequests(ctx, requests)
	}
	r.metrics.RecordClaimed(len(jobs))
	return len(jobs), r.processJobs(ctx, jobs)
}

func (r *Runner) processJobs(ctx context.Context, items []jobs.Job) error {
	var wg sync.WaitGroup
	errs := make(chan error, len(items))
	sem := make(chan struct{}, min(len(items), max(1, r.config.BatchSize)))
	for _, item := range items {
		wg.Add(1)
		go func(job jobs.Job) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			if err := r.handleJob(ctx, job); err != nil {
				errs <- err
			}
		}(item)
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			r.logger.Warn("market_worker_job_failed", "error", err)
		}
	}
	return nil
}

func (r *Runner) processRequests(ctx context.Context, requests []jobs.PollingRequest) error {
	var wg sync.WaitGroup
	errs := make(chan error, len(requests))
	sem := make(chan struct{}, min(len(requests), max(1, r.config.BatchSize)))
	for _, request := range requests {
		wg.Add(1)
		go func(item jobs.PollingRequest) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			if err := r.handleDirectRequest(ctx, item); err != nil {
				errs <- err
			}
		}(request)
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			r.logger.Warn("market_worker_request_failed", "error", err)
		}
	}
	return nil
}
