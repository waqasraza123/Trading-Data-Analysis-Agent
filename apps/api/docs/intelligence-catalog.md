# Workspace Intelligence Catalog

The intelligence catalog is a workspace-scoped metadata index for persisted backend artifacts. It lets future UI and operator tools answer what intelligence exists in a workspace and filter it by symbol, timeframe, profile, pattern, status, label, source, tags, and date.

The catalog does not store full raw payloads, uploaded files, LLM inputs, LLM outputs, candle rows, provider event bodies, or report bodies. It stores bounded titles, summaries, labels, tags, source identifiers, artifact IDs, and searchable metadata.

## Indexed Artifact Types

- `analysis_run`
- `signal`
- `outcome`
- `reasoning_run`
- `action_plan`
- `action_item`
- `news_event`
- `chart_screenshot_run`
- `operator_review`
- `quality_run`
- `diagnostic_run`
- `dataset_export`
- `report`
- `rule_manifest`
- `provider_polling_request`
- `scheduled_scan_run`

Some catalog types are metadata views over existing persisted artifacts:

- `scheduled_scan_run` indexes `analysis_runs` with `analysis_mode='scheduled_scan'`.
- `dataset_export` indexes import batches as persisted dataset ingestion/export metadata.
- `quality_run` indexes import batch quality metadata.
- `operator_review` indexes calibration recommendations and human-review action items.
- `rule_manifest` indexes deterministic strategy profile rule manifests into a workspace catalog row.
- `provider_polling_request` indexes API polling data sources.
- `report` indexes existing read-only intelligence report subjects as searchable metadata, not generated report payloads.

## Search Behavior

Search is implemented inside PostgreSQL with no external search engine. The current implementation uses normalized `searchable_text` plus `ILIKE` filtering. JSONB tags are filterable through `tags_json`.

Supported filters:

- `workspace_id`
- `query`
- `artifact_types`
- `status`
- `symbol_id`
- `timeframe`
- `strategy_profile_key`
- `pattern_type`
- `bias`
- `outcome_label`
- `source_type`
- `tags`
- `start_time`
- `end_time`
- `limit`
- `offset`

Results are ordered by artifact creation time when present, then by `indexed_at`.

## Indexing Behavior

`POST /intelligence-catalog/index` indexes one existing artifact by `artifact_type` and `artifact_id`.

`POST /intelligence-catalog/reindex` indexes a bounded set of artifacts for a workspace. The default limit is `1000` per artifact type. Reindexing upserts catalog rows and does not mutate source artifacts.

Catalog rows are unique by:

```txt
workspace_id + artifact_type + artifact_id
```

## API Contracts

```txt
POST /intelligence-catalog/index
POST /intelligence-catalog/reindex
POST /intelligence-catalog/items
DELETE /intelligence-catalog/items
GET /intelligence-catalog/search
GET /intelligence-catalog/items/{item_id}
GET /intelligence-catalog/by-artifact
```

`POST /intelligence-catalog/items` is an internal upsert path for backend services that already have a prepared metadata payload. It should not be used to store raw artifacts.

`GET /intelligence-catalog/by-artifact` requires `workspace_id`, `artifact_type`, and `artifact_id` because artifact uniqueness is workspace-scoped.

## Safety Boundaries

- No external search service.
- No UI.
- No broker execution.
- No auto-trading.
- No financial advice.
- No LLM classification.
- No mutation of source artifacts.
- No raw payload storage.
