# Data Contract Schema Registry

The data contract registry stores versioned schemas for backend JSON artifacts and records validation results for explicit payload checks. It is backend-only and does not classify signals, generate advice, execute broker actions, send alerts, or mutate existing analysis artifacts.

## Tables

`data_contracts` stores registered contracts:

- `key`
- `version`
- `status`
- `description`
- `schema_json`
- `metadata_json`

`key` and `version` are unique together. Status can be `active`, `draft`, `deprecated`, or `archived`.

`data_contract_validations` stores validation attempts:

- optional `workspace_id`
- `contract_key`
- `contract_version`
- optional `source_type`
- optional `source_id`
- `status`
- `validation_errors_json`
- `validation_warnings_json`
- `payload_summary_json`
- `created_at`

Validation status can be `passed`, `failed`, or `passed_with_warnings`.

## Default Contracts

The seed endpoint registers these v1 contracts:

- `candle_import_row.v1`
- `normalized_candle.v1`
- `feature_snapshot.v1`
- `indicator_snapshot.v1`
- `strategy_profile_config.v1`
- `signal_snapshot.v1`
- `outcome_metadata.v1`
- `reasoning_output.v1`
- `scenario_hypothesis.v1`
- `webhook_payload.v1`
- `dataset_record.v1`
- `chart_axis_calibration.v1`
- `chart_ocr_metadata.v1`

The schemas are JSON-schema-like dictionaries held in code under `app.modules.data_contracts.registry`. They intentionally cover structural compatibility rather than replacing existing Pydantic request models or deterministic engine validation.

## Validation Behavior

The validator checks:

- top-level object or array shape
- required fields
- primitive field types
- nested object and array item shapes where a contract defines them
- enum membership where a contract defines allowed values
- market-number compatibility for values serialized as strings, integers, floats, or Decimals

The validator returns structured errors and warnings. It stores only a payload summary, not a duplicate full payload, in `data_contract_validations`.

## Strict vs Loose

`strict=false` is the compatibility mode. Missing required fields and type mismatches fail validation. Unknown fields are warnings so older or richer JSONB artifacts can still pass while surfacing drift.

`strict=true` is the migration/readiness mode. Unknown fields become errors. Use this when validating a proposed migration or enforcing a newly narrowed contract.

## Source Payload Validation

`validate_source_payload` supports current JSONB artifact locations that have concrete storage in the backend:

- `feature_snapshot`
- `indicator_snapshot`
- `pattern_evidence`
- `pattern_metrics`
- `strategy_profile_config`
- `signal_snapshot`
- `news_correlation_metadata`
- `outcome_metadata`
- `reasoning_input`
- `reasoning_output`
- `scenario_hypothesis`
- `webhook_payload`
- `live_feed_event_payload`
- `chart_axis_calibration`
- `chart_ocr_metadata`

`dataset_record` is registered for future dataset storage, but this phase does not add a dataset persistence module.

## APIs

```txt
GET /data-contracts
GET /data-contracts?status=active
GET /data-contracts/{key}/{version}
POST /data-contracts/seed-default
POST /data-contracts/validate
POST /data-contracts/validate-source
GET /data-contracts/validations
```

`POST /data-contracts/validate` accepts an explicit payload:

```json
{
  "key": "reasoning_output",
  "version": "v1",
  "payload": {
    "summary": "Grounded scenario summary",
    "scenarios": [],
    "limitations": []
  },
  "sourceType": "reasoning_output",
  "sourceId": "00000000-0000-0000-0000-000000000000",
  "strict": false
}
```

`POST /data-contracts/validate-source` loads a stored source payload by `sourceType` and `sourceId`, validates it, and persists the result:

```json
{
  "sourceType": "feature_snapshot",
  "sourceId": "00000000-0000-0000-0000-000000000000",
  "contractKey": "feature_snapshot",
  "version": "v1",
  "strict": false
}
```

## Future Migration Use

Future JSONB migrations can use this registry in three phases:

1. Seed or update the new contract version as `draft`.
2. Validate stored source payloads with `strict=false` to identify required-field and type failures without rejecting historical extension fields.
3. Validate candidate transformed payloads with `strict=true` before promoting the contract to `active`.

The registry is deliberately additive. It does not rewrite every schema, does not alter existing API response contracts, and does not move JSONB ownership away from the modules that create each artifact.
