package candles

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/shopspring/decimal"

	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
)

type BatchWriter struct {
	pool         *pgxpool.Pool
	capabilities workerdb.Capabilities
}

type RunContext struct {
	ID                       *uuid.UUID
	WorkspaceID              uuid.UUID
	ProviderPollingRequestID *uuid.UUID
	SourceID                 uuid.UUID
	SymbolID                 uuid.UUID
	Timeframe                string
	StartedAt               time.Time
}

func NewBatchWriter(pool *pgxpool.Pool, capabilities workerdb.Capabilities) *BatchWriter {
	return &BatchWriter{pool: pool, capabilities: capabilities}
}

func (w *BatchWriter) StartRun(ctx context.Context, workspaceID uuid.UUID, sourceID uuid.UUID, symbolID uuid.UUID, timeframe string, providerPollingRequestID *uuid.UUID) (RunContext, error) {
	run := RunContext{
		WorkspaceID:              workspaceID,
		ProviderPollingRequestID: providerPollingRequestID,
		SourceID:                 sourceID,
		SymbolID:                 symbolID,
		Timeframe:                timeframe,
		StartedAt:                time.Now().UTC(),
	}
	if !w.capabilities.HasTable("candle_ingestion_performance_runs") {
		return run, nil
	}
	runID := uuid.New()
	_, err := w.pool.Exec(ctx, `
insert into candle_ingestion_performance_runs (
	id, workspace_id, provider_polling_request_id, source_id, symbol_id, timeframe, status,
	ingestion_mode, diagnostics_json, created_at, updated_at
) values ($1, $2, $3, $4, $5, $6, 'running', 'provider_polling', $7, now(), now())
`, runID, workspaceID, providerPollingRequestID, sourceID, symbolID, timeframe, map[string]any{
		"writer": "go_market_worker",
	})
	if err != nil {
		return run, err
	}
	run.ID = &runID
	return run, nil
}

func (w *BatchWriter) FinishRun(ctx context.Context, run RunContext, counts WriteCounts, failed bool) error {
	if run.ID == nil || !w.capabilities.HasTable("candle_ingestion_performance_runs") {
		return nil
	}
	elapsed := int(time.Since(run.StartedAt).Milliseconds())
	status := "completed"
	if failed {
		status = "failed"
	} else if counts.Invalid > 0 || counts.Conflicted > 0 || counts.Failed > 0 {
		status = "completed_with_warnings"
	}
	_, err := w.pool.Exec(ctx, `
update candle_ingestion_performance_runs
set status = $2,
	rows_received = $3,
	rows_validated = $4,
	rows_inserted = $5,
	rows_updated = $6,
	rows_skipped_duplicate = $7,
	rows_conflicted = $8,
	rows_failed = $9,
	batch_count = $10,
	elapsed_ms = $11,
	updated_at = now()
where id = $1
`, *run.ID, status, counts.Received, counts.Valid, counts.Inserted, counts.Updated, counts.DuplicateSkipped, counts.Conflicted, counts.Invalid+counts.Failed, counts.Batches, elapsed)
	return err
}

func (w *BatchWriter) Write(ctx context.Context, run RunContext, candles []Candle) (WriteCounts, []Conflict, error) {
	counts := WriteCounts{Received: len(candles), Valid: len(candles)}
	if len(candles) == 0 {
		return counts, nil, nil
	}
	existing, err := w.fetchExisting(ctx, candles)
	if err != nil {
		return counts, nil, err
	}
	batch := &pgx.Batch{}
	conflicts := make([]Conflict, 0)
	virtual := make(map[string]ExistingCandle, len(existing)+len(candles))
	for key, value := range existing {
		virtual[key] = value
	}
	for _, incoming := range candles {
		key := identityKey(incoming.Identity())
		current, exists := virtual[key]
		if !exists {
			id := uuid.New()
			insertCandle(batch, id, incoming)
			virtual[key] = ExistingCandle{ID: id, Candle: incoming, IsFinal: incoming.IsFinal, Exists: true}
			counts.Inserted++
			continue
		}
		if current.IsFinal && !incoming.IsFinal {
			counts.DuplicateSkipped++
			conflicts = append(conflicts, buildConflict("partial_after_final", "kept_existing", current.Candle, incoming))
			continue
		}
		if current.IsFinal && incoming.IsFinal {
			if valuesDiffer(current.Candle, incoming) {
				counts.Conflicted++
				conflicts = append(conflicts, buildConflict("final_conflict", "kept_existing", current.Candle, incoming))
				continue
			}
			counts.DuplicateSkipped++
			conflicts = append(conflicts, buildConflict("duplicate_final", "skipped", current.Candle, incoming))
			continue
		}
		updateCandle(batch, current.ID, incoming)
		virtual[key] = ExistingCandle{ID: current.ID, Candle: incoming, IsFinal: incoming.IsFinal, Exists: true}
		counts.Updated++
	}
	if batch.Len() > 0 {
		results := w.pool.SendBatch(ctx, batch)
		for i := 0; i < batch.Len(); i++ {
			if _, err := results.Exec(); err != nil {
				_ = results.Close()
				return counts, conflicts, err
			}
		}
		if err := results.Close(); err != nil {
			return counts, conflicts, err
		}
	}
	if len(conflicts) > 0 && run.ID != nil && w.capabilities.HasTable("candle_ingestion_conflicts") {
		if err := w.recordConflicts(ctx, *run.ID, conflicts); err != nil {
			return counts, conflicts, err
		}
	}
	counts.Batches = 1
	return counts, conflicts, nil
}

func (w *BatchWriter) RecordInvalidConflicts(ctx context.Context, run RunContext, invalid []ValidationIssue, fallback Candle) error {
	if run.ID == nil || !w.capabilities.HasTable("candle_ingestion_conflicts") {
		return nil
	}
	batch := &pgx.Batch{}
	for _, item := range invalid {
		conflictType := "invalid_ohlc"
		if item.Code == "timestamp_misalignment" || item.Code == "invalid_timestamp" {
			conflictType = "timestamp_misalignment"
		}
		incoming := item.RawItem
		if incoming == nil {
			incoming = SerializeCandle(fallback)
		}
		batch.Queue(`
insert into candle_ingestion_conflicts (
	id, workspace_id, performance_run_id, symbol_id, source_id, timeframe, timestamp,
	conflict_type, existing_candle_json, incoming_candle_json, resolution, created_at
) values ($1, $2, $3, $4, $5, $6, $7, $8, '{}'::jsonb, $9, 'rejected', now())
`, uuid.New(), run.WorkspaceID, *run.ID, run.SymbolID, run.SourceID, run.Timeframe, fallback.Timestamp, conflictType, incoming)
	}
	results := w.pool.SendBatch(ctx, batch)
	for i := 0; i < batch.Len(); i++ {
		if _, err := results.Exec(); err != nil {
			_ = results.Close()
			return err
		}
	}
	return results.Close()
}

func (w *BatchWriter) fetchExisting(ctx context.Context, candidates []Candle) (map[string]ExistingCandle, error) {
	identities := make([]Identity, 0, len(candidates))
	seen := map[string]bool{}
	for _, candidate := range candidates {
		identity := candidate.Identity()
		key := identityKey(identity)
		if seen[key] {
			continue
		}
		seen[key] = true
		identities = append(identities, identity)
	}
	args := make([]any, 0, len(identities)*5)
	placeholders := make([]string, 0, len(identities))
	for index, identity := range identities {
		base := index*5 + 1
		placeholders = append(placeholders, fmt.Sprintf("($%d, $%d, $%d, $%d, $%d)", base, base+1, base+2, base+3, base+4))
		args = append(args, identity.WorkspaceID, identity.SymbolID, identity.SourceID, identity.Timeframe, identity.Timestamp)
	}
	query := `
select id, workspace_id, symbol_id, source_id, timeframe, timestamp, open::text, high::text, low::text, close::text, volume::text, is_final, created_at
from candles
where (workspace_id, symbol_id, source_id, timeframe, timestamp) in (` + strings.Join(placeholders, ",") + `)
`
	rows, err := w.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	existing := map[string]ExistingCandle{}
	for rows.Next() {
		var id uuid.UUID
		var workspaceID uuid.UUID
		var symbolID uuid.UUID
		var sourceID uuid.UUID
		var timeframe string
		var timestamp time.Time
		var openText string
		var highText string
		var lowText string
		var closeText string
		var volumeText *string
		var isFinal bool
		var createdAt time.Time
		if err := rows.Scan(&id, &workspaceID, &symbolID, &sourceID, &timeframe, &timestamp, &openText, &highText, &lowText, &closeText, &volumeText, &isFinal, &createdAt); err != nil {
			return nil, err
		}
		openValue, _ := decimal.NewFromString(openText)
		highValue, _ := decimal.NewFromString(highText)
		lowValue, _ := decimal.NewFromString(lowText)
		closeValue, _ := decimal.NewFromString(closeText)
		var volumeValue *decimal.Decimal
		if volumeText != nil {
			parsed, _ := decimal.NewFromString(*volumeText)
			volumeValue = &parsed
		}
		candle := Candle{
			WorkspaceID: workspaceID,
			SymbolID:    symbolID,
			SourceID:    sourceID,
			Timeframe:   timeframe,
			Timestamp:   timestamp.UTC(),
			Open:        openValue,
			High:        highValue,
			Low:         lowValue,
			Close:       closeValue,
			Volume:      volumeValue,
			IsFinal:     isFinal,
		}
		existing[identityKey(candle.Identity())] = ExistingCandle{ID: id, Candle: candle, IsFinal: isFinal, Exists: true, CreatedAt: createdAt}
	}
	return existing, rows.Err()
}

func insertCandle(batch *pgx.Batch, id uuid.UUID, candle Candle) {
	batch.Queue(`
insert into candles (
	id, workspace_id, symbol_id, source_id, timeframe, timestamp, open, high, low, close,
	volume, is_final, created_at, updated_at
) values ($1, $2, $3, $4, $5, $6, $7::numeric, $8::numeric, $9::numeric, $10::numeric, $11::numeric, $12, now(), now())
`, id, candle.WorkspaceID, candle.SymbolID, candle.SourceID, candle.Timeframe, candle.Timestamp, candle.Open.String(), candle.High.String(), candle.Low.String(), candle.Close.String(), decimalPointerString(candle.Volume), candle.IsFinal)
}

func updateCandle(batch *pgx.Batch, id uuid.UUID, candle Candle) {
	batch.Queue(`
update candles
set open = $2::numeric,
	high = $3::numeric,
	low = $4::numeric,
	close = $5::numeric,
	volume = $6::numeric,
	is_final = $7,
	updated_at = now()
where id = $1
`, id, candle.Open.String(), candle.High.String(), candle.Low.String(), candle.Close.String(), decimalPointerString(candle.Volume), candle.IsFinal)
}

func (w *BatchWriter) recordConflicts(ctx context.Context, performanceRunID uuid.UUID, conflicts []Conflict) error {
	batch := &pgx.Batch{}
	for _, conflict := range conflicts {
		batch.Queue(`
insert into candle_ingestion_conflicts (
	id, workspace_id, performance_run_id, symbol_id, source_id, timeframe, timestamp,
	conflict_type, existing_candle_json, incoming_candle_json, resolution, created_at
) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now())
`, uuid.New(), conflict.Candle.WorkspaceID, performanceRunID, conflict.Candle.SymbolID, conflict.Candle.SourceID, conflict.Candle.Timeframe, conflict.Candle.Timestamp, conflict.Type, conflict.Existing, conflict.Incoming, conflict.Resolution)
	}
	results := w.pool.SendBatch(ctx, batch)
	for i := 0; i < batch.Len(); i++ {
		if _, err := results.Exec(); err != nil {
			_ = results.Close()
			return err
		}
	}
	return results.Close()
}

func valuesDiffer(existing Candle, incoming Candle) bool {
	if !existing.Open.Equal(incoming.Open) || !existing.High.Equal(incoming.High) || !existing.Low.Equal(incoming.Low) || !existing.Close.Equal(incoming.Close) {
		return true
	}
	if existing.Volume == nil || incoming.Volume == nil {
		return existing.Volume != nil || incoming.Volume != nil
	}
	return !existing.Volume.Equal(*incoming.Volume)
}

func buildConflict(conflictType string, resolution string, existing Candle, incoming Candle) Conflict {
	return Conflict{
		Type:       conflictType,
		Resolution: resolution,
		Existing:   SerializeCandle(existing),
		Incoming:   SerializeCandle(incoming),
		Candle:     incoming,
	}
}

func identityKey(identity Identity) string {
	return identity.WorkspaceID.String() + "|" + identity.SymbolID.String() + "|" + identity.SourceID.String() + "|" + identity.Timeframe + "|" + identity.Timestamp.UTC().Format(time.RFC3339Nano)
}

func decimalPointerString(value *decimal.Decimal) *string {
	if value == nil {
		return nil
	}
	text := value.String()
	return &text
}

func JSONString(value any) string {
	payload, err := json.Marshal(value)
	if err != nil {
		return "{}"
	}
	return string(payload)
}
