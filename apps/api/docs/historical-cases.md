# Historical Similarity And Case Retrieval

Historical cases provide deterministic similarity search over persisted signal and analysis
artifacts. The module is backend-only and supports operator review by surfacing similar historical
contexts and observed outcomes.

## Purpose

The case retrieval engine stores vector-like deterministic feature payloads and search records for
signals or analysis runs. Similarity scoring is deterministic and uses persisted artifacts only.

Expected routes:

```txt
POST /signals/{signal_id}/historical-case-vector
GET /signals/{signal_id}/historical-case-vector
POST /signals/{signal_id}/historical-cases/search
POST /analysis-runs/{analysis_run_id}/historical-cases/search
POST /historical-cases/backfill
```

## Settings

```txt
HISTORICAL_CASE_VECTOR_VERSION=historical_case_vector_v1
HISTORICAL_CASE_DEFAULT_LIMIT=10
HISTORICAL_CASE_MAX_LIMIT=50
HISTORICAL_CASE_MIN_SCORE=0.5000
```

## Integration

Decision readiness and scenario reasoning may read existing similar-case search results when
available. Similarity search must not trigger LLMs, create signals, run analysis, run replay, or
auto-backfill vectors unless the explicit historical-case API is called.

## Safety

Similar cases are descriptive historical context. Public payloads should use terms like observed
outcomes, historical follow-through, and similar cases. They must not imply profit, guarantees,
trade readiness, or financial advice.
