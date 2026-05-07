package worker

import (
	"context"
	"fmt"
	"time"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/jobs"
)

func (r *Runner) handleJob(ctx context.Context, job jobs.Job) error {
	if !jobs.SupportedJobTypes[job.JobType] {
		err := r.repository.FailJob(ctx, job, "unsupported_job_type", "Unsupported job type", time.Minute)
		if err == nil {
			r.metrics.RecordFailed(false)
		}
		return err
	}
	request, err := jobs.DecodePayload(job.Payload, job.WorkspaceID, r.config.MaxCandlesPerRequest)
	if err != nil {
		_ = r.repository.FailJob(ctx, job, "validation_error", err.Error(), time.Minute)
		r.metrics.RecordFailed(false)
		return err
	}
	result, err := r.polling.Process(ctx, request)
	if err != nil {
		_ = r.repository.FailJob(ctx, job, errorCode(err), err.Error(), time.Minute)
		r.metrics.RecordFailed(true)
		return err
	}
	warnings := result.Skipped > 0 || result.Warnings > 0 || result.ProviderErrors > 0 || result.Conflicted > 0 || result.Invalid > 0
	if err := r.repository.CompleteJob(ctx, job, map[string]any{
		"provider":       result.Provider,
		"providerSymbol": result.ProviderSymbol,
		"timeframe":      result.Timeframe,
		"received":       result.Received,
		"stored":         result.Stored,
		"skipped":        result.Skipped,
		"conflicted":     result.Conflicted,
		"invalid":        result.Invalid,
	}, warnings); err != nil {
		return err
	}
	r.metrics.RecordCompleted(result.Received, result.Counts.Inserted+result.Counts.Updated, result.Skipped, result.Conflicted)
	return nil
}

func (r *Runner) handleDirectRequest(ctx context.Context, request jobs.PollingRequest) error {
	result, err := r.polling.Process(ctx, request)
	if err != nil {
		r.metrics.RecordFailed(true)
		return err
	}
	r.metrics.RecordCompleted(result.Received, result.Counts.Inserted+result.Counts.Updated, result.Skipped, result.Conflicted)
	return nil
}

func errorCode(err error) string {
	if err == nil {
		return ""
	}
	return fmt.Sprintf("%T", err)
}
