package polling

import (
	"context"
	"sync"
	"time"
)

type ProviderGate struct {
	maxConcurrency int
	minInterval    time.Duration
	mu             sync.Mutex
	semaphores     map[string]chan struct{}
	lastStarted    map[string]time.Time
}

func NewProviderGate(maxConcurrency int, minInterval time.Duration) *ProviderGate {
	if maxConcurrency <= 0 {
		maxConcurrency = 1
	}
	if minInterval < 0 {
		minInterval = 0
	}
	return &ProviderGate{
		maxConcurrency: maxConcurrency,
		minInterval:    minInterval,
		semaphores:     map[string]chan struct{}{},
		lastStarted:    map[string]time.Time{},
	}
}

func (g *ProviderGate) Wait(ctx context.Context, provider string) (func(), time.Duration, error) {
	sem := g.semaphore(provider)
	started := time.Now()
	select {
	case sem <- struct{}{}:
	case <-ctx.Done():
		return nil, 0, ctx.Err()
	}
	release := func() {
		<-sem
	}
	if err := g.waitForPace(ctx, provider); err != nil {
		release()
		return nil, 0, err
	}
	return release, time.Since(started), nil
}

func (g *ProviderGate) semaphore(provider string) chan struct{} {
	g.mu.Lock()
	defer g.mu.Unlock()
	sem, ok := g.semaphores[provider]
	if !ok {
		sem = make(chan struct{}, g.maxConcurrency)
		g.semaphores[provider] = sem
	}
	return sem
}

func (g *ProviderGate) waitForPace(ctx context.Context, provider string) error {
	if g.minInterval <= 0 {
		return nil
	}
	for {
		g.mu.Lock()
		next := g.lastStarted[provider].Add(g.minInterval)
		wait := time.Until(next)
		if wait <= 0 {
			g.lastStarted[provider] = time.Now().UTC()
			g.mu.Unlock()
			return nil
		}
		g.mu.Unlock()
		timer := time.NewTimer(wait)
		select {
		case <-ctx.Done():
			if !timer.Stop() {
				select {
				case <-timer.C:
				default:
				}
			}
			return ctx.Err()
		case <-timer.C:
		}
	}
}
