package worker

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/jobs"
)

func (r *Runner) handleJob(ctx context.Context, job jobs.Job) error {
	if !jobs.SupportedJobTypes[job.JobType] {
		writeCtx, cancel := r.writeContext(ctx)
		defer cancel()
		err := r.repository.FailJobTerminal(writeCtx, job, "unsupported_job_type", "Unsupported job type")
		if err == nil {
			r.metrics.RecordFailed(false)
		}
		return err
	}
	request, err := jobs.DecodePayload(job.Payload, job.WorkspaceID, r.config.MaxCandlesPerRequest)
	if err != nil {
		writeCtx, cancel := r.writeContext(ctx)
		defer cancel()
		_ = r.repository.FailJobTerminal(writeCtx, job, "validation_error", err.Error())
		r.metrics.RecordFailed(false)
		return err
	}
	result, err := r.polling.Process(ctx, request)
	if err != nil {
		code := errorCode(err)
		if code == "job_timeout" {
			r.metrics.RecordTimedOut()
		}
		writeCtx, cancel := r.writeContext(ctx)
		defer cancel()
		if retryableError(code, err) {
			_ = r.repository.FailJob(writeCtx, job, code, err.Error(), r.config.RetryBackoff)
		} else {
			_ = r.repository.FailJobTerminal(writeCtx, job, code, err.Error())
		}
		r.metrics.RecordFailed(true)
		return err
	}
	warnings := result.Skipped > 0 || result.Warnings > 0 || result.ProviderErrors > 0 || result.Conflicted > 0 || result.Invalid > 0
	writeCtx, cancel := r.writeContext(ctx)
	defer cancel()
	if err := r.repository.CompleteJob(writeCtx, job, map[string]any{
		"provider":       result.Provider,
		"providerSymbol": result.ProviderSymbol,
		"timeframe":      result.Timeframe,
		"received":       result.Received,
		"stored":         result.Stored,
		"skipped":        result.Skipped,
		"conflicted":     result.Conflicted,
		"invalid":        result.Invalid,
	}, warnings); err != nil {
		r.metrics.RecordFailed(false)
		return err
	}
	r.metrics.RecordCompleted(result.Received, result.Counts.Inserted+result.Counts.Updated, result.Skipped, result.Conflicted)
	return nil
}

func (r *Runner) handleDirectRequest(ctx context.Context, request jobs.PollingRequest) error {
	result, err := r.polling.Process(ctx, request)
	if err != nil {
		code := errorCode(err)
		if code == "job_timeout" {
			r.metrics.RecordTimedOut()
		}
		if request.ID != nil {
			writeCtx, cancel := r.writeContext(ctx)
			defer cancel()
			_ = r.repository.FailProviderPollingRequest(writeCtx, *request.ID, code, err.Error())
		}
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
	if errors.Is(err, context.DeadlineExceeded) {
		return "job_timeout"
	}
	if errors.Is(err, context.Canceled) {
		return "job_canceled"
	}
	text := err.Error()
	if text == "" {
		return fmt.Sprintf("%T", err)
	}
	code := strings.Split(text, ":")[0]
	code = strings.TrimSpace(code)
	code = strings.ReplaceAll(code, " ", "_")
	if code == "" || len(code) > 120 {
		return fmt.Sprintf("%T", err)
	}
	return code
}

func retryableError(code string, err error) bool {
	text := strings.ToLower(code + " " + err.Error())
	terminalMarkers := []string{
		"validation_error",
		"provider_not_supported",
		"unsupported_timeframe",
		"missing_",
		"invalid_",
		"secret_metadata",
		"not_configured",
	}
	for _, marker := range terminalMarkers {
		if strings.Contains(text, marker) {
			return false
		}
	}
	retryableMarkers := []string{
		"network",
		"timeout",
		"http_error",
		"temporarily",
		"connection",
		"deadlock",
		"serialization",
	}
	for _, marker := range retryableMarkers {
		if strings.Contains(text, marker) {
			return true
		}
	}
	return true
}

func (r *Runner) writeContext(parent context.Context) (context.Context, context.CancelFunc) {
	timeout := r.config.DBWriteTimeout
	if timeout <= 0 {
		timeout = 15 * time.Second
	}
	if parent == nil || parent.Err() != nil {
		return context.WithTimeout(context.Background(), timeout)
	}
	return context.WithTimeout(parent, timeout)
}
