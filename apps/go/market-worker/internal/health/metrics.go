package health

import (
	"sync"
	"time"

	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
)

type Metrics struct {
	startedAt                time.Time
	mu                       sync.RWMutex
	JobsClaimed               int        `json:"jobsClaimed"`
	ProviderRequestsReclaimed int        `json:"providerRequestsReclaimed"`
	JobsCompleted             int        `json:"jobsCompleted"`
	JobsFailed                int        `json:"jobsFailed"`
	JobsTimedOut              int        `json:"jobsTimedOut"`
	CandlesReceived           int        `json:"candlesReceived"`
	CandlesInserted           int        `json:"candlesInserted"`
	CandlesSkipped            int        `json:"candlesSkipped"`
	CandlesConflicted         int        `json:"candlesConflicted"`
	LiveSubscriptionsClaimed   int        `json:"liveSubscriptionsClaimed"`
	LiveSubscriptionsStale     int        `json:"liveSubscriptionsStale"`
	LiveSubscriptionsRevived   int        `json:"liveSubscriptionsRevived"`
	LiveSubscriptionsStarted   int        `json:"liveSubscriptionsStarted"`
	LiveReconnects            int        `json:"liveReconnects"`
	LiveReconnectBudgetExceeded int       `json:"liveReconnectBudgetExceeded"`
	LiveReconnectReadTimeouts  int        `json:"liveReconnectReadTimeouts"`
	LiveMessagesReceived      int        `json:"liveMessagesReceived"`
	LiveMessagesFailed        int        `json:"liveMessagesFailed"`
	LiveMessageParseFailures  int        `json:"liveMessageParseFailures"`
	LiveCandlesWritten        int        `json:"liveCandlesWritten"`
	LiveMessageDrops          int        `json:"liveMessageDrops"`
	LiveGapRequests           int        `json:"liveGapRequests"`
	ProviderFailures          int        `json:"providerFailures"`
	ProviderGateWaits         int        `json:"providerGateWaits"`
	ProviderGateWaitMillis    int64      `json:"providerGateWaitMillis"`
	ProviderCircuitOpenings   int        `json:"providerCircuitOpenings"`
	ProviderCircuitBlocks     int        `json:"providerCircuitBlocks"`
	JobLockRenewals           int        `json:"jobLockRenewals"`
	JobLockRenewalFailures    int        `json:"jobLockRenewalFailures"`
	LastJobTime               *time.Time `json:"lastJobTime"`
}

type Snapshot struct {
	StartedAt                 time.Time             `json:"startedAt"`
	UptimeSeconds             int64                 `json:"uptimeSeconds"`
	JobsClaimed               int                   `json:"jobsClaimed"`
	ProviderRequestsReclaimed int                   `json:"providerRequestsReclaimed"`
	JobsCompleted             int                   `json:"jobsCompleted"`
	JobsFailed                int                   `json:"jobsFailed"`
	JobsTimedOut              int                   `json:"jobsTimedOut"`
	CandlesReceived           int                   `json:"candlesReceived"`
	CandlesInserted           int                   `json:"candlesInserted"`
	CandlesSkipped            int                   `json:"candlesSkipped"`
	CandlesConflicted         int                   `json:"candlesConflicted"`
	LiveSubscriptionsClaimed   int                   `json:"liveSubscriptionsClaimed"`
	LiveSubscriptionsStale     int                   `json:"liveSubscriptionsStale"`
	LiveSubscriptionsRevived   int                   `json:"liveSubscriptionsRevived"`
	LiveSubscriptionsStarted   int                   `json:"liveSubscriptionsStarted"`
	LiveReconnects            int                   `json:"liveReconnects"`
	LiveReconnectBudgetExceeded int                 `json:"liveReconnectBudgetExceeded"`
	LiveReconnectReadTimeouts  int                  `json:"liveReconnectReadTimeouts"`
	LiveMessagesReceived      int                   `json:"liveMessagesReceived"`
	LiveMessagesFailed        int                   `json:"liveMessagesFailed"`
	LiveMessageParseFailures  int                   `json:"liveMessageParseFailures"`
	LiveCandlesWritten        int                   `json:"liveCandlesWritten"`
	LiveMessageDrops          int                   `json:"liveMessageDrops"`
	LiveGapRequests           int                   `json:"liveGapRequests"`
	ProviderFailures          int                   `json:"providerFailures"`
	ProviderGateWaits         int                   `json:"providerGateWaits"`
	ProviderGateWaitMillis    int64                 `json:"providerGateWaitMillis"`
	ProviderCircuitOpenings   int                   `json:"providerCircuitOpenings"`
	ProviderCircuitBlocks     int                   `json:"providerCircuitBlocks"`
	JobLockRenewals           int                   `json:"jobLockRenewals"`
	JobLockRenewalFailures    int                   `json:"jobLockRenewalFailures"`
	LastJobTime               *time.Time            `json:"lastJobTime"`
	DBCapabilities            workerdb.Capabilities `json:"dbCapabilities"`
}

func NewMetrics() *Metrics {
	return &Metrics{startedAt: time.Now().UTC()}
}

func (m *Metrics) RecordClaimed(count int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.JobsClaimed += count
	now := time.Now().UTC()
	m.LastJobTime = &now
}

func (m *Metrics) RecordProviderRequestsReclaimed(count int) {
	if count <= 0 {
		return
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.ProviderRequestsReclaimed += count
}

func (m *Metrics) RecordCompleted(received int, inserted int, skipped int, conflicted int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.JobsCompleted++
	m.CandlesReceived += received
	m.CandlesInserted += inserted
	m.CandlesSkipped += skipped
	m.CandlesConflicted += conflicted
	now := time.Now().UTC()
	m.LastJobTime = &now
}

func (m *Metrics) RecordLiveSubscriptionClaimed() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveSubscriptionsClaimed++
}

func (m *Metrics) RecordLiveSubscriptionStale(count int) {
	if count <= 0 {
		return
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveSubscriptionsStale += count
}

func (m *Metrics) RecordLiveSubscriptionStarted() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveSubscriptionsStarted++
}

func (m *Metrics) RecordLiveSubscriptionRevived() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveSubscriptionsRevived++
}

func (m *Metrics) RecordLiveReconnect() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveReconnects++
}

func (m *Metrics) RecordLiveReconnectBudgetExceeded() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveReconnectBudgetExceeded++
}

func (m *Metrics) RecordLiveReconnectReadTimeout() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveReconnectReadTimeouts++
}

func (m *Metrics) RecordLiveMessageParseFailure() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveMessageParseFailures++
}

func (m *Metrics) RecordLiveMessageReceived() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveMessagesReceived++
}

func (m *Metrics) RecordLiveMessageFailed() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveMessagesFailed++
}

func (m *Metrics) RecordLiveCandlesWritten(count int) {
	if count <= 0 {
		return
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveCandlesWritten += count
}

func (m *Metrics) RecordLiveMessageDrop() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveMessageDrops++
}

func (m *Metrics) RecordLiveGapRequest() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.LiveGapRequests++
}

func (m *Metrics) RecordFailed(providerFailure bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.JobsFailed++
	if providerFailure {
		m.ProviderFailures++
	}
	now := time.Now().UTC()
	m.LastJobTime = &now
}

func (m *Metrics) RecordTimedOut() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.JobsTimedOut++
}

func (m *Metrics) RecordJobLockRenewal(success bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if success {
		m.JobLockRenewals++
	} else {
		m.JobLockRenewalFailures++
	}
}

func (m *Metrics) RecordProviderGateWait(wait time.Duration) {
	if wait < time.Millisecond {
		return
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.ProviderGateWaits++
	m.ProviderGateWaitMillis += wait.Milliseconds()
}

func (m *Metrics) RecordProviderCircuitOpened() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.ProviderCircuitOpenings++
}

func (m *Metrics) RecordProviderCircuitBlocked() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.ProviderCircuitBlocks++
}

func (m *Metrics) Snapshot(capabilities workerdb.Capabilities) Snapshot {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return Snapshot{
		StartedAt:                m.startedAt,
		UptimeSeconds:            int64(time.Since(m.startedAt).Seconds()),
		JobsClaimed:              m.JobsClaimed,
		ProviderRequestsReclaimed: m.ProviderRequestsReclaimed,
		JobsCompleted:            m.JobsCompleted,
		JobsFailed:               m.JobsFailed,
		JobsTimedOut:             m.JobsTimedOut,
		CandlesReceived:          m.CandlesReceived,
		CandlesInserted:          m.CandlesInserted,
		CandlesSkipped:           m.CandlesSkipped,
		CandlesConflicted:        m.CandlesConflicted,
		LiveSubscriptionsClaimed:  m.LiveSubscriptionsClaimed,
		LiveSubscriptionsStale:    m.LiveSubscriptionsStale,
		LiveSubscriptionsRevived:  m.LiveSubscriptionsRevived,
		LiveSubscriptionsStarted:  m.LiveSubscriptionsStarted,
		LiveReconnects:           m.LiveReconnects,
		LiveReconnectBudgetExceeded: m.LiveReconnectBudgetExceeded,
		LiveReconnectReadTimeouts:  m.LiveReconnectReadTimeouts,
		LiveMessagesReceived:     m.LiveMessagesReceived,
		LiveMessagesFailed:       m.LiveMessagesFailed,
		LiveMessageParseFailures: m.LiveMessageParseFailures,
		LiveCandlesWritten:       m.LiveCandlesWritten,
		LiveMessageDrops:         m.LiveMessageDrops,
		LiveGapRequests:          m.LiveGapRequests,
		ProviderFailures:         m.ProviderFailures,
		ProviderGateWaits:        m.ProviderGateWaits,
		ProviderGateWaitMillis:   m.ProviderGateWaitMillis,
		ProviderCircuitOpenings:  m.ProviderCircuitOpenings,
		ProviderCircuitBlocks:    m.ProviderCircuitBlocks,
		JobLockRenewals:          m.JobLockRenewals,
		JobLockRenewalFailures:   m.JobLockRenewalFailures,
		LastJobTime:              m.LastJobTime,
		DBCapabilities:           capabilities,
	}
}
