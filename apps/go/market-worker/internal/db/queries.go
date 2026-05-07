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
	if len(missing) > 0 {
		return fmt.Errorf("required database capabilities missing: %v", missing)
	}
	return nil
}

func (c Capabilities) OptionalTables() []string {
	tables := slices.Clone(ExpectedTables)
	slices.Sort(tables)
	return tables
}
