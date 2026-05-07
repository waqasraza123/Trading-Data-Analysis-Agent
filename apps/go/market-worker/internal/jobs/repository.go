package jobs

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
)

type Repository struct {
	pool             *pgxpool.Pool
	capabilities     workerdb.Capabilities
}

func NewRepository(pool *pgxpool.Pool, capabilities workerdb.Capabilities) *Repository {
	return &Repository{pool: pool, capabilities: capabilities}
}

func (r *Repository) ClaimJobQueueItems(ctx context.Context, queueName string, workerID string, limit int, lockDuration time.Duration) ([]Job, error) {
	tx, err := r.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = tx.Rollback(ctx)
	}()
	rows, err := tx.Query(ctx, `
select id, workspace_id, queue_name, job_type, attempts, max_attempts, payload_json::text
from job_queue_items
where (queue_name = $1 or job_type = any($2))
	and status in ('pending', 'scheduled', 'retrying', 'running')
	and attempts < max_attempts
	and (available_at is null or available_at <= now())
	and (locked_by is null or locked_until is null or locked_until <= now())
order by
	case priority when 'urgent' then 0 when 'high' then 1 when 'normal' then 2 else 3 end,
	available_at asc nulls first
limit $3
for update skip locked
`, queueName, supportedTypes(), limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	jobs := make([]Job, 0, limit)
	for rows.Next() {
		var job Job
		var workspaceID *uuid.UUID
		var payloadText string
		if err := rows.Scan(&job.ID, &workspaceID, &job.QueueName, &job.JobType, &job.Attempts, &job.MaxAttempts, &payloadText); err != nil {
			return nil, err
		}
		payload, err := PayloadFromJSON(payloadText)
		if err != nil {
			return nil, err
		}
		job.WorkspaceID = workspaceID
		job.Payload = payload
		jobs = append(jobs, job)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	lockUntil := time.Now().UTC().Add(lockDuration)
	for index := range jobs {
		_, err := tx.Exec(ctx, `
update job_queue_items
set status = 'running',
	locked_by = $2,
	locked_until = $3,
	attempts = attempts + 1,
	started_at = coalesce(started_at, now()),
	error_code = null,
	error_message = null,
	updated_at = now()
where id = $1
`, jobs[index].ID, workerID, lockUntil)
		if err != nil {
			return nil, err
		}
		jobs[index].Attempts++
		jobs[index].LockedBy = workerID
		if err := r.addJobEventTx(ctx, tx, jobs[index], "claimed", "Job claimed", map[string]any{"workerId": workerID, "attempts": jobs[index].Attempts}); err != nil {
			return nil, err
		}
	}
	if err := tx.Commit(ctx); err != nil {
		return nil, err
	}
	return jobs, nil
}

func (r *Repository) CompleteJob(ctx context.Context, job Job, result map[string]any, warnings bool) error {
	status := "completed"
	if warnings {
		status = "completed_with_warnings"
	}
	tag, err := r.pool.Exec(ctx, `
update job_queue_items
set status = $2,
	result_json = $3,
	error_code = null,
	error_message = null,
	locked_by = null,
	locked_until = null,
	completed_at = now(),
	updated_at = now()
where id = $1
	and status = 'running'
	and locked_by = $4
`, job.ID, status, result, job.LockedBy)
	if err != nil {
		return err
	}
	if tag.RowsAffected() != 1 {
		return fmt.Errorf("job_lock_not_owned")
	}
	return r.AddJobEvent(ctx, job, "completed", "Job completed", map[string]any{"completedWithWarnings": warnings})
}

func (r *Repository) FailJob(ctx context.Context, job Job, code string, message string, retryBackoff time.Duration) error {
	status := "failed"
	var availableAt *time.Time
	if job.Attempts < job.MaxAttempts {
		status = "retrying"
		next := time.Now().UTC().Add(retryBackoff * time.Duration(max(job.Attempts, 1)))
		availableAt = &next
	} else {
		status = "dead_letter"
	}
	tag, err := r.pool.Exec(ctx, `
update job_queue_items
set status = $2,
	error_code = left($3, 120),
	error_message = left($4, 2000),
	locked_by = null,
	locked_until = null,
	available_at = coalesce($5, available_at),
	completed_at = case when $2 in ('failed', 'dead_letter') then now() else completed_at end,
	updated_at = now()
where id = $1
	and status = 'running'
	and locked_by = $6
`, job.ID, status, code, message, availableAt, job.LockedBy)
	if err != nil {
		return err
	}
	if tag.RowsAffected() != 1 {
		return fmt.Errorf("job_lock_not_owned")
	}
	eventType := "failed"
	if status == "retrying" {
		eventType = "retry_scheduled"
	}
	if status == "dead_letter" {
		eventType = "dead_lettered"
	}
	return r.AddJobEvent(ctx, job, eventType, "Job failed", map[string]any{"errorCode": code, "status": status})
}

func (r *Repository) FailJobTerminal(ctx context.Context, job Job, code string, message string) error {
	status := "failed"
	if job.Attempts >= job.MaxAttempts {
		status = "dead_letter"
	}
	tag, err := r.pool.Exec(ctx, `
update job_queue_items
set status = $2,
	error_code = left($3, 120),
	error_message = left($4, 2000),
	locked_by = null,
	locked_until = null,
	completed_at = now(),
	updated_at = now()
where id = $1
	and status = 'running'
	and locked_by = $5
`, job.ID, status, code, message, job.LockedBy)
	if err != nil {
		return err
	}
	if tag.RowsAffected() != 1 {
		return fmt.Errorf("job_lock_not_owned")
	}
	eventType := "failed"
	if status == "dead_letter" {
		eventType = "dead_lettered"
	}
	return r.AddJobEvent(ctx, job, eventType, "Job failed without retry", map[string]any{"errorCode": code, "status": status, "retryable": false})
}

func (r *Repository) RenewJobLock(ctx context.Context, job Job, workerID string, lockDuration time.Duration) (bool, error) {
	lockUntil := time.Now().UTC().Add(lockDuration)
	tag, err := r.pool.Exec(ctx, `
update job_queue_items
set locked_until = $3,
	updated_at = now()
where id = $1
	and locked_by = $2
	and status = 'running'
`, job.ID, workerID, lockUntil)
	if err != nil {
		return false, err
	}
	return tag.RowsAffected() == 1, nil
}

func (r *Repository) ClaimProviderPollingRequests(ctx context.Context, workerID string, limit int, staleAfter time.Duration) ([]PollingRequest, error) {
	tx, err := r.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = tx.Rollback(ctx)
	}()
	rows, err := tx.Query(ctx, `
select id, workspace_id, source_id, symbol_id, provider, provider_symbol, timeframe, status,
	start_time, end_time, coalesce(limit, 1000), request_metadata_json::text
from provider_polling_requests
where status = 'pending'
	or (
		$2 > 0
		and status = 'running'
		and started_at is not null
		and started_at <= now() - ($2 * interval '1 second')
		and request_metadata_json ->> 'claimedByGoWorker' = 'true'
	)
order by
	case when status = 'pending' then 0 else 1 end,
	created_at asc
limit $1
for update skip locked
`, limit, int(staleAfter.Seconds()))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	requests := make([]PollingRequest, 0, limit)
	for rows.Next() {
		var request PollingRequest
		var metadataText string
		var requestID uuid.UUID
		var status string
		if err := rows.Scan(&requestID, &request.WorkspaceID, &request.SourceID, &request.SymbolID, &request.Provider, &request.ProviderSymbol, &request.Timeframe, &status, &request.StartTime, &request.EndTime, &request.Limit, &metadataText); err != nil {
			return nil, err
		}
		metadata, err := PayloadFromJSON(metadataText)
		if err != nil {
			return nil, err
		}
		request.ID = &requestID
		request.Metadata = metadata
		request.Reclaimed = status == "running"
		requests = append(requests, request)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	for _, request := range requests {
		_, err := tx.Exec(ctx, `
update provider_polling_requests
set status = 'running',
	started_at = now(),
	request_metadata_json = request_metadata_json || $2::jsonb,
	response_metadata_json = '{}'::jsonb,
	error_message = null,
	completed_at = null,
	updated_at = now()
where id = $1
`, *request.ID, map[string]any{
			"claimedBy":           workerID,
			"claimedByGoWorker":   true,
			"claimedAt":           time.Now().UTC().Format(time.RFC3339),
			"staleAfterSeconds":   int(staleAfter.Seconds()),
			"reclaimedByGoWorker": request.Reclaimed,
		})
		if err != nil {
			return nil, err
		}
	}
	if err := tx.Commit(ctx); err != nil {
		return nil, err
	}
	return requests, nil
}

func (r *Repository) LoadProviderPollingRequest(ctx context.Context, id uuid.UUID) (PollingRequest, error) {
	var request PollingRequest
	var metadataText string
	err := r.pool.QueryRow(ctx, `
select id, workspace_id, source_id, symbol_id, provider, provider_symbol, timeframe,
	start_time, end_time, coalesce(limit, 1000), request_metadata_json::text
from provider_polling_requests
where id = $1
`, id).Scan(&id, &request.WorkspaceID, &request.SourceID, &request.SymbolID, &request.Provider, &request.ProviderSymbol, &request.Timeframe, &request.StartTime, &request.EndTime, &request.Limit, &metadataText)
	if err != nil {
		return PollingRequest{}, err
	}
	metadata, err := PayloadFromJSON(metadataText)
	if err != nil {
		return PollingRequest{}, err
	}
	request.ID = &id
	request.Metadata = metadata
	return request, nil
}

func (r *Repository) CompleteProviderPollingRequest(ctx context.Context, id uuid.UUID, received int, stored int, skipped int, metadata map[string]any, warnings bool) error {
	status := "completed"
	if warnings {
		status = "completed_with_warnings"
	}
	if stored == 0 {
		status = "failed"
	}
	_, err := r.pool.Exec(ctx, `
update provider_polling_requests
set status = $2,
	response_metadata_json = $3,
	received_candle_count = $4,
	stored_candle_count = $5,
	skipped_candle_count = $6,
	error_message = case when $2 = 'failed' then 'Provider polling stored no candles' else null end,
	completed_at = now(),
	updated_at = now()
where id = $1
`, id, status, metadata, received, stored, skipped)
	return err
}

func (r *Repository) FailProviderPollingRequest(ctx context.Context, id uuid.UUID, code string, message string) error {
	_, err := r.pool.Exec(ctx, `
update provider_polling_requests
set status = 'failed',
	error_message = left($2, 2000),
	completed_at = now(),
	updated_at = now()
where id = $1
`, id, message)
	if err != nil {
		return err
	}
	return r.AddProviderPollingError(ctx, id, uuid.Nil, code, message, nil)
}

func (r *Repository) AddProviderPollingError(ctx context.Context, requestID uuid.UUID, workspaceID uuid.UUID, code string, message string, raw map[string]any) error {
	if !r.capabilities.HasTable("provider_polling_errors") || !r.capabilities.HasOptionalColumns("provider_polling_errors") {
		return nil
	}
	if workspaceID == uuid.Nil {
		err := r.pool.QueryRow(ctx, `select workspace_id from provider_polling_requests where id = $1`, requestID).Scan(&workspaceID)
		if err != nil {
			return err
		}
	}
	_, err := r.pool.Exec(ctx, `
insert into provider_polling_errors (
	id, workspace_id, polling_request_id, error_code, error_message, raw_item_json, created_at
) values ($1, $2, $3, left($4, 80), left($5, 2000), $6, now())
`, uuid.New(), workspaceID, requestID, code, message, raw)
	return err
}

func (r *Repository) AddJobEvent(ctx context.Context, job Job, eventType string, message string, metadata map[string]any) error {
	return r.addJobEvent(ctx, r.pool, job, eventType, message, metadata)
}

func (r *Repository) addJobEventTx(ctx context.Context, tx pgx.Tx, job Job, eventType string, message string, metadata map[string]any) error {
	return r.addJobEvent(ctx, tx, job, eventType, message, metadata)
}

type eventExecutor interface {
	Exec(context.Context, string, ...any) (pgconn.CommandTag, error)
}

func (r *Repository) addJobEvent(ctx context.Context, executor eventExecutor, job Job, eventType string, message string, metadata map[string]any) error {
	if !r.capabilities.HasTable("job_queue_events") || !r.capabilities.HasOptionalColumns("job_queue_events") {
		return nil
	}
	_, err := executor.Exec(ctx, `
insert into job_queue_events (id, workspace_id, job_id, event_type, message, metadata_json, created_at)
values ($1, $2, $3, $4, $5, $6, now())
`, uuid.New(), job.WorkspaceID, job.ID, eventType, message, metadata)
	return err
}

func supportedTypes() []string {
	values := make([]string, 0, len(SupportedJobTypes))
	for value := range SupportedJobTypes {
		values = append(values, value)
	}
	return values
}
