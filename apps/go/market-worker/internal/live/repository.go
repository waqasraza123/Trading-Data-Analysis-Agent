package live

import (
	"context"
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
)

type Repository struct {
	pool         *pgxpool.Pool
	capabilities workerdb.Capabilities
}

func NewRepository(pool *pgxpool.Pool, capabilities workerdb.Capabilities) *Repository {
	return &Repository{
		pool:         pool,
		capabilities: capabilities,
	}
}

func (r *Repository) RuntimeCandidates(ctx context.Context, limit int) ([]Subscription, error) {
	if !r.hasLiveSubscriptions() {
		return []Subscription{}, nil
	}
	if limit <= 0 {
		limit = 1
	}
	rows, err := r.pool.Query(ctx, `
select lfs.id, lfs.workspace_id, lfs.source_id, lfs.symbol_id, symbols.symbol,
	lfs.timeframe, lfs.provider, lfs.status, lfs.config_json::text,
	lfs.last_message_at, lfs.last_final_candle_at, lfs.lease_expires_at,
	lfs.worker_id, lfs.created_at
from live_feed_subscriptions lfs
join symbols on symbols.id = lfs.symbol_id
where lfs.status = 'active'
	and (lfs.worker_id is null or lfs.lease_expires_at is null or lfs.lease_expires_at <= now())
order by lfs.created_at asc
limit $1
`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	subscriptions := make([]Subscription, 0, limit)
	for rows.Next() {
		var subscription Subscription
		var configText string
		if err := rows.Scan(
			&subscription.ID,
			&subscription.WorkspaceID,
			&subscription.SourceID,
			&subscription.SymbolID,
			&subscription.Symbol,
			&subscription.Timeframe,
			&subscription.Provider,
			&subscription.Status,
			&configText,
			&subscription.LastMessageAt,
			&subscription.LastFinalCandle,
			&subscription.LeaseExpiresAt,
			&subscription.WorkerID,
			&subscription.CreatedAt,
		); err != nil {
			return nil, err
		}
		configMap, err := PayloadFromJSON(configText)
		if err != nil {
			return nil, err
		}
		subscription.ConfigJSON = configMap
		subscriptions = append(subscriptions, subscription)
	}
	return subscriptions, rows.Err()
}

func (r *Repository) LoadSubscription(ctx context.Context, subscriptionID uuid.UUID) (Subscription, error) {
	if !r.hasLiveSubscriptions() {
		return Subscription{}, ErrSubscriptionDisabled
	}
	row := r.pool.QueryRow(ctx, `
select lfs.id, lfs.workspace_id, lfs.source_id, lfs.symbol_id, symbols.symbol,
	lfs.timeframe, lfs.provider, lfs.status, lfs.config_json::text,
	lfs.last_message_at, lfs.last_final_candle_at, lfs.lease_expires_at,
	lfs.worker_id, lfs.created_at
from live_feed_subscriptions lfs
join symbols on symbols.id = lfs.symbol_id
where lfs.id = $1
`, subscriptionID)
	var subscription Subscription
	var configText string
	if err := row.Scan(
		&subscription.ID,
		&subscription.WorkspaceID,
		&subscription.SourceID,
		&subscription.SymbolID,
		&subscription.Symbol,
		&subscription.Timeframe,
		&subscription.Provider,
		&subscription.Status,
		&configText,
		&subscription.LastMessageAt,
		&subscription.LastFinalCandle,
		&subscription.LeaseExpiresAt,
		&subscription.WorkerID,
		&subscription.CreatedAt,
	); err != nil {
		return Subscription{}, err
	}
	configMap, err := PayloadFromJSON(configText)
	if err != nil {
		return Subscription{}, err
	}
	subscription.ConfigJSON = configMap
	return subscription, nil
}

func (r *Repository) AcquireLease(ctx context.Context, subscriptionID uuid.UUID, workerID string, expiresAt time.Time) bool {
	if !r.hasLiveSubscriptions() {
		return false
	}
	result, err := r.pool.Exec(ctx, `
update live_feed_subscriptions
set worker_id = $2, lease_expires_at = $3, updated_at = now()
where id = $1
	and status = 'active'
	and (
		worker_id is null
		or worker_id = $2
		or lease_expires_at is null
		or lease_expires_at <= now()
	)
`, subscriptionID, workerID, expiresAt)
	if err != nil {
		return false
	}
	return result.RowsAffected() == 1
}

func (r *Repository) RefreshLease(ctx context.Context, subscriptionID uuid.UUID, workerID string, expiresAt time.Time) bool {
	if !r.hasLiveSubscriptions() {
		return false
	}
	result, err := r.pool.Exec(ctx, `
update live_feed_subscriptions
set lease_expires_at = $3, updated_at = now()
where id = $1
	and worker_id = $2
`, subscriptionID, workerID, expiresAt)
	if err != nil {
		return false
	}
	return result.RowsAffected() == 1
}

func (r *Repository) ReleaseLease(ctx context.Context, subscriptionID uuid.UUID, workerID string) bool {
	if !r.hasLiveSubscriptions() {
		return false
	}
	result, err := r.pool.Exec(ctx, `
update live_feed_subscriptions
set worker_id = null, lease_expires_at = null, updated_at = now()
where id = $1
	and worker_id = $2
`, subscriptionID, workerID)
	if err != nil {
		return false
	}
	return result.RowsAffected() == 1
}

func (r *Repository) RecordHeartbeat(ctx context.Context, subscriptionID uuid.UUID, providerTimestamp *time.Time) error {
	if !r.hasLiveSubscriptions() {
		return nil
	}
	_, err := r.pool.Exec(ctx, `
update live_feed_subscriptions
set last_message_at = now(),
	status = case when status = 'stale' then 'active' else status end,
	last_error = case when status = 'stale' then null else last_error end,
	updated_at = now()
where id = $1
`, subscriptionID)
	return err
}

func (r *Repository) RecordFinalCandle(ctx context.Context, subscriptionID uuid.UUID, finalCandleAt time.Time) error {
	if !r.hasLiveSubscriptions() {
		return nil
	}
	_, err := r.pool.Exec(ctx, `
update live_feed_subscriptions
set last_final_candle_at = $2,
	status = case when status = 'stale' then 'active' else status end,
	last_error = case when status = 'stale' then null else last_error end,
	updated_at = now()
where id = $1
`, subscriptionID, finalCandleAt)
	return err
}

func (r *Repository) MarkFailed(ctx context.Context, subscriptionID uuid.UUID, message string) error {
	if !r.hasLiveSubscriptions() {
		return nil
	}
	_, err := r.pool.Exec(ctx, `
update live_feed_subscriptions
set status = 'failed',
	last_error = left($2, 1000),
	worker_id = null,
	lease_expires_at = null,
	updated_at = now()
where id = $1
`, subscriptionID, sanitizeMessage(message))
	return err
}

func (r *Repository) CreateEvent(
	ctx context.Context,
	subscription Subscription,
	eventType EventType,
	providerTimestamp *time.Time,
	payload map[string]any,
) (uuid.UUID, bool, error) {
	if !r.hasLiveEvents() {
		return uuid.Nil, false, nil
	}
	eventID := uuid.New()
	_, err := r.pool.Exec(ctx, `
insert into live_feed_events (
	id, workspace_id, source_id, subscription_id, provider, event_type, received_at,
	provider_timestamp, payload_json, processing_status, error_message, created_at
) values (
	$1, $2, $3, $4, $5, $6, now(), $7, $8, $9, null, now()
)`, eventID, subscription.WorkspaceID, subscription.SourceID, subscription.ID, subscription.Provider, eventType, providerTimestamp, payload, EventStatusReceived)
	if err != nil {
		return uuid.Nil, true, err
	}
	return eventID, true, nil
}

func (r *Repository) UpdateEventStatus(ctx context.Context, eventID uuid.UUID, status EventProcessingStatus, errorMessage string) error {
	if !r.hasLiveEvents() {
		return nil
	}
	_, err := r.pool.Exec(ctx, `
update live_feed_events
set processing_status = $2, error_message = $3
where id = $1
`, eventID, status, sanitizeMessage(errorMessage))
	return err
}

func (r *Repository) HasOpenGapRequest(ctx context.Context, subscription Subscription, startTime time.Time, endTime time.Time) (bool, error) {
	if !r.hasProviderPollingRequests() {
		return false, nil
	}
	var exists bool
	err := r.pool.QueryRow(ctx, `
select exists (
	select 1
	from provider_polling_requests
	where workspace_id = $1
		and source_id = $2
		and symbol_id = $3
		and provider = $4
		and timeframe = $5
		and start_time = $6
		and end_time = $7
		and status in ('pending', 'running')
)
`, subscription.WorkspaceID, subscription.SourceID, subscription.SymbolID, subscription.Provider, subscription.Timeframe, startTime, endTime).Scan(&exists)
	return exists, err
}

func (r *Repository) CreateGapRequest(ctx context.Context, subscription Subscription, startTime time.Time, endTime time.Time, providerSymbol string) (bool, error) {
	if !r.hasProviderPollingRequests() {
		return false, nil
	}
	hasRequest, err := r.HasOpenGapRequest(ctx, subscription, startTime, endTime)
	if err != nil {
		return false, err
	}
	if hasRequest {
		return false, nil
	}
	var createdRequestID uuid.UUID
	err := r.pool.QueryRow(ctx, `
insert into provider_polling_requests (
	id, workspace_id, source_id, symbol_id, provider, provider_symbol, timeframe,
	status, start_time, end_time, request_metadata_json, response_metadata_json,
	error_message, started_at, completed_at, created_at, updated_at
) values (
	$1, $2, $3, $4, $5, $6, $7,
	'pending', $8, $9,
	$10,
	'{}'::jsonb,
	null,
	null,
	null,
	now(),
	now()
)
on conflict do nothing
returning id
`, uuid.New(), subscription.WorkspaceID, subscription.SourceID, subscription.SymbolID, subscription.Provider, providerSymbol, subscription.Timeframe, startTime, endTime, map[string]any{
		"requestedByGoWorker": true,
		"requestSource":       "go_market_worker_live",
		"subscriptionId":      subscription.ID.String(),
		"requestedAt":         time.Now().UTC().Format(time.RFC3339Nano),
	}).Scan(&createdRequestID)
	if err == pgx.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return true, nil
}

func (r *Repository) hasLiveSubscriptions() bool {
	return r.capabilities.HasTable("live_feed_subscriptions") && r.capabilities.HasOptionalColumns("live_feed_subscriptions")
}

func (r *Repository) hasLiveEvents() bool {
	return r.capabilities.HasTable("live_feed_events") && r.capabilities.HasOptionalColumns("live_feed_events")
}

func (r *Repository) hasProviderPollingRequests() bool {
	return r.capabilities.HasTable("provider_polling_requests")
}

func sanitizeMessage(value string) string {
	if len(value) <= 1000 {
		return value
	}
	return value[:1000]
}

func PayloadFromJSON(text string) (map[string]any, error) {
	payload := map[string]any{}
	if text == "" {
		return payload, nil
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		return nil, err
	}
	return payload, nil
}
