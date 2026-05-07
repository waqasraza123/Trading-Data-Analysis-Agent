package health

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	workerdb "github.com/waqasraza123/trading-data-analysis-agent/apps/go/market-worker/internal/db"
)

type Server struct {
	server       *http.Server
	pool         *pgxpool.Pool
	workerID     string
	providers    []string
	capabilities workerdb.Capabilities
	metrics      *Metrics
	startedAt     time.Time
	readyErr      error
}

func NewServer(addr string, pool *pgxpool.Pool, workerID string, providers []string, capabilities workerdb.Capabilities, metrics *Metrics, readyErr error) *Server {
	instance := &Server{
		pool:         pool,
		workerID:     workerID,
		providers:    providers,
		capabilities: capabilities,
		metrics:      metrics,
		startedAt:     time.Now().UTC(),
		readyErr:      readyErr,
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", instance.healthz)
	mux.HandleFunc("GET /readyz", instance.readyz)
	mux.HandleFunc("GET /metrics.json", instance.metricsJSON)
	instance.server = &http.Server{Addr: addr, Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	return instance
}

func (s *Server) ListenAndServe() error {
	err := s.server.ListenAndServe()
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}

func (s *Server) Shutdown(ctx context.Context) error {
	return s.server.Shutdown(ctx)
}

func (s *Server) healthz(writer http.ResponseWriter, request *http.Request) {
	writeJSON(writer, http.StatusOK, map[string]any{
		"alive":         true,
		"workerId":      s.workerID,
		"uptimeSeconds": int64(time.Since(s.startedAt).Seconds()),
	})
}

func (s *Server) readyz(writer http.ResponseWriter, request *http.Request) {
	ctx, cancel := context.WithTimeout(request.Context(), 2*time.Second)
	defer cancel()
	dbConnected := s.pool.Ping(ctx) == nil
	ready := dbConnected && s.readyErr == nil && len(s.providers) > 0
	status := http.StatusOK
	if !ready {
		status = http.StatusServiceUnavailable
	}
	payload := map[string]any{
		"ready":          ready,
		"dbConnected":    dbConnected,
		"workerId":       s.workerID,
		"providers":      s.providers,
		"dbCapabilities": s.capabilities,
	}
	if s.readyErr != nil {
		payload["error"] = s.readyErr.Error()
	}
	writeJSON(writer, status, payload)
}

func (s *Server) metricsJSON(writer http.ResponseWriter, request *http.Request) {
	writeJSON(writer, http.StatusOK, s.metrics.Snapshot(s.capabilities))
}

func writeJSON(writer http.ResponseWriter, status int, payload any) {
	writer.Header().Set("Content-Type", "application/json")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(payload)
}
