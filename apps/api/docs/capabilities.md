# Intelligence Capability Registry

The capability registry documents which backend intelligence modules exist, what they can do, what contracts and artifacts they use, and whether they are currently available.

It is metadata and configuration only. It does not run module operations, execute broker actions, auto-trade, send alerts, mutate intelligence artifacts, call external providers, or provide financial advice.

## Purpose

The registry answers operator and future UI questions:

- Which backend intelligence modules are installed.
- Which APIs and artifacts belong to each module.
- Which modules require a database.
- Which modules require external provider credentials.
- Which modules are deterministic, LLM-backed, read-only, worker-driven, or manual-only.
- Which modules produce persisted artifacts.
- Which modules are safe for automatic backend use.

## Table

`intelligence_capabilities` stores versioned capability metadata:

- `id`
- `key`
- `name`
- `version`
- `category`
- `status`
- `execution_type`
- `safety_level`
- `requires_external_credentials`
- `requires_database`
- `input_contracts_json`
- `output_contracts_json`
- `produced_artifacts_json`
- `route_refs_json`
- `dependencies_json`
- `metadata_json`
- `created_at`
- `updated_at`

`key` and `version` are unique together.

## Categories

Supported category values:

- `ingestion`
- `analysis`
- `signal`
- `explanation`
- `reasoning`
- `outcome`
- `diagnostics`
- `reporting`
- `operations`
- `safety`
- `governance`
- `export`

## Execution Types

Supported execution type values:

- `read_only`
- `deterministic_write`
- `external_provider`
- `llm_provider`
- `worker`
- `manual_only`

Execution type is descriptive. The capability registry does not invoke any execution path.

## Safety Levels

Supported safety level values:

- `safe_read`
- `safe_backend_write`
- `provider_backed`
- `review_required`
- `restricted`

Safety levels describe backend risk and review expectations. They do not grant permission to run modules automatically.

## Runtime Availability

Runtime availability checks are read-only. They inspect:

- whether the configured module path is importable;
- whether `DATABASE_URL` exists when a capability requires database access;
- whether provider or LLM settings exist when external credentials are required;
- whether module-level enablement settings, such as worker or LLM flags, are enabled.

The registry does not test network connections, call LLMs, connect to brokers, start workers, run analysis, poll providers, or mutate source artifacts.

## Settings

```txt
CAPABILITY_REGISTRY_DEFAULT_VERSION=v1
```

## APIs

```txt
GET /capabilities
GET /capabilities/{key}
POST /capabilities/seed-default
GET /capabilities/summary
```

`GET /capabilities` supports filters:

```txt
category
status
execution_type
safety_level
requires_external_credentials
include_runtime
limit
offset
```

`GET /capabilities/{key}` returns the latest registered version for the key.

`POST /capabilities/seed-default` is idempotent. It creates or updates default capability metadata and preserves persisted `disabled` or `deprecated` status values.

`GET /capabilities/summary` returns counts by persisted status, category, execution type, safety level, runtime status, and compact lists for missing, disabled, provider-backed, and auto-safe modules.

## Default Capabilities

`POST /capabilities/seed-default` registers:

```txt
candle_imports
live_feed_ingestion
provider_polling
analysis_lifecycle
signal_classification
deterministic_explanations
news_correlation
llm_explanations
scenario_reasoning
action_plans
reasoning_action_worker
outcomes
profile_diagnostics
intelligence_reports
audit_timeline
intelligence_quality
chart_screenshots
market_scans
historical_cases
market_regimes
market_sessions
cross_asset_context
walk_forward_validation
candle_gap_recovery
explanation_comparison
data_quality
datasets
synthetic_fixtures
webhook_outbox
safety_policies
decision_readiness
rule_packs
state_machines
```

If a default module cannot be imported, seeding marks it unavailable instead of failing the registry phase.

## Integrated Context Modules

The registry includes the merged context and diagnostics modules:

- `cross_asset_context` records final-candle-only co-movement, divergence, and possible lead/lag context.
- `walk_forward_validation` records validation-window behavior from existing signals and outcomes.
- `candle_gap_recovery` records missing final-candle recovery plans and optional pending polling rows without executing provider fetches.
- `explanation_comparison` records persisted explanation alignment findings without calling LLM providers or regenerating explanations.

Reports, audit timelines, readiness checks, and operator review flows may later read these artifacts
as context. The registry itself remains metadata only and never invokes those modules.

## Safety Boundaries

- Backend-only.
- No broker execution.
- No auto-trading.
- No financial advice.
- No UI.
- No alerts.
- Metadata and configuration only.
- Does not execute module operations.
- Does not mutate intelligence artifacts.
- Does not require optional modules to be present.
