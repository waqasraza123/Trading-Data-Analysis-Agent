package worker

import (
	"context"
	"errors"
	"log/slog"
	"sync"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/config"
	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/health"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/jobs"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/live"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/polling"
)

type Runner struct {
	config       config.Config
	pool         *pgxpool.Pool
	capabilities workerdb.Capabilities
	repository   *jobs.Repository
	polling      *polling.Service
	live         *live.Service
	heartbeat    *jobs.Heartbeat
	metrics      *health.Metrics
	logger       *slog.Logger
}

func NewRunner(cfg config.Config, pool *pgxpool.Pool, capabilities workerdb.Capabilities, pollingService *polling.Service, liveService *live.Service, metrics *health.Metrics, logger *slog.Logger) *Runner {
	return &Runner{
		config:       cfg,
		pool:         pool,
		capabilities: capabilities,
		repository:   jobs.NewRepository(pool, capabilities),
		polling:      pollingService,
		live:         liveService,
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

	runCtx, cancel := context.WithCancel(ctx)
	defer cancel()

	errCh := make(chan error, 2)
	loopCount := 1

	go func() {
		errCh <- r.runJobsLoop(runCtx)
	}()
	if r.live != nil && r.live.Enabled() {
		loopCount = 2
		go func() {
			errCh <- r.runLiveLoop(runCtx)
		}()
	}

	for completed := 0; completed < loopCount; completed++ {
		select {
		case <-ctx.Done():
			return nil
		case err := <-errCh:
			if err != nil && !errors.Is(err, context.Canceled) {
				cancel()
				return err
			}
		}
	}
	return nil
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

	if r.live != nil && r.live.Enabled() {
		additionalClaims, liveErr := r.processLiveCandidates(ctx)
		claimed += additionalClaims
		if liveErr != nil {
			_ = r.heartbeat.Failed(ctx, map[string]any{"error": liveErr.Error(), "runMode": "once"})
			return claimed, liveErr
		}
	}
	_ = r.heartbeat.Running(ctx, map[string]any{"claimedCount": claimed, "queueName": r.config.QueueName, "runMode": "once"})
	return claimed, nil
}

func (r *Runner) runJobsLoop(ctx context.Context) error {
	ticker := time.NewTicker(r.config.PollInterval)
	defer ticker.Stop()

	for {
		claimed, err := r.pollOnce(ctx)
		if err != nil {
			r.logger.Warn("market_worker_poll_failed", "error", err, "mode", r.config.Mode)
			if ctx.Err() != nil {
				return ctx.Err()
			}
			_ = r.heartbeat.Failed(ctx, map[string]any{"error": err.Error(), "runMode": "jobs"})
		} else {
			_ = r.heartbeat.Running(ctx, map[string]any{"claimedCount": claimed, "queueName": r.config.QueueName, "runMode": "jobs"})
		}
		if claimed > 0 {
			continue
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
		}
	}
}

func (r *Runner) runLiveLoop(ctx context.Context) error {
	if !r.live.Enabled() {
		return nil
	}
	ticker := time.NewTicker(r.config.LiveStreamClaimInterval)
	defer ticker.Stop()

	for {
		claimed, err := r.processLiveCandidates(ctx)
		if err != nil {
			r.logger.Warn("market_worker_live_claim_failed", "error", err)
			if ctx.Err() != nil {
				return ctx.Err()
			}
			_ = r.heartbeat.Failed(ctx, map[string]any{"error": err.Error(), "runMode": "live"})
		} else {
			_ = r.heartbeat.Running(ctx, map[string]any{"claimedCount": claimed, "runMode": "live"})
		}
		if claimed > 0 {
			continue
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
		}
	}
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

func (r *Runner) processLiveCandidates(ctx context.Context) (int, error) {
	if !r.live.Enabled() {
		return 0, nil
	}
	staleCount, err := r.live.MarkStaleCandidates(ctx)
	if err != nil {
		return 0, err
	}
	if staleCount > 0 && r.metrics != nil {
		r.metrics.RecordLiveSubscriptionStale(staleCount)
		r.logger.Info("market_worker_live_subscriptions_stale", "count", staleCount)
	}
	subscriptions, err := r.live.RuntimeCandidates(ctx, r.config.LiveStreamClaimBatchSize)
	if err != nil {
		return 0, err
	}
	if len(subscriptions) == 0 {
		return 0, nil
	}
	var wg sync.WaitGroup
	errCh := make(chan error, len(subscriptions))
	claimedMu := sync.Mutex{}
	claimed := 0
	sem := make(chan struct{}, r.concurrencyLimit(len(subscriptions)))
	for _, subscription := range subscriptions {
		wg.Add(1)
		go func(item live.Subscription) {
			defer wg.Done()
			if !acquire(ctx, sem) {
				return
			}
			defer release(sem)
			if !r.live.AcquireLease(ctx, item) {
				return
			}
			claimedMu.Lock()
			claimed++
			claimedMu.Unlock()
			r.metrics.RecordLiveSubscriptionClaimed()
			if err := r.handleLiveWithLease(ctx, item); err != nil {
				if !errors.Is(err, context.Canceled) {
					errCh <- err
				}
			}
		}(subscription)
	}
	wg.Wait()
	close(errCh)
	var firstErr error
	for streamErr := range errCh {
		if streamErr == nil {
			continue
		}
		if firstErr == nil {
			firstErr = streamErr
		}
	}
	return claimed, firstErr
}

func (r *Runner) handleLiveWithLease(ctx context.Context, subscription live.Subscription) error {
	leaseCtx, cancel := context.WithCancel(ctx)
	done := make(chan struct{})
	go func() {
		defer close(done)
		r.renewLiveLease(leaseCtx, subscription)
	}()
	err := r.live.Process(leaseCtx, subscription)
	cancel()
	<-done
	releaseCtx, releaseCancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer releaseCancel()
	if !r.live.ReleaseLease(releaseCtx, subscription) {
		r.logger.Warn("market_worker_live_lease_release_failed", "subscriptionId", subscription.ID.String())
	}
	return err
}

func (r *Runner) renewLiveLease(ctx context.Context, subscription live.Subscription) {
	interval := r.config.LiveStreamLeaseDuration / 3
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
			renewed, err := r.live.RefreshLease(renewCtx, subscription)
			cancel()
			if err != nil {
				r.logger.Warn("market_worker_live_lease_renewal_failed", "subscriptionId", subscription.ID.String(), "error", err)
				continue
			}
			if !renewed {
				r.logger.Warn("market_worker_live_lease_lost", "subscriptionId", subscription.ID.String())
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

func reclaimedRequestCount(requests []jobs.PollingRequest) int {
	count := 0
	for _, request := range requests {
		if request.Reclaimed {
			count++
		}
	}
	return count
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
