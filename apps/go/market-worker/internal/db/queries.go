package db

import (
	"context"
	"fmt"
	"slices"

	"github.com/jackc/pgx/v5/pgxpool"
)

var ExpectedTables = []string{
	"job_queue_items",
	"job_queue_events",
	"provider_polling_requests",
	"live_feed_subscriptions",
	"live_feed_events",
	"provider_polling_errors",
	"candles",
	"symbols",
	"data_sources",
	"provider_health_snapshots",
	"candle_ingestion_performance_runs",
	"candle_ingestion_conflicts",
	"runtime_worker_definitions",
	"runtime_worker_instances",
	"engine_execution_records",
}

var RequiredColumns = map[string][]string{
	"candles": {
		"id",
		"workspace_id",
		"symbol_id",
		"source_id",
		"timeframe",
		"timestamp",
		"open",
		"high",
		"low",
		"close",
		"volume",
		"is_final",
		"created_at",
		"updated_at",
	},
	"symbols": {
		"id",
		"is_active",
	},
	"data_sources": {
		"id",
		"workspace_id",
		"status",
		"source_type",
		"provider",
	},
	"job_queue_items": {
		"id",
		"workspace_id",
		"queue_name",
		"job_type",
		"status",
		"attempts",
		"max_attempts",
		"payload_json",
		"available_at",
		"locked_by",
		"locked_until",
		"priority",
		"started_at",
		"error_code",
		"error_message",
		"result_json",
		"completed_at",
		"updated_at",
	},
	"provider_polling_requests": {
		"id",
		"workspace_id",
		"source_id",
		"symbol_id",
		"provider",
		"provider_symbol",
		"timeframe",
		"status",
		"start_time",
		"end_time",
		"limit",
		"request_metadata_json",
		"response_metadata_json",
		"error_message",
		"started_at",
		"completed_at",
		"created_at",
		"updated_at",
		"received_candle_count",
		"stored_candle_count",
		"skipped_candle_count",
	},
}

var OptionalColumns = map[string][]string{
	"job_queue_events": {
		"id",
		"workspace_id",
		"job_id",
		"event_type",
		"message",
		"metadata_json",
		"created_at",
	},
	"provider_polling_errors": {
		"id",
		"workspace_id",
		"polling_request_id",
		"error_code",
		"error_message",
		"raw_item_json",
		"created_at",
	},
	"provider_health_snapshots": {
		"id",
		"workspace_id",
		"source_id",
		"provider",
		"symbol_id",
		"timeframe",
		"status",
		"freshness_label",
		"latest_final_candle_time",
		"latest_successful_poll_at",
		"latest_failed_poll_at",
		"consecutive_failure_count",
		"missing_candle_count",
		"stale_seconds",
		"summary",
		"metadata_json",
		"created_at",
		"updated_at",
	},
	"candle_ingestion_performance_runs": {
		"id",
		"workspace_id",
		"provider_polling_request_id",
		"source_id",
		"symbol_id",
		"timeframe",
		"status",
		"ingestion_mode",
		"diagnostics_json",
		"rows_received",
		"rows_validated",
		"rows_inserted",
		"rows_updated",
		"rows_skipped_duplicate",
		"rows_conflicted",
		"rows_failed",
		"batch_count",
		"elapsed_ms",
		"created_at",
		"updated_at",
	},
	"candle_ingestion_conflicts": {
		"id",
		"workspace_id",
		"performance_run_id",
		"symbol_id",
		"source_id",
		"timeframe",
		"timestamp",
		"conflict_type",
		"existing_candle_json",
		"incoming_candle_json",
		"resolution",
		"created_at",
	},
	"runtime_worker_definitions": {
		"id",
		"key",
		"name",
		"description",
		"worker_type",
		"status",
		"command",
		"required_settings_json",
		"optional_settings_json",
		"safety_notes_json",
		"metadata_json",
		"created_at",
		"updated_at",
	},
	"live_feed_subscriptions": {
		"id",
		"workspace_id",
		"source_id",
		"symbol_id",
		"timeframe",
		"provider",
		"status",
		"last_message_at",
		"last_final_candle_at",
		"last_error",
		"config_json",
		"worker_id",
		"lease_expires_at",
		"created_at",
		"updated_at",
	},
	"live_feed_events": {
		"id",
		"workspace_id",
		"source_id",
		"subscription_id",
		"provider",
		"event_type",
		"received_at",
		"provider_timestamp",
		"payload_json",
		"processing_status",
		"error_message",
		"created_at",
	},
	"runtime_worker_instances": {
		"id",
		"worker_definition_key",
		"worker_id",
		"status",
		"host_name",
		"process_id",
		"started_at",
		"last_heartbeat_at",
		"stopped_at",
		"heartbeat_payload_json",
		"metadata_json",
		"created_at",
		"updated_at",
	},
}

type Capabilities struct {
	Tables  map[string]bool           `json:"tables"`
	Columns map[string]map[string]bool `json:"columns"`
}

func DetectCapabilities(ctx context.Context, pool *pgxpool.Pool) (Capabilities, error) {
	capabilities := Capabilities{
		Tables:  make(map[string]bool, len(ExpectedTables)),
		Columns: make(map[string]map[string]bool, len(ExpectedTables)),
	}
	rows, err := pool.Query(ctx, `
select table_name, column_name
from information_schema.columns
where table_schema = 'public' and table_name = any($1)
order by table_name, ordinal_position
`, ExpectedTables)
	if err != nil {
		return Capabilities{}, err
	}
	defer rows.Close()
	for rows.Next() {
		var tableName string
		var columnName string
		if err := rows.Scan(&tableName, &columnName); err != nil {
			return Capabilities{}, err
		}
		capabilities.Tables[tableName] = true
		if capabilities.Columns[tableName] == nil {
			capabilities.Columns[tableName] = map[string]bool{}
		}
		capabilities.Columns[tableName][columnName] = true
	}
	if err := rows.Err(); err != nil {
		return Capabilities{}, err
	}
	for _, table := range ExpectedTables {
		if _, ok := capabilities.Tables[table]; !ok {
			capabilities.Tables[table] = false
		}
		if capabilities.Columns[table] == nil {
			capabilities.Columns[table] = map[string]bool{}
		}
	}
	return capabilities, nil
}

func (c Capabilities) HasTable(tableName string) bool {
	return c.Tables[tableName]
}

func (c Capabilities) HasColumn(tableName string, columnName string) bool {
	return c.Columns[tableName] != nil && c.Columns[tableName][columnName]
}

func (c Capabilities) HasColumns(tableName string, columnNames []string) bool {
	return len(c.MissingColumns(tableName, columnNames)) == 0
}

func (c Capabilities) HasOptionalColumns(tableName string) bool {
	return c.HasColumns(tableName, OptionalColumns[tableName])
}

func (c Capabilities) MissingColumns(tableName string, columnNames []string) []string {
	missing := make([]string, 0)
	for _, columnName := range columnNames {
		if !c.HasColumn(tableName, columnName) {
			missing = append(missing, columnName)
		}
	}
	slices.Sort(missing)
	return missing
}

func (c Capabilities) Validate(mode string) error {
	missing := make([]string, 0)
	for _, tableName := range []string{"candles", "symbols", "data_sources"} {
		if !c.HasTable(tableName) {
			missing = append(missing, tableName)
		}
	}
	if mode == "provider_polling_requests" {
		if !c.HasTable("provider_polling_requests") {
			missing = append(missing, "provider_polling_requests")
		}
	} else if !c.HasTable("job_queue_items") && !c.HasTable("provider_polling_requests") {
		missing = append(missing, "job_queue_items or provider_polling_requests")
	}
	for tableName, columns := range c.RequiredColumnProblems(mode) {
		for _, columnName := range columns {
			missing = append(missing, tableName+"."+columnName)
		}
	}
	slices.Sort(missing)
	if len(missing) > 0 {
		return fmt.Errorf("required database capabilities missing: %v", missing)
	}
	return nil
}

func (c Capabilities) RequiredColumnProblems(mode string) map[string][]string {
	tables := []string{"candles", "symbols", "data_sources"}
	if mode == "provider_polling_requests" {
		tables = append(tables, "provider_polling_requests")
	} else {
		if c.HasTable("job_queue_items") {
			tables = append(tables, "job_queue_items")
		}
		if c.HasTable("provider_polling_requests") {
			tables = append(tables, "provider_polling_requests")
		}
	}
	return c.columnProblems(tables, RequiredColumns)
}

func (c Capabilities) OptionalColumnProblems() map[string][]string {
	tables := make([]string, 0, len(OptionalColumns))
	for tableName := range OptionalColumns {
		if c.HasTable(tableName) {
			tables = append(tables, tableName)
		}
	}
	slices.Sort(tables)
	return c.columnProblems(tables, OptionalColumns)
}

func (c Capabilities) OptionalTables() []string {
	tables := slices.Clone(ExpectedTables)
	slices.Sort(tables)
	return tables
}

func (c Capabilities) columnProblems(tableNames []string, contract map[string][]string) map[string][]string {
	problems := map[string][]string{}
	for _, tableName := range tableNames {
		if !c.HasTable(tableName) {
			continue
		}
		missing := c.MissingColumns(tableName, contract[tableName])
		if len(missing) > 0 {
			problems[tableName] = missing
		}
	}
	return problems
}
