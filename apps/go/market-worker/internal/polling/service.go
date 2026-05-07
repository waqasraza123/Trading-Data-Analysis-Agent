package polling

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/health"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/jobs"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/providers"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/safety"
)

type Service struct {
	pool            *pgxpool.Pool
	capabilities    workerdb.Capabilities
	repository      *jobs.Repository
	writer          *candles.BatchWriter
	validator       *candles.SymbolSourceValidator
	providers       *providers.Registry
	providerGate    *ProviderGate
	providerCircuit *ProviderCircuitBreaker
	maxCandles      int
	timeout         time.Duration
	binanceBaseURL  string
	metrics         *health.Metrics
	logger          *slog.Logger
}

func NewService(pool *pgxpool.Pool, capabilities workerdb.Capabilities, registry *providers.Registry, maxCandles int, timeout time.Duration, binanceBaseURL string, providerMaxConcurrency int, providerMinInterval time.Duration, providerFailureThreshold int, providerCooldown time.Duration, metrics *health.Metrics, logger *slog.Logger) *Service {
	return &Service{
		pool:            pool,
		capabilities:    capabilities,
		repository:      jobs.NewRepository(pool, capabilities),
		writer:          candles.NewBatchWriter(pool, capabilities),
		validator:       candles.NewSymbolSourceValidator(pool),
		providers:       registry,
		providerGate:    NewProviderGate(providerMaxConcurrency, providerMinInterval),
		providerCircuit: NewProviderCircuitBreaker(providerFailureThreshold, providerCooldown),
		maxCandles:      maxCandles,
		timeout:         timeout,
		binanceBaseURL:  binanceBaseURL,
		metrics:         metrics,
		logger:          logger,
	}
}

func (s *Service) Process(ctx context.Context, request jobs.PollingRequest) (Result, error) {
	if request.ID != nil && request.Provider == "" {
		loaded, err := s.repository.LoadProviderPollingRequest(ctx, *request.ID)
		if err != nil {
			return Result{}, err
		}
		request = loaded
	}
	if safety.MetadataContainsSecret(request.Metadata) {
		return Result{}, errors.New("provider_polling_secret_metadata_rejected")
	}
	if request.Limit <= 0 || request.Limit > s.maxCandles {
		request.Limit = s.maxCandles
	}
	provider, ok := s.providers.Get(request.Provider)
	if !ok {
		return Result{}, fmt.Errorf("provider_not_supported")
	}
	state, err := s.validator.Load(ctx, request.WorkspaceID, request.SymbolID, request.SourceID)
	if err != nil {
		return Result{}, fmt.Errorf("symbol_or_source_not_found: %w", err)
	}
	run, err := s.writer.StartRun(ctx, request.WorkspaceID, request.SourceID, request.SymbolID, request.Timeframe, request.ID)
	if err != nil {
		return Result{}, err
	}
	circuitState, circuitAllowed := s.providerCircuit.Allow(request.Provider)
	if !circuitAllowed {
		circuitErr := providers.NewProviderError("provider_circuit_open", "Provider temporarily paused after repeated failures")
		_ = s.writer.FinishRun(ctx, run, candles.WriteCounts{}, true)
		if request.ID != nil && s.capabilities.HasTable("provider_polling_requests") {
			_ = s.repository.FailProviderPollingRequest(ctx, *request.ID, circuitErr.Code, circuitErr.Error())
		}
		if s.metrics != nil {
			s.metrics.RecordProviderCircuitBlocked()
		}
		_ = s.recordProviderHealth(ctx, request, Result{
			Provider: request.Provider,
			ProviderMetadata: map[string]any{
				"circuitOpenUntil": circuitState.OpenUntil,
			},
		}, circuitErr)
		return Result{}, circuitErr
	}
	releaseProvider, providerWait, gateErr := s.providerGate.Wait(ctx, request.Provider)
	if gateErr != nil {
		_ = s.writer.FinishRun(ctx, run, candles.WriteCounts{}, true)
		_ = s.recordProviderHealth(ctx, request, Result{Provider: request.Provider}, gateErr)
		return Result{}, gateErr
	}
	if s.metrics != nil {
		s.metrics.RecordProviderGateWait(providerWait)
	}
	result, fetchErr := func() (providers.FetchCandlesResult, error) {
		defer releaseProvider()
		return provider.FetchCandles(ctx, providers.FetchCandlesRequest{
			WorkspaceID:    request.WorkspaceID,
			SourceID:       request.SourceID,
			SymbolID:       request.SymbolID,
			Provider:       request.Provider,
			ProviderSymbol: request.ProviderSymbol,
			Timeframe:      request.Timeframe,
			StartTime:      request.StartTime,
			EndTime:        request.EndTime,
			Limit:          request.Limit,
			Timeout:        s.timeout,
			BaseURL:        s.binanceBaseURL,
			Metadata:       request.Metadata,
		})
	}()
	if fetchErr != nil {
		if s.providerCircuit.RecordFailure(request.Provider) && s.metrics != nil {
			s.metrics.RecordProviderCircuitOpened()
		}
		_ = s.writer.FinishRun(ctx, run, candles.WriteCounts{}, true)
		if request.ID != nil && s.capabilities.HasTable("provider_polling_requests") {
			_ = s.repository.FailProviderPollingRequest(ctx, *request.ID, errorCode(fetchErr), fetchErr.Error())
		}
		_ = s.recordProviderHealth(ctx, request, Result{Provider: request.Provider}, fetchErr)
		return Result{}, fetchErr
	}
	s.providerCircuit.RecordSuccess(request.Provider)
	for _, warning := range result.Warnings {
		if request.ID != nil {
			_ = s.repository.AddProviderPollingError(ctx, *request.ID, request.WorkspaceID, warning.Code, warning.Message, warning.RawItem)
		}
	}
	for _, providerError := range result.Errors {
		if request.ID != nil {
			_ = s.repository.AddProviderPollingError(ctx, *request.ID, request.WorkspaceID, providerError.Code, providerError.Message, providerError.RawItem)
		}
	}
	normalized, normalizationIssues := NormalizeProviderCandles(result.Candles, request.WorkspaceID, request.SourceID, request.SymbolID, request.Timeframe, request.ID)
	validation := candles.ValidateBatch(normalized, state)
	invalid := append(normalizationIssues, validation.Invalid...)
	for _, invalidItem := range invalid {
		if request.ID != nil {
			_ = s.repository.AddProviderPollingError(ctx, *request.ID, request.WorkspaceID, invalidItem.Code, invalidItem.Message, invalidItem.RawItem)
		}
	}
	writeCounts, conflicts, writeErr := s.writer.Write(ctx, run, validation.Valid)
	writeCounts.Received = len(result.Candles)
	writeCounts.Valid = len(validation.Valid)
	writeCounts.Invalid = len(invalid)
	if writeErr != nil {
		writeCounts.Failed += len(validation.Valid)
		_ = s.writer.FinishRun(ctx, run, writeCounts, true)
		if request.ID != nil {
			_ = s.repository.FailProviderPollingRequest(ctx, *request.ID, "candle_write_failed", writeErr.Error())
		}
		_ = s.recordProviderHealth(ctx, request, Result{Provider: request.Provider}, writeErr)
		return Result{}, writeErr
	}
	if len(invalid) > 0 {
		fallback := fallbackCandle(request)
		if len(normalized) > 0 {
			fallback = normalized[0]
		}
		_ = s.writer.RecordInvalidConflicts(ctx, run, invalid, fallback)
	}
	if request.ID != nil {
		for _, conflict := range conflicts {
			if conflict.Type == "final_conflict" {
				_ = s.repository.AddProviderPollingError(ctx, *request.ID, request.WorkspaceID, "conflicting_final_candle", "Existing final candle conflicts with incoming final candle", conflict.Incoming)
			}
		}
	}
	if err := s.writer.FinishRun(ctx, run, writeCounts, false); err != nil {
		return Result{}, err
	}
	stored := writeCounts.Inserted + writeCounts.Updated
	skipped := writeCounts.DuplicateSkipped + writeCounts.Conflicted + writeCounts.Invalid + writeCounts.Failed
	metadata := mergeMetadata(result.ProviderMetadata, ProviderMessagesToMetadata(result.Warnings, result.Errors))
	metadata["recordedErrorCount"] = len(invalid) + len(result.Errors) + len(result.Warnings)
	final := Result{
		WorkspaceID:      request.WorkspaceID,
		Provider:         request.Provider,
		ProviderSymbol:   request.ProviderSymbol,
		Timeframe:        request.Timeframe,
		Received:         len(result.Candles),
		Stored:           stored,
		Skipped:          skipped,
		Conflicted:       writeCounts.Conflicted,
		Invalid:          len(invalid),
		Warnings:         len(result.Warnings),
		ProviderErrors:   len(result.Errors),
		CompletedAt:      time.Now().UTC(),
		Counts:           writeCounts,
		ProviderMetadata: metadata,
	}
	if request.ID != nil && s.capabilities.HasTable("provider_polling_requests") {
		warnings := skipped > 0 || len(result.Warnings) > 0 || len(result.Errors) > 0
		if err := s.repository.CompleteProviderPollingRequest(ctx, *request.ID, final.Received, final.Stored, final.Skipped, metadata, warnings); err != nil {
			return final, err
		}
	}
	if err := s.recordProviderHealth(ctx, request, final, nil); err != nil {
		s.logger.Warn("provider_health_snapshot_failed", "error", err)
	}
	return final, nil
}

func (s *Service) recordProviderHealth(ctx context.Context, request jobs.PollingRequest, result Result, cause error) error {
	if !s.capabilities.HasTable("provider_health_snapshots") || !s.capabilities.HasOptionalColumns("provider_health_snapshots") {
		return nil
	}
	latestFinal, staleSeconds, freshness := s.latestFinalFreshness(ctx, request)
	status := "healthy"
	summary := "Provider polling completed"
	consecutiveFailures := 0
	var latestSuccessful *time.Time
	var latestFailed *time.Time
	now := time.Now().UTC()
	if cause != nil {
		status = "failing"
		freshness = "unknown"
		summary = cause.Error()
		consecutiveFailures = 1
		latestFailed = &now
	} else {
		latestSuccessful = &now
		if result.Stored == 0 {
			status = "stale"
			freshness = "no_data"
			summary = "Provider polling completed but stored no candles"
		} else if result.Skipped > 0 || result.Warnings > 0 || result.ProviderErrors > 0 {
			status = "degraded"
			summary = "Provider polling completed with warnings"
		}
	}
	metadata := map[string]any{
		"worker":         "go_market_worker",
		"providerSymbol": request.ProviderSymbol,
		"stored":         result.Stored,
		"skipped":        result.Skipped,
		"received":       result.Received,
	}
	for key, value := range result.ProviderMetadata {
		if !safety.KeyContainsSecret(key) {
			metadata[key] = value
		}
	}
	_, err := s.pool.Exec(ctx, `
insert into provider_health_snapshots (
	id, workspace_id, source_id, provider, symbol_id, timeframe, status, freshness_label,
	latest_final_candle_time, latest_successful_poll_at, latest_failed_poll_at,
	consecutive_failure_count, missing_candle_count, stale_seconds, summary, metadata_json,
	created_at, updated_at
) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 0, $13, left($14, 2000), $15, now(), now())
	`, uuid.New(), request.WorkspaceID, request.SourceID, request.Provider, request.SymbolID, request.Timeframe, status, freshness, latestFinal, latestSuccessful, latestFailed, consecutiveFailures, staleSeconds, summary, metadata)
	return err
}

func (s *Service) latestFinalFreshness(ctx context.Context, request jobs.PollingRequest) (*time.Time, *int, string) {
	var latest *time.Time
	_ = s.pool.QueryRow(ctx, `
select max(timestamp)
from candles
where workspace_id = $1 and source_id = $2 and symbol_id = $3 and timeframe = $4 and is_final = true
`, request.WorkspaceID, request.SourceID, request.SymbolID, request.Timeframe).Scan(&latest)
	if latest == nil {
		return nil, nil, "no_data"
	}
	age := int(time.Since(latest.UTC()).Seconds())
	freshness := "fresh"
	timeframe, err := candles.ParseTimeframe(request.Timeframe)
	if err != nil {
		freshness = "unknown"
	} else if int64(age) > timeframe.Seconds*4 {
		freshness = "stale"
	} else if int64(age) > timeframe.Seconds*2 {
		freshness = "delayed"
	}
	return latest, &age, freshness
}

func fallbackCandle(request jobs.PollingRequest) candles.Candle {
	return candles.Candle{
		WorkspaceID: request.WorkspaceID,
		SourceID:    request.SourceID,
		SymbolID:    request.SymbolID,
		Timeframe:   request.Timeframe,
		Timestamp:   time.Now().UTC().Truncate(time.Minute),
		IsFinal:     true,
	}
}

func mergeMetadata(left map[string]any, right map[string]any) map[string]any {
	merged := map[string]any{}
	for key, value := range left {
		if !safety.KeyContainsSecret(key) {
			merged[key] = value
		}
	}
	for key, value := range right {
		merged[key] = value
	}
	return merged
}

func errorCode(err error) string {
	var providerErr providers.ProviderError
	if errors.As(err, &providerErr) {
		return providerErr.Code
	}
	return "provider_polling_failed"
}
