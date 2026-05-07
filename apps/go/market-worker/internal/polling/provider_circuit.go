package polling

import (
	"sync"
	"time"
)

type ProviderCircuitBreaker struct {
	threshold int
	cooldown  time.Duration
	mu        sync.Mutex
	state     map[string]ProviderCircuitState
}

type ProviderCircuitState struct {
	ConsecutiveFailures int       `json:"consecutiveFailures"`
	OpenUntil           time.Time `json:"openUntil"`
	LastFailureAt        time.Time `json:"lastFailureAt"`
	LastSuccessAt        time.Time `json:"lastSuccessAt"`
}

func NewProviderCircuitBreaker(threshold int, cooldown time.Duration) *ProviderCircuitBreaker {
	if threshold < 0 {
		threshold = 0
	}
	if cooldown < 0 {
		cooldown = 0
	}
	return &ProviderCircuitBreaker{
		threshold: threshold,
		cooldown:  cooldown,
		state:     map[string]ProviderCircuitState{},
	}
}

func (b *ProviderCircuitBreaker) Allow(provider string) (ProviderCircuitState, bool) {
	if b.threshold == 0 || b.cooldown == 0 {
		return ProviderCircuitState{}, true
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	state := b.state[provider]
	if !state.OpenUntil.IsZero() && time.Now().UTC().Before(state.OpenUntil) {
		return state, false
	}
	return state, true
}

func (b *ProviderCircuitBreaker) RecordSuccess(provider string) {
	if b.threshold == 0 || b.cooldown == 0 {
		return
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	state := b.state[provider]
	state.ConsecutiveFailures = 0
	state.OpenUntil = time.Time{}
	state.LastSuccessAt = time.Now().UTC()
	b.state[provider] = state
}

func (b *ProviderCircuitBreaker) RecordFailure(provider string) bool {
	if b.threshold == 0 || b.cooldown == 0 {
		return false
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	state := b.state[provider]
	state.ConsecutiveFailures++
	state.LastFailureAt = time.Now().UTC()
	opened := false
	if state.ConsecutiveFailures >= b.threshold {
		state.OpenUntil = state.LastFailureAt.Add(b.cooldown)
		opened = true
	}
	b.state[provider] = state
	return opened
}
