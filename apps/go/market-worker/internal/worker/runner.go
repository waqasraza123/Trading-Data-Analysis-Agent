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

func (r *Runner) RunOnce(ctx context.Context) (int, error) {
	_ = r.heartbeat.Starting(ctx, map[string]any{"queueName": r.config.QueueName, "runMode": "once"})
	defer func() {
		_ = r.heartbeat.Stopped(context.Background(), map[string]any{"queueName": r.config.QueueName, "runMode": "once"})
	}()
	claimed, err := r.pollOnce(ctx)
	if err != nil {
		_ = r.heartbeat.Failed(ctx, map[string]any{"error": err.Error(), "runMode": "once"})
		return claimed, err
	}
	_ = r.heartbeat.Running(ctx, map[string]any{"claimedCount": claimed, "queueName": r.config.QueueName, "runMode": "once"})
	return claimed, nil
}

func (r *Runner) pollOnce(ctx context.Context) (int, error) {
	if r.config.Mode == "provider_polling_requests" || !r.capabilities.HasTable("job_queue_items") {
		requests, err := r.repository.ClaimProviderPollingRequests(ctx, r.config.WorkerID, r.config.BatchSize, r.config.ProviderRequestStaleAfter)
		if err != nil {
			return 0, err
		}
		r.metrics.RecordClaimed(len(requests))
		r.metrics.RecordProviderRequestsReclaimed(reclaimedRequestCount(requests))
		return len(requests), r.processRequests(ctx, requests)
	}
	jobs, err := r.repository.ClaimJobQueueItems(ctx, r.config.QueueName, r.config.WorkerID, r.config.BatchSize, r.config.JobLockDuration)
	if err != nil {
		return 0, err
	}
	if len(jobs) == 0 && r.capabilities.HasTable("provider_polling_requests") {
		requests, err := r.repository.ClaimProviderPollingRequests(ctx, r.config.WorkerID, r.config.BatchSize, r.config.ProviderRequestStaleAfter)
		if err != nil {
			return 0, err
		}
		r.metrics.RecordClaimed(len(requests))
		r.metrics.RecordProviderRequestsReclaimed(reclaimedRequestCount(requests))
		return len(requests), r.processRequests(ctx, requests)
	}
	r.metrics.RecordClaimed(len(jobs))
	return len(jobs), r.processJobs(ctx, jobs)
}

func (r *Runner) processJobs(ctx context.Context, items []jobs.Job) error {
	var wg sync.WaitGroup
	errs := make(chan error, len(items))
	sem := make(chan struct{}, r.concurrencyLimit(len(items)))
	for _, item := range items {
		wg.Add(1)
		go func(job jobs.Job) {
			defer wg.Done()
			if !acquire(ctx, sem) {
				return
			}
			defer release(sem)
			itemCtx, cancel := r.itemContext(ctx)
			defer cancel()
			if err := r.handleJobWithLease(itemCtx, job); err != nil {
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
	sem := make(chan struct{}, r.concurrencyLimit(len(requests)))
	for _, request := range requests {
		wg.Add(1)
		go func(item jobs.PollingRequest) {
			defer wg.Done()
			if !acquire(ctx, sem) {
				return
			}
			defer release(sem)
			itemCtx, cancel := r.itemContext(ctx)
			defer cancel()
			if err := r.handleDirectRequest(itemCtx, item); err != nil {
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

func reclaimedRequestCount(requests []jobs.PollingRequest) int {
	count := 0
	for _, request := range requests {
		if request.Reclaimed {
			count++
		}
	}
	return count
}

func (r *Runner) handleJobWithLease(ctx context.Context, job jobs.Job) error {
	leaseCtx, cancel := context.WithCancel(ctx)
	done := make(chan struct{})
	go func() {
		defer close(done)
		r.renewJobLock(leaseCtx, job)
	}()
	err := r.handleJob(ctx, job)
	cancel()
	<-done
	return err
}

func (r *Runner) renewJobLock(ctx context.Context, job jobs.Job) {
	interval := r.config.JobLockDuration / 3
	if interval < time.Second {
		interval = time.Second
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			renewCtx, cancel := context.WithTimeout(ctx, renewalTimeout(interval))
			renewed, err := r.repository.RenewJobLock(renewCtx, job, r.config.WorkerID, r.config.JobLockDuration)
			cancel()
			if err != nil {
				r.metrics.RecordJobLockRenewal(false)
				r.logger.Warn("market_worker_job_lock_renewal_failed", "jobId", job.ID.String(), "error", err)
				continue
			}
			r.metrics.RecordJobLockRenewal(renewed)
			if !renewed {
				r.logger.Warn("market_worker_job_lock_lost", "jobId", job.ID.String())
				return
			}
		}
	}
}

func (r *Runner) concurrencyLimit(count int) int {
	if count <= 0 {
		return 1
	}
	limit := r.config.MaxConcurrency
	if limit <= 0 {
		limit = r.config.BatchSize
	}
	if limit > count {
		return count
	}
	return limit
}

func (r *Runner) itemContext(parent context.Context) (context.Context, context.CancelFunc) {
	if r.config.JobTimeout <= 0 {
		return context.WithCancel(parent)
	}
	return context.WithTimeout(parent, r.config.JobTimeout)
}

func acquire(ctx context.Context, sem chan struct{}) bool {
	select {
	case sem <- struct{}{}:
		return true
	case <-ctx.Done():
		return false
	}
}

func release(sem chan struct{}) {
	<-sem
}

func renewalTimeout(interval time.Duration) time.Duration {
	timeout := 5 * time.Second
	if interval < timeout {
		return interval
	}
	return timeout
}
