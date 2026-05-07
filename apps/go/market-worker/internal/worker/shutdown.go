package worker

import (
	"context"
	"os/signal"
	"syscall"
)

func SignalContext(parent context.Context) (context.Context, context.CancelFunc) {
	return signal.NotifyContext(parent, syscall.SIGINT, syscall.SIGTERM)
}
