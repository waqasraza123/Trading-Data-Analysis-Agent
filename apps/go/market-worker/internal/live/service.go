package live

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"math/rand"
	"net"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/candles"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/config"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
	"github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/health"
)

var errLiveSubscriptionStopped = errors.New("live subscription stopped")

type Service struct {
	cfg       config.Config
	repo      *Repository
	validator *candles.SymbolSourceValidator
	writer    *candles.BatchWriter
	logger    *slog.Logger
	metrics   *health.Metrics
}

func NewService(pool *pgxpool.Pool, capabilities db.Capabilities, cfg config.Config, logger *slog.Logger, metrics *health.Metrics) *Service {
	return &Service{
		cfg:       cfg,
		repo:      NewRepository(pool, capabilities, cfg.LiveStreamStaleAfter),
		validator: candles.NewSymbolSourceValidator(pool),
		writer:    candles.NewBatchWriter(pool, capabilities),
		logger:    logger,
		metrics:   metrics,
	}
}

func (s *Service) Enabled() bool {
	return s.cfg.EnableLiveStream && s.cfg.EnableLiveBinance && s.cfg.Mode == "jobs"
}

func (s *Service) RuntimeCandidates(ctx context.Context, limit int) ([]Subscription, error) {
	if !s.Enabled() {
		return nil, nil
	}
	return s.repo.RuntimeCandidates(ctx, limit)
}

func (s *Service) MarkStaleCandidates(ctx context.Context) (int, error) {
	if !s.Enabled() {
		return 0, nil
	}
	return s.repo.MarkStaleCandidates(ctx, s.cfg.LiveStreamStaleAfter)
}

func (s *Service) AcquireLease(ctx context.Context, subscription Subscription) bool {
	if !s.Enabled() {
		return false
	}
	expiresAt := time.Now().UTC().Add(s.cfg.LiveStreamLeaseDuration)
	return s.repo.AcquireLease(ctx, subscription.ID, s.cfg.WorkerID, expiresAt)
}

func (s *Service) RefreshLease(ctx context.Context, subscription Subscription) bool {
	if !s.Enabled() {
		return false
	}
	expiresAt := time.Now().UTC().Add(s.cfg.LiveStreamLeaseDuration)
	return s.repo.RefreshLease(ctx, subscription.ID, s.cfg.WorkerID, expiresAt)
}

func (s *Service) ReleaseLease(ctx context.Context, subscription Subscription) bool {
	if !s.Enabled() {
		return false
	}
	return s.repo.ReleaseLease(ctx, subscription.ID, s.cfg.WorkerID)
}

func (s *Service) Process(ctx context.Context, subscription Subscription) error {
	if !s.Enabled() {
		return nil
	}
	provider, err := s.resolveProviderSymbol(subscription)
	if err != nil {
		return err
	}
	timeframe, err := candles.ParseTimeframe(subscription.Timeframe)
	if err != nil {
		return err
	}
	state, err := s.validator.Load(ctx, subscription.WorkspaceID, subscription.SymbolID, subscription.SourceID)
	if err != nil {
		return err
	}
	readTimeout := s.cfg.LiveStreamReadTimeout
	if readTimeout <= 0 {
		readTimeout = 30 * time.Second
	}
	reconnectAttempts := 0
	for {
		if !isLiveSubscriptionActive(subscription.Status) {
			return nil
		}
		streamURL := strings.TrimRight(s.cfg.BinanceLiveWebSocketBaseURL, "/")
		conn, err := websocket.DefaultDialer.Dial(streamURL, nil)
		if err != nil {
			reconnectAttempts++
			exceeded, err := s.reconnectBudgetExceeded(ctx, subscription, reconnectAttempts)
			if err != nil {
				return err
			}
			if exceeded {
				return nil
			}
			reconnectDelay := s.liveReconnectDelay(reconnectAttempts - 1)
			s.logger.Warn("live_subscription_connect_failed", "subscriptionId", subscription.ID.String(), "error", err)
			if s.metrics != nil {
				s.metrics.RecordLiveReconnect()
			}
			s.logger.Info("live_subscription_reconnect_wait", "subscriptionId", subscription.ID.String(), "attempt", reconnectAttempts, "delaySeconds", int(reconnectDelay.Seconds()))
			if err := s.waitForLiveReconnect(ctx, reconnectDelay); err != nil {
				return err
			}
			continue
		}
		if err := s.subscribeBinance(conn, provider, subscription.Timeframe); err != nil {
			_ = conn.Close()
			reconnectAttempts++
			exceeded, err := s.reconnectBudgetExceeded(ctx, subscription, reconnectAttempts)
			if err != nil {
				return err
			}
			if exceeded {
				return nil
			}
			reconnectDelay := s.liveReconnectDelay(reconnectAttempts - 1)
			s.logger.Warn("live_subscription_subscribe_failed", "subscriptionId", subscription.ID.String(), "error", err)
			if s.metrics != nil {
				s.metrics.RecordLiveReconnect()
			}
			s.logger.Info("live_subscription_reconnect_wait", "subscriptionId", subscription.ID.String(), "attempt", reconnectAttempts, "delaySeconds", int(reconnectDelay.Seconds()))
			if err := s.waitForLiveReconnect(ctx, reconnectDelay); err != nil {
				return err
			}
			continue
		}
		reconnectAttempts = 0
		streamErr := s.consume(ctx, conn, subscription, provider, timeframe, readTimeout, state)
		_ = conn.Close()
		if errors.Is(streamErr, errLiveSubscriptionStopped) {
			return nil
		}
		if streamErr == nil {
			return nil
		}
		reconnectAttempts++
		exceeded, err := s.reconnectBudgetExceeded(ctx, subscription, reconnectAttempts)
		if err != nil {
			return err
		}
		if exceeded {
			return nil
		}
		if ctx.Err() != nil {
			return ctx.Err()
		}
		reconnectDelay := s.liveReconnectDelay(reconnectAttempts - 1)
		if s.metrics != nil {
			s.metrics.RecordLiveReconnect()
			if isLiveStreamReadTimeout(streamErr) {
				s.metrics.RecordLiveReconnectReadTimeout()
			}
		}
		if isLiveStreamReadTimeout(streamErr) {
			s.logger.Warn("live_subscription_stream_read_timeout", "subscriptionId", subscription.ID.String(), "error", streamErr)
		} else {
			s.logger.Warn("live_subscription_stream_reconnect", "subscriptionId", subscription.ID.String(), "error", streamErr)
		}
		s.logger.Info("live_subscription_reconnect_wait", "subscriptionId", subscription.ID.String(), "attempt", reconnectAttempts, "delaySeconds", int(reconnectDelay.Seconds()))
		if err := s.waitForLiveReconnect(ctx, reconnectDelay); err != nil {
			return err
		}
	}
}

func (s *Service) liveReconnectDelay(attempt int) time.Duration {
	delay := s.cfg.LiveStreamReconnectDelay
	maxDelay := s.cfg.LiveStreamMaxReconnectDelay
	if delay <= 0 {
		delay = 1 * time.Second
	}
	if maxDelay <= 0 || maxDelay < delay {
		maxDelay = delay
	}
	for attempt > 0 {
		delay = delay * 2
		attempt--
		if delay >= maxDelay {
			delay = maxDelay
			break
		}
	}
	delay = s.applyReconnectJitter(delay)
	if delay < s.cfg.LiveStreamReconnectDelay {
		return s.cfg.LiveStreamReconnectDelay
	}
	if delay > maxDelay {
		return maxDelay
	}
	return delay
}

func (s *Service) reconnectBudgetExceeded(ctx context.Context, subscription Subscription, reconnectAttempts int) (bool, error) {
	maxAttempts := s.cfg.LiveStreamMaxReconnectAttempts
	if maxAttempts <= 0 || reconnectAttempts <= maxAttempts {
		return false, nil
	}
	failReason := fmt.Sprintf(
		"live stream reconnect attempt budget exceeded after %d attempts",
		reconnectAttempts,
	)
	if s.metrics != nil {
		s.metrics.RecordLiveReconnectBudgetExceeded()
	}
	s.logger.Warn(
		"live_subscription_reconnect_budget_exceeded",
		"subscriptionId",
		subscription.ID.String(),
		"attempt",
		reconnectAttempts,
		"maxAttempts",
		maxAttempts,
	)
	if err := s.repo.MarkFailed(ctx, subscription.ID, failReason); err != nil {
		return true, err
	}
	return true, nil
}

func (s *Service) waitForLiveReconnect(ctx context.Context, delay time.Duration) error {
	if delay <= 0 {
		return nil
	}
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(delay):
		return nil
	}
}

func (s *Service) applyReconnectJitter(baseDelay time.Duration) time.Duration {
	if baseDelay <= 0 {
		return baseDelay
	}
	if s.cfg.LiveStreamReconnectJitterPercent <= 0 {
		return baseDelay
	}
	jitterWindow := baseDelay * time.Duration(s.cfg.LiveStreamReconnectJitterPercent) / 100
	if jitterWindow <= 0 {
		return baseDelay
	}
	windowNanoseconds := int64(jitterWindow)
	delta := rand.Int63n(windowNanoseconds*2+1) - windowNanoseconds
	delay := time.Duration(int64(baseDelay) + delta)
	return delay
}

func (s *Service) consume(
	ctx context.Context,
	conn *websocket.Conn,
	subscription Subscription,
	providerSymbol string,
	timeframe candles.Timeframe,
	readTimeout time.Duration,
	state candles.SymbolSourceState,
) error {
	defer conn.Close()
	bufferSize := s.cfg.LiveStreamMessageBuffer
	if bufferSize <= 0 {
		bufferSize = 1
	}
	messageBuffer := make(chan []byte, bufferSize)
	errorC := make(chan error, 1)
	go func() {
		defer close(messageBuffer)
		for {
			deadline := time.Now().UTC().Add(readTimeout)
			_ = conn.SetReadDeadline(deadline)
			_, rawMessage, err := conn.ReadMessage()
			if err != nil {
				errorC <- err
				return
			}
			select {
			case messageBuffer <- rawMessage:
			default:
				s.logger.Warn("live_subscription_message_dropped", "subscriptionId", subscription.ID.String())
				if s.metrics != nil {
					s.metrics.RecordLiveMessageDrop()
				}
			}
		}
	}()
	var run = candles.RunContext{}
	runInitialized := false
	runCounts := candles.WriteCounts{}
	for {
		select {
		case <-ctx.Done():
			if runInitialized {
				_ = s.writer.FinishRun(ctx, run, runCounts, false)
			}
			return ctx.Err()
		case readErr := <-errorC:
			if runInitialized {
				_ = s.writer.FinishRun(ctx, run, runCounts, false)
			}
			return readErr
		case rawMessage, ok := <-messageBuffer:
			if !ok {
				if runInitialized {
					_ = s.writer.FinishRun(ctx, run, runCounts, false)
				}
				return errLiveSubscriptionStopped
			}
			if s.metrics != nil {
				s.metrics.RecordLiveMessageReceived()
			}
			parsedEvent, parseErr := ParseBinanceMessage(rawMessage, subscription)
			eventStatus := EventStatusIgnored
			eventID, recorded, recErr := s.repo.CreateEvent(ctx, subscription, parsedEvent.Type, parsedEvent.ProviderTimestamp, parsedEvent.Payload)
			if recErr != nil {
				return recErr
			}
			if isLiveSubscriptionStopped(subscription.Status) {
				if recorded {
					_ = s.repo.UpdateEventStatus(ctx, eventID, EventStatusIgnored, "")
				}
				return errLiveSubscriptionStopped
			}
			if s.isProviderError(parsedEvent, parseErr) {
				eventStatus = EventStatusFailed
				errorMessage := parsedEvent.ErrorMessage
				if errorMessage == "" {
					errorMessage = "provider_error"
				}
				if recorded {
					_ = s.repo.MarkFailed(ctx, subscription.ID, errorMessage)
					_ = s.repo.UpdateEventStatus(ctx, eventID, eventStatus, errorMessage)
				}
				if s.metrics != nil {
					s.metrics.RecordLiveMessageFailed()
				}
				return errors.New(errorMessage)
			}
			if parseErr != nil {
				eventStatus = EventStatusFailed
				if s.metrics != nil {
					s.metrics.RecordLiveMessageParseFailure()
				}
				if recorded {
					_ = s.repo.UpdateEventStatus(ctx, eventID, eventStatus, parseErr.Error())
				}
				if s.metrics != nil {
					s.metrics.RecordLiveMessageFailed()
				}
				continue
			}
			if len(parsedEvent.Payload) > 0 {
				wasStale, err := s.repo.RecordHeartbeat(ctx, subscription.ID, parsedEvent.ProviderTimestamp)
				if err != nil {
					s.logger.Warn("live_subscription_heartbeat_failed", "subscriptionId", subscription.ID.String(), "error", err)
				}
				if wasStale {
					s.logger.Info("live_subscription_stale_recovered", "subscriptionId", subscription.ID.String(), "eventType", parsedEvent.Type)
					if s.metrics != nil {
						s.metrics.RecordLiveSubscriptionRevived()
					}
				}
			}
			if parsedEvent.Candle != nil {
				if !runInitialized {
					startedRun, err := s.writer.StartRun(ctx, subscription.WorkspaceID, subscription.SourceID, subscription.SymbolID, subscription.Timeframe, nil)
					if err != nil {
						_ = s.repo.UpdateEventStatus(ctx, eventID, EventStatusFailed, err.Error())
						if recorded {
							_ = s.repo.MarkFailed(ctx, subscription.ID, err.Error())
						}
						if s.metrics != nil {
							s.metrics.RecordLiveMessageFailed()
						}
						continue
					}
					run = startedRun
					runInitialized = true
					if s.metrics != nil {
						s.metrics.RecordLiveSubscriptionStarted()
					}
				}
				eventStatus = EventStatusProcessed
				issue := candles.Validate(*parsedEvent.Candle, state)
				if issue != nil {
					runCounts.Invalid++
					runCounts.Failed++
					if runInitialized {
						_ = s.writer.RecordInvalidConflicts(ctx, run, []candles.ValidationIssue{*issue}, fallbackCandleFromEvent(parsedEvent, subscription, timeframe))
					}
					if recorded {
						_ = s.repo.UpdateEventStatus(ctx, eventID, EventStatusFailed, issue.Message)
					}
					if s.metrics != nil {
						s.metrics.RecordLiveMessageFailed()
					}
					continue
				}
				writeCounts, conflicts, writeErr := s.writer.Write(ctx, run, []candles.Candle{*parsedEvent.Candle})
				runCounts.Received += writeCounts.Received
				runCounts.Inserted += writeCounts.Inserted
				runCounts.Updated += writeCounts.Updated
				runCounts.DuplicateSkipped += writeCounts.DuplicateSkipped
				runCounts.Conflicted += writeCounts.Conflicted
				runCounts.Invalid += writeCounts.Invalid
				runCounts.Failed += writeCounts.Failed
				runCounts.Batches += writeCounts.Batches
				if writeErr != nil {
					runCounts.Failed += 1
					if recorded {
						_ = s.repo.UpdateEventStatus(ctx, eventID, EventStatusFailed, writeErr.Error())
					}
					if s.metrics != nil {
						s.metrics.RecordLiveMessageFailed()
					}
					continue
				}
				for _, conflict := range conflicts {
					if parsedEvent.Type == EventTypeCandleFinal && conflict.Type == "final_conflict" {
						if recorded {
							_ = s.repo.UpdateEventStatus(ctx, eventID, EventStatusFailed, conflict.Type)
						}
						if s.metrics != nil {
							s.metrics.RecordLiveMessageFailed()
						}
						break
					}
					if conflict.Type == "partial_after_final" {
						eventStatus = EventStatusIgnored
					}
				}
				if parsedEvent.Type == EventTypeCandleFinal {
					if err := s.repo.RecordFinalCandle(ctx, subscription.ID, parsedEvent.Candle.Timestamp); err != nil {
						if recorded {
							_ = s.repo.UpdateEventStatus(ctx, eventID, EventStatusFailed, err.Error())
						}
						if s.metrics != nil {
							s.metrics.RecordLiveMessageFailed()
						}
						continue
					}
					if s.cfg.LiveStreamGapRecovery {
						_ = s.requestGap(ctx, subscription, providerSymbol, timeframe, parsedEvent.Candle.Timestamp)
					}
					subscription.LastFinalCandle = &parsedEvent.Candle.Timestamp
				}
				if s.metrics != nil {
					s.metrics.RecordLiveCandlesWritten(runCounts.Inserted + runCounts.Updated)
				}
			}
			if recorded {
				_ = s.repo.UpdateEventStatus(ctx, eventID, eventStatus, "")
			}
			if _, err := s.repo.LoadSubscription(ctx, subscription.ID); err != nil {
				if errors.Is(err, pgx.ErrNoRows) {
					if runInitialized {
						_ = s.writer.FinishRun(ctx, run, runCounts, false)
					}
					return errLiveSubscriptionStopped
				}
				if runInitialized {
					_ = s.writer.FinishRun(ctx, run, runCounts, false)
				}
				return err
			}
			if isLiveSubscriptionStopped(subscription.Status) {
				if runInitialized {
					_ = s.writer.FinishRun(ctx, run, runCounts, false)
				}
				return errLiveSubscriptionStopped
			}
		}
	}
}

func (s *Service) resolveProviderSymbol(subscription Subscription) (string, error) {
	return parseProviderSymbolOrDefault(subscription.ConfigJSON, subscription.Symbol)
}

func (s *Service) subscribeBinance(conn *websocket.Conn, providerSymbol string, timeframe string) error {
	stream := fmt.Sprintf("%s@kline_%s", strings.ToLower(providerSymbol), strings.ToLower(timeframe))
	now := time.Now().UTC().UnixNano()
	request := map[string]any{
		"method": "SUBSCRIBE",
		"params": []string{stream},
		"id":     now,
	}
	_ = conn.SetWriteDeadline(time.Now().UTC().Add(10 * time.Second))
	if err := conn.WriteJSON(request); err != nil {
		return err
	}
	_, _, err := conn.ReadMessage()
	if err != nil {
		return err
	}
	return nil
}

func (s *Service) requestGap(
	ctx context.Context,
	subscription Subscription,
	providerSymbol string,
	timeframe candles.Timeframe,
	finalAt time.Time,
) error {
	if !s.cfg.LiveStreamGapRecovery || subscription.LastFinalCandle == nil {
		return nil
	}
	if s.cfg.LiveStreamGapAfter > 0 && time.Since(*subscription.LastFinalCandle) < s.cfg.LiveStreamGapAfter {
		return nil
	}
	nextExpected := subscription.LastFinalCandle.Add(time.Duration(timeframe.Seconds) * time.Second)
	if !nextExpected.Before(finalAt) {
		return nil
	}
	missingSeconds := finalAt.Sub(nextExpected).Seconds()
	if missingSeconds <= 0 {
		return nil
	}
	missingCandles := int(missingSeconds / float64(timeframe.Seconds))
	if missingCandles > s.cfg.LiveStreamGapRequestLimit {
		return nil
	}
	created, err := s.repo.CreateGapRequest(ctx, subscription, nextExpected, finalAt, providerSymbol)
	if err != nil || !created {
		return err
	}
	if s.metrics != nil {
		s.metrics.RecordLiveGapRequest()
	}
	return nil
}

func (s *Service) isProviderError(event ParsedEvent, err error) bool {
	if err != nil || event.Type != EventTypeError {
		return false
	}
	return !strings.EqualFold(event.ErrorMessage, "unsupported_live_event_type")
}

func isLiveStreamReadTimeout(err error) bool {
	if err == nil {
		return false
	}
	var netErr net.Error
	if errors.As(err, &netErr) {
		return netErr.Timeout()
	}
	return errors.Is(err, context.DeadlineExceeded)
}

func isLiveSubscriptionActive(status string) bool {
	switch strings.ToLower(strings.TrimSpace(status)) {
	case "active", "stale":
		return true
	default:
		return false
	}
}

func isLiveSubscriptionStopped(status string) bool {
	switch strings.ToLower(strings.TrimSpace(status)) {
	case "paused", "failed", "stopped":
		return true
	default:
		return false
	}
}

func fallbackCandleFromEvent(event ParsedEvent, subscription Subscription, timeframe candles.Timeframe) candles.Candle {
	if event.Candle != nil {
		return *event.Candle
	}
	return candles.Candle{
		WorkspaceID:      subscription.WorkspaceID,
		SymbolID:         subscription.SymbolID,
		SourceID:         subscription.SourceID,
		Timeframe:        subscription.Timeframe,
		Timestamp:        time.Now().UTC().Truncate(time.Duration(timeframe.Seconds) * time.Second),
		IsFinal:          event.Type == EventTypeCandleFinal,
		OriginType:       "live_feed",
		OriginReferenceID: &subscription.ID,
		ProviderMetadata:  map[string]any{"provider": "binance"},
	}
}
