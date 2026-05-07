package health

import (
	"sync"
	"time"

	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
)

type Metrics struct {
	startedAt                time.Time
	mu                       sync.RWMutex
	JobsClaimed              int        `json:"jobsClaimed"`
	JobsCompleted            int        `json:"jobsCompleted"`
	JobsFailed               int        `json:"jobsFailed"`
	CandlesReceived          int        `json:"candlesReceived"`
	CandlesInserted          int        `json:"candlesInserted"`
	CandlesSkipped           int        `json:"candlesSkipped"`
	CandlesConflicted        int        `json:"candlesConflicted"`
	ProviderFailures         int        `json:"providerFailures"`
	ProviderGateWaits        int        `json:"providerGateWaits"`
	ProviderGateWaitMillis   int64      `json:"providerGateWaitMillis"`
	JobLockRenewals          int        `json:"jobLockRenewals"`
	JobLockRenewalFailures   int        `json:"jobLockRenewalFailures"`
	LastJobTime              *time.Time `json:"lastJobTime"`
}

type Snapshot struct {
	StartedAt              time.Time             `json:"startedAt"`
	UptimeSeconds          int64                 `json:"uptimeSeconds"`
	JobsClaimed            int                   `json:"jobsClaimed"`
	JobsCompleted          int                   `json:"jobsCompleted"`
	JobsFailed             int                   `json:"jobsFailed"`
	CandlesReceived        int                   `json:"candlesReceived"`
	CandlesInserted        int                   `json:"candlesInserted"`
	CandlesSkipped         int                   `json:"candlesSkipped"`
	CandlesConflicted      int                   `json:"candlesConflicted"`
	ProviderFailures       int                   `json:"providerFailures"`
	ProviderGateWaits      int                   `json:"providerGateWaits"`
	ProviderGateWaitMillis int64                 `json:"providerGateWaitMillis"`
	JobLockRenewals        int                   `json:"jobLockRenewals"`
	JobLockRenewalFailures int                   `json:"jobLockRenewalFailures"`
	LastJobTime            *time.Time            `json:"lastJobTime"`
	DBCapabilities         workerdb.Capabilities `json:"dbCapabilities"`
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

func (m *Metrics) Snapshot(capabilities workerdb.Capabilities) Snapshot {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return Snapshot{
		StartedAt:              m.startedAt,
		UptimeSeconds:          int64(time.Since(m.startedAt).Seconds()),
		JobsClaimed:            m.JobsClaimed,
		JobsCompleted:          m.JobsCompleted,
		JobsFailed:             m.JobsFailed,
		CandlesReceived:        m.CandlesReceived,
		CandlesInserted:        m.CandlesInserted,
		CandlesSkipped:         m.CandlesSkipped,
		CandlesConflicted:      m.CandlesConflicted,
		ProviderFailures:       m.ProviderFailures,
		ProviderGateWaits:      m.ProviderGateWaits,
		ProviderGateWaitMillis: m.ProviderGateWaitMillis,
		JobLockRenewals:        m.JobLockRenewals,
		JobLockRenewalFailures: m.JobLockRenewalFailures,
		LastJobTime:            m.LastJobTime,
		DBCapabilities:         capabilities,
	}
}
