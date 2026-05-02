# Intelligence Dataset Builder

The dataset builder creates redacted JSONL exports from persisted intelligence artifacts for offline
review and future evaluation workflows.

It does not train ML models, classify signals, run LLM classification, mutate final signals, export
secrets, export raw images, or include full candle series by default.

## APIs

```txt
POST /intelligence-datasets/exports
GET /intelligence-datasets/exports
GET /intelligence-datasets/exports/{export_id}
GET /intelligence-datasets/exports/{export_id}/items
GET /intelligence-datasets/exports/{export_id}/jsonl
```

## Export Contract

Exports are stored in `intelligence_dataset_exports` and `intelligence_dataset_export_items`.
Items include compact signal context and redaction metadata. Dataset exports are read-only artifacts.

## Settings

```txt
INTELLIGENCE_DATASET_SCHEMA_VERSION=v1
INTELLIGENCE_DATASET_DEFAULT_LIMIT=500
INTELLIGENCE_DATASET_MAX_LIMIT=5000
INTELLIGENCE_DATASET_MAX_TEXT_LENGTH=2000
```
