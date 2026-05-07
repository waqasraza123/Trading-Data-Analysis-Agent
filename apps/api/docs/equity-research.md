# Equity Research Mode

Equity Research Mode adds a deterministic stock research workflow for personal swing setup review.
It is a market-intelligence module only. It does not place orders, connect to brokers for order
execution, auto-trade, copy-trade, mutate final signal classifications, call LLMs for
classification, or provide financial advice.

## Scope

The module supports:

- Workspace-scoped equity universes.
- Manual stock universe membership from existing `symbols` records.
- Deterministic swing scan runs over stored candles and persisted analysis artifacts.
- Ranked swing setup candidates with auditable component scores.
- Manual and provider-derived catalyst context attached to persisted symbols.
- Latest equity metadata, fundamentals, and earnings context when imported or enriched.
- Optional links to existing analysis runs, signals, setup context, and priority context.

External stock-universe, fundamentals, and earnings ingestion now exists as an additive foundation
under `/equity-data`. Polygon, Alpaca, and generic HTTP are registered as safe provider skeletons
that use credential references and do not require paid credentials at startup.

## Data Model

The migration `202605071000_add_equity_research.py` adds:

- `equity_universes`
- `equity_universe_members`
- `equity_swing_scan_runs`
- `equity_swing_candidates`
- `equity_catalyst_contexts`

The equity data foundation separately adds provider request audit rows, metadata snapshots,
fundamentals snapshots, earnings events, and import errors. Equity research reads those artifacts
when available but keeps manual catalyst flows intact.

Universes are workspace-scoped and can be manual, market-cap, sector, index, watchlist-linked, or
custom. This phase implements manual membership and leaves provider-backed population for later.
Universe members must reference existing active stock symbols.

Scan runs store scan version, profile key, filters, counts, status, summary, and error details.
Candidates store the deterministic score, label, component scores, evidence, review notes, and
links to existing persisted artifacts when available.

## Settings

- `EQUITY_RESEARCH_VERSION`, default `v1`
- `EQUITY_SWING_SCAN_MAX_SYMBOLS`, default `500`
- `EQUITY_SWING_MIN_AVERAGE_VOLUME`, default `500000`
- `EQUITY_SWING_MIN_SETUP_SCORE`, default `0.60`
- `EQUITY_SWING_STRONG_SETUP_SCORE`, default `0.75`
- `EQUITY_SWING_LOOKBACK_DAYS`, default `90`
- `EQUITY_SWING_DEFAULT_TIMEFRAMES`, default `1d,4h,1h`

## Scan Profiles

Initial deterministic profiles are code-defined:

- `continuation_momentum`
- `constructive_pullback`
- `breakout_retest`
- `reversal_watch`
- `avoid_chop_or_stale`

Profiles constrain allowed setup types, minimum data quality, liquidity, volume, trend, relative
strength, volatility, stale-data tolerance, and timeframe context where available. They do not
mutate strategy profiles and do not emit direct action instructions.

## Scoring

The scorer reads stored candles and optional persisted artifacts. It computes:

- Liquidity context.
- Volume context.
- Trend quality.
- Pullback quality.
- Relative strength context.
- Momentum context.
- Volatility context.
- Catalyst context.
- Data freshness and quality context.
- Weighted setup quality.

Labels are:

- `strong_context`
- `acceptable_context`
- `mixed_context`
- `review_required`
- `avoid_condition`
- `insufficient_context`

Candidate states are:

- `candidate`
- `needs_confirmation`
- `conflicted`
- `avoid`
- `insufficient_data`
- `stale_data`

## API

Universe APIs:

- `POST /equity-research/universes`
- `GET /equity-research/universes`
- `GET /equity-research/universes/{universe_id}`
- `PATCH /equity-research/universes/{universe_id}`
- `POST /equity-research/universes/{universe_id}/members`
- `POST /equity-research/universes/{universe_id}/members/bulk`
- `GET /equity-research/universes/{universe_id}/members`
- `DELETE /equity-research/universes/{universe_id}/members/{member_id}`

Swing scan APIs:

- `POST /equity-research/swing-scans`
- `GET /equity-research/swing-scans`
- `GET /equity-research/swing-scans/{scan_run_id}`
- `GET /equity-research/swing-scans/{scan_run_id}/candidates`
- `GET /equity-research/candidates/{candidate_id}`

Catalyst APIs:

- `POST /equity-research/catalysts`
- `GET /equity-research/catalysts`
- `GET /equity-research/symbols/{symbol_id}/catalysts`

## Safety Boundary

All outputs use research and review language such as research candidate, swing setup candidate,
setup quality, observation zone, invalidation context, target context zone, review recommended,
needs confirmation, avoid condition, no directional signal, and data freshness. LLM explanation
layers may be added later only after deterministic artifacts exist and must remain grounded in
stored data.
