# Workspace Quick Actions

`POST /workspaces/{workspace_id}/quick-actions` runs explicit backend-safe daily tasks.

Allowed `actionType` values:

- `run_daily_workflow`
- `refresh_provider_health`
- `generate_daily_brief`
- `score_recent_signals`
- `refresh_market_memory`
- `run_product_readiness`

The endpoint rejects unsafe action names with `unsafe_action_rejected`. Unsupported backend-safe names return `unsupported_action`.

Quick actions call existing deterministic services only. Provider polling remains disabled unless an existing safe service and explicit options allow it. External notification delivery and broker execution are not part of this endpoint.

The response includes status, summary, created artifact IDs, result JSON, warnings, and missing sections.
