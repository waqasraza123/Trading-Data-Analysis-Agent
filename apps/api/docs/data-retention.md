# Workspace Data Retention

Workspace data retention is an operational hygiene layer for identifying old raw or bulky records before any cleanup is applied. It is backend-only, audit-first, and dry-run-first.

The retention engine does not run automatically. There is no worker in this phase.

## Safety Model

- Dry-run is the default behavior.
- Apply can only act on items that were previously planned by a retention run.
- Redaction is preferred over deleting records.
- Critical audit records are not hard-deleted by default.
- Unsupported destructive actions are skipped and remain visible on run items.
- Each run stores filters, summary counts, result metadata, and item-level target/action records.

## Policy Shape

```json
{
  "importBatchRetentionDays": 365,
  "liveEventPayloadRetentionDays": 90,
  "providerPollingPayloadRetentionDays": 90,
  "llmInputRetentionDays": 90,
  "llmOutputRetentionDays": 180,
  "datasetExportRetentionDays": 180,
  "webhookOutboxRetentionDays": 180,
  "chartOcrPayloadRetentionDays": 180
}
```

Policies can be `active`, `paused`, or `archived`. Only active policies can be used for a run. If no policy is supplied, the default policy shape is used.

## Planned Target Types

- `import_batch`
- `live_feed_event`
- `provider_polling_request`
- `llm_explanation_payload`
- `reasoning_run_payload`
- `dataset_export`
- `webhook_outbox_event`
- `chart_screenshot_audit_payload`

The current implementation safely plans and applies redaction for existing raw-payload tables in this backend slice:

- `live_feed_events.payload_json`
- `llm_explanations.input_json`
- `llm_explanations.output_text`
- `llm_reasoning_runs.input_snapshot_json`
- `llm_reasoning_runs.output_json`
- `llm_reasoning_runs.output_text`
- `chart_screenshot_runs.extracted_payload_json`
- `chart_screenshot_runs.parser_metadata_json.ocr`

Import batches are planned as archive candidates but apply skips them because the current import batch table does not have an archive status or archive timestamp.

Provider polling requests, dataset exports, and webhook outbox events are optional target families. The planner checks whether matching tables exist and otherwise returns no items for those target types.

## APIs

```txt
POST /data-retention/policies
GET /data-retention/policies
GET /data-retention/policies/{policy_id}
PATCH /data-retention/policies/{policy_id}
POST /data-retention/runs/dry-run
POST /data-retention/runs/{run_id}/apply
GET /data-retention/runs/{run_id}
GET /data-retention/runs/{run_id}/items
```

## Dry-Run Flow

`POST /data-retention/runs/dry-run` accepts:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "policyId": null,
  "targetTypes": null,
  "olderThan": null,
  "limitPerTargetType": 500
}
```

The response creates a `data_retention_runs` record with mode `dry_run` and item records with status `planned`. It does not redact or delete anything.

## Apply Flow

`POST /data-retention/runs/{run_id}/apply` applies only the already-planned items from the dry run. Supported redaction items are updated and marked `applied`. Unsupported archive/delete actions are marked `skipped` with a reason.

The run mode changes to `apply`, and the run stores applied, skipped, and failed counts.

## Auditability

Retention runs preserve:

- policy id and workspace id
- request filters
- planned action count
- applied, skipped, and failed counts
- target type and target id
- action type and reason
- safe item metadata
- final result summary

The raw data being cleaned is not copied into retention run metadata.
