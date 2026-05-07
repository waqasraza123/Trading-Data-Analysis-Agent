package jobs

import (
	"context"
	"os"
	"runtime"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"

	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
)

type Heartbeat struct {
	pool         *pgxpool.Pool
	capabilities workerdb.Capabilities
	workerID     string
	hostName     string
	processID    int
}

func NewHeartbeat(pool *pgxpool.Pool, capabilities workerdb.Capabilities, workerID string) *Heartbeat {
	hostName, _ := os.Hostname()
	return &Heartbeat{
		pool:         pool,
		capabilities: capabilities,
		workerID:     workerID,
		hostName:     hostName,
		processID:    os.Getpid(),
	}
}

func (h *Heartbeat) Starting(ctx context.Context, payload map[string]any) error {
	return h.send(ctx, "starting", payload)
}

func (h *Heartbeat) Running(ctx context.Context, payload map[string]any) error {
	return h.send(ctx, "running", payload)
}

func (h *Heartbeat) Stopped(ctx context.Context, payload map[string]any) error {
	return h.send(ctx, "stopped", payload)
}

func (h *Heartbeat) Failed(ctx context.Context, payload map[string]any) error {
	return h.send(ctx, "failed", payload)
}

func (h *Heartbeat) send(ctx context.Context, status string, payload map[string]any) error {
	if !h.capabilities.HasTable("runtime_worker_instances") || !h.capabilities.HasTable("runtime_worker_definitions") {
		return nil
	}
	if err := h.ensureDefinition(ctx); err != nil {
		return err
	}
	now := time.Now().UTC()
	stoppedAt := any(nil)
	if status == "stopped" || status == "failed" {
		stoppedAt = now
	}
	_, err := h.pool.Exec(ctx, `
insert into runtime_worker_instances (
	id, worker_definition_key, worker_id, status, host_name, process_id, started_at,
	last_heartbeat_at, stopped_at, heartbeat_payload_json, metadata_json, created_at, updated_at
) values ($1, 'go_market_worker', $2, $3, $4, $5, $6, $6, $7, $8, $9, now(), now())
on conflict (worker_id) do update set
	worker_definition_key = excluded.worker_definition_key,
	status = excluded.status,
	host_name = excluded.host_name,
	process_id = excluded.process_id,
	last_heartbeat_at = excluded.last_heartbeat_at,
	stopped_at = excluded.stopped_at,
	heartbeat_payload_json = excluded.heartbeat_payload_json,
	metadata_json = runtime_worker_instances.metadata_json || excluded.metadata_json,
	updated_at = now()
`, uuid.New(), h.workerID, status, h.hostName, h.processID, now, stoppedAt, payload, map[string]any{
		"runtime": runtime.Version(),
		"worker":  "go_market_worker",
	})
	return err
}

func (h *Heartbeat) ensureDefinition(ctx context.Context) error {
	_, err := h.pool.Exec(ctx, `
insert into runtime_worker_definitions (
	id, key, name, description, worker_type, status, command,
	required_settings_json, optional_settings_json, safety_notes_json, metadata_json, created_at, updated_at
) values (
	$1, 'go_market_worker', 'Go market data worker',
	'Additive Go sidecar for provider polling and candle ingestion.',
	'provider_polling', 'available', 'apps/go/market-worker/market-worker',
	$2, $3, $4, $5, now(), now()
)
on conflict (key) do update set
	name = excluded.name,
	description = excluded.description,
	worker_type = excluded.worker_type,
	status = excluded.status,
	command = excluded.command,
	required_settings_json = excluded.required_settings_json,
	optional_settings_json = excluded.optional_settings_json,
	safety_notes_json = excluded.safety_notes_json,
	metadata_json = runtime_worker_definitions.metadata_json || excluded.metadata_json,
	updated_at = now()
`, uuid.New(), []string{"DATABASE_URL"}, []string{"MARKET_WORKER_QUEUE_NAME", "MARKET_WORKER_HEALTH_ADDR"}, []string{
		"Market data ingestion only.",
		"Does not execute broker actions.",
		"Does not provide financial advice.",
	}, map[string]any{
		"heartbeatSupported": true,
		"implementedIn":      "go",
	})
	return err
}
