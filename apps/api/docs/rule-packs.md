# Rule Packs and Reproducibility Manifests

Rule packs persist deterministic rule metadata used by the backend. Reproducibility manifests attach
the relevant engine, rule, and module versions to an analysis run or signal so future replay,
reporting, and audit paths can understand which deterministic context was available.

This module is backend-only. It does not execute broker actions, provide financial advice, run LLM
classification, mutate final signals, or auto-adjust strategy profiles.

## Tables

- `rule_packs`
- `analysis_reproducibility_manifests`

## Settings

```txt
RULE_PACK_DEFAULT_KEY=default_deterministic_rules
RULE_PACK_DEFAULT_VERSION=v1
REPRODUCIBILITY_MANIFEST_VERSION=v1
```

## APIs

```txt
POST /rule-packs
GET /rule-packs
GET /rule-packs/{key}/{version}
POST /rule-packs/seed-default
POST /analysis-runs/{analysis_run_id}/reproducibility-manifest
GET /analysis-runs/{analysis_run_id}/reproducibility-manifest
POST /signals/{signal_id}/reproducibility-manifest
GET /signals/{signal_id}/reproducibility-manifest
```

## Integration

Manifests may reference advanced feature pack, event study, confidence calibration, and webhook
payload versions as module snapshots. They should remain audit artifacts and must not change replay
compatibility behavior unless a later replay module explicitly consumes them.
