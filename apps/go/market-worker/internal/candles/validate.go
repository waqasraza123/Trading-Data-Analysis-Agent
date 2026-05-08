package candles

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/shopspring/decimal"
)

type SymbolSourceValidator struct {
	pool *pgxpool.Pool
}

type SymbolSourceState struct {
	SymbolID         uuid.UUID
	SourceID         uuid.UUID
	WorkspaceID      uuid.UUID
	SymbolActive     bool
	SourceActive     bool
	SourceType       string
	SourceProvider   string
	SourceWorkspace  uuid.UUID
}

func NewSymbolSourceValidator(pool *pgxpool.Pool) *SymbolSourceValidator {
	return &SymbolSourceValidator{pool: pool}
}

func (v *SymbolSourceValidator) Load(ctx context.Context, workspaceID uuid.UUID, symbolID uuid.UUID, sourceID uuid.UUID) (SymbolSourceState, error) {
	state := SymbolSourceState{}
	row := v.pool.QueryRow(ctx, `
select s.id, ds.id, ds.workspace_id, s.is_active, ds.status = 'active', ds.source_type, ds.provider
from symbols s
cross join data_sources ds
where s.id = $1 and ds.id = $2
`, symbolID, sourceID)
	if err := row.Scan(&state.SymbolID, &state.SourceID, &state.SourceWorkspace, &state.SymbolActive, &state.SourceActive, &state.SourceType, &state.SourceProvider); err != nil {
		return SymbolSourceState{}, err
	}
	state.WorkspaceID = workspaceID
	return state, nil
}

func ValidateBatch(candidates []Candle, state SymbolSourceState) ValidationResult {
	result := ValidationResult{Valid: make([]Candle, 0, len(candidates))}
	for _, candidate := range candidates {
		if issue := Validate(candidate, state); issue != nil {
			result.Invalid = append(result.Invalid, *issue)
			continue
		}
		result.Valid = append(result.Valid, candidate)
	}
	return result
}

func Validate(candidate Candle, state SymbolSourceState) *ValidationIssue {
	timeframe, err := ParseTimeframe(candidate.Timeframe)
	if err != nil {
		return issue("unsupported_timeframe", "Unsupported timeframe", candidate.RawItem)
	}
	if candidate.WorkspaceID != state.SourceWorkspace {
		return issue("missing_source", "Data source does not belong to workspace", candidate.RawItem)
	}
	if !state.SymbolActive {
		return issue("missing_symbol", "Symbol is missing or inactive", candidate.RawItem)
	}
	if !state.SourceActive || (state.SourceType != "api_polling" && state.SourceType != "websocket_live") {
		return issue("missing_source", "Data source is missing, inactive, or unsupported", candidate.RawItem)
	}
	if !TimestampAligns(candidate.Timestamp, timeframe) {
		return issue("timestamp_misalignment", "Timestamp does not align with timeframe", candidate.RawItem)
	}
	if candidate.Open.LessThanOrEqual(decimal.Zero) {
		return issue("invalid_open", "Open must be positive", candidate.RawItem)
	}
	if candidate.High.LessThanOrEqual(decimal.Zero) {
		return issue("invalid_high", "High must be positive", candidate.RawItem)
	}
	if candidate.Low.LessThanOrEqual(decimal.Zero) {
		return issue("invalid_low", "Low must be positive", candidate.RawItem)
	}
	if candidate.Close.LessThanOrEqual(decimal.Zero) {
		return issue("invalid_close", "Close must be positive", candidate.RawItem)
	}
	if candidate.Volume != nil && candidate.Volume.LessThan(decimal.Zero) {
		return issue("invalid_volume", "Volume must be non-negative", candidate.RawItem)
	}
	if candidate.High.LessThan(candidate.Open) || candidate.High.LessThan(candidate.Close) || candidate.High.LessThan(candidate.Low) || candidate.Low.GreaterThan(candidate.Open) || candidate.Low.GreaterThan(candidate.Close) {
		return issue("invalid_ohlc_relationship", "OHLC relationship is invalid", candidate.RawItem)
	}
	return nil
}

func issue(code string, message string, raw map[string]any) *ValidationIssue {
	return &ValidationIssue{Code: code, Message: message, RawItem: raw}
}

func ParseDecimal(value string, field string) (decimal.Decimal, error) {
	parsed, err := decimal.NewFromString(value)
	if err != nil {
		return decimal.Decimal{}, fmt.Errorf("invalid_%s", field)
	}
	return parsed, nil
}
