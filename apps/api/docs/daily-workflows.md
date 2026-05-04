# Daily Workflows

Daily workflows persist a bounded, auditable backend orchestration for the daily deterministic review loop.

The first workflow type is the one-click daily scan:

```txt
refresh provider/data status
prepare missing-data recovery plans
run scheduled/watchlist scan
generate setup context
score review priority
refresh market memory
generate signal digest
generate daily brief when the backend brief module is installed
```

The workflow does not place orders, call brokers, execute reasoning action items, execute notifications, auto-trade, copy-trade, or provide financial advice.

## Daily Product Flow

The daily-use loop is:

```txt
data freshness -> run workflow -> scanner presets -> brief -> triage -> setup detail -> journal/outcome review
```

Data freshness remains visible through provider health and onboarding. Running the workflow is an
explicit backend request. Scanner presets create watchlists and scan configs only. The generated
brief and triage pages read stored artifacts. Setup detail, journal, and outcome review stay
read-only or note-taking workflows around deterministic records.

## Tables

`daily_workflow_runs` stores one orchestration record per request:

- `workspace_id`
- `workflow_type`
- `status`
- `workflow_version`
- optional `watchlist_id`
- optional `preference_profile_id`
- optional `period_start` / `period_end`
- request filters, step summaries, result payload, artifact ids, summary, error, and timestamps

`daily_workflow_steps` stores one row per deterministic step:

- `workflow_run_id`
- `step_key`
- `status`
- input/output JSON
- skipped reason or error message
- timestamps

## API

```txt
POST /daily-workflows/run
GET /daily-workflows/runs
GET /daily-workflows/runs/{run_id}
GET /daily-workflows/runs/{run_id}/steps
POST /daily-workflows/runs/{run_id}/cancel
```

Run request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "workflowType": "daily_scan",
  "watchlistId": "00000000-0000-0000-0000-000000000000",
  "preferenceProfileId": null,
  "periodStart": "2026-05-03T00:00:00Z",
  "periodEnd": "2026-05-03T23:59:59Z",
  "options": {
    "prepareGapRecovery": true,
    "allowProviderPolling": false,
    "runScan": true,
    "generateSetupContext": true,
    "scorePriorities": true,
    "generateDigest": true,
    "generateBrief": true
  }
}
```

## Step Behavior

- `provider_health_refresh`: calls the provider health workspace refresh service. It reads stored data-source, candle, provider polling, live subscription, data-quality, market-memory, and gap-recovery state.
- `gap_recovery_prepare`: prepares recovery plans for refreshed snapshots with missing candles. It creates provider polling request rows only when both the request and backend setting explicitly allow it.
- `scheduled_scan_run`: runs existing scheduled scan configs. With a watchlist, it uses an active watchlist scan config or creates a workflow-owned config. Without a watchlist, it runs due configs for the workspace.
- `setup_context_generate`: generates setup context for produced signals when available.
- `signal_priority_score`: scores review priority for produced signals, or recent workspace signals when no scan signals were produced.
- `market_memory_refresh`: refreshes affected symbol/timeframe market memory, or bounded workspace candidates when no scan targets were produced.
- `signal_digest_generate`: creates a daily or watchlist digest over the workflow period.
- `daily_brief_generate`: creates a daily/watchlist brief if the backend daily brief module is installed; otherwise the step is skipped with an unavailable reason and a frontend brief link.

## Idempotency

If a pending or running workflow exists for the same workspace, workflow type, and watchlist, `POST /daily-workflows/run` returns that existing run instead of starting duplicate work.

Within a run, completed steps are not repeated when `force=false`.

## Settings

```txt
DAILY_WORKFLOW_VERSION=v1
DAILY_WORKFLOW_MAX_SYMBOLS=100
DAILY_WORKFLOW_MAX_SCAN_ITEMS=500
DAILY_WORKFLOW_ENABLE_PROVIDER_POLLING=false
DAILY_WORKFLOW_ENABLE_NOTIFICATIONS=false
```

Provider polling remains off unless both `allowProviderPolling=true` in the request and `DAILY_WORKFLOW_ENABLE_PROVIDER_POLLING=true` in backend settings.

Notifications remain off by default and are not executed by the workflow.

## Frontend

`/command-center` and `/scanner` show a “Run daily scan” control and workflow status panel. The panel shows run status, step completion/skipped/failed states, and links to the generated brief page, scan runs, and produced signal detail pages.

The UI uses review-oriented wording:

- Run daily scan
- Refresh data
- Generate brief
- Score review priority
- Prepare recovery plan

It avoids broker execution, notification execution, and advice wording.
