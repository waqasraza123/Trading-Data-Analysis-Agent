# Intelligence Artifact Dependency Graph

The artifact graph records how persisted intelligence artifacts relate to each other. It is traceability and invalidation infrastructure only. It does not recompute artifacts, delete artifacts, mutate signal classification, create alerts, run workers, execute broker actions, or provide financial advice.

## Purpose

The graph answers audit and debugging questions such as:

- Which artifacts were produced by an analysis run.
- Which signals depend on pattern candidates, features, indicators, and profile diagnostics.
- Which outcomes depend on a signal.
- Which reasoning runs depend on signals, explanations, outcomes, and news correlations.
- Which downstream artifacts become stale when an upstream source changes.
- Which stale artifacts are recomputation candidates for a future worker.
- Which dependency path explains why an artifact became stale.

## Artifact Records

Artifacts are registered in `intelligence_artifacts` by workspace, type, and source id. Registration is idempotent on:

```txt
workspace_id + artifact_type + artifact_id
```

Supported artifact types:

```txt
candle_set
analysis_run
feature_snapshot
indicator_snapshot
pattern_candidate_set
signal
deterministic_explanation
llm_explanation
news_correlation_set
outcome_set
reasoning_run
action_plan
report
dataset_export
quality_run
diagnostic_run
historical_case_vector
rule_manifest
chart_screenshot_run
replay_run
```

Artifact status values:

```txt
current
stale
superseded
archived
unknown
```

`stale` means the artifact may need recomputation later. The artifact graph does not perform that recomputation.

## Dependencies

Dependencies are stored in `intelligence_artifact_dependencies`. The source artifact points to the upstream artifact and the target artifact points to the downstream artifact.

Relationship types:

```txt
produced
derived_from
explained_by
evaluated_by
correlated_with
reasoned_from
planned_from
replayed_from
corrected_from
diagnosed_by
exported_from
```

Examples:

- `analysis_run produced signal`
- `feature_snapshot derived_from candle_set`
- `signal derived_from pattern_candidate_set`
- `outcome_set evaluated_by signal`
- `reasoning_run reasoned_from signal`
- `action_plan planned_from reasoning_run`
- `report exported_from signal`

Traversal is bounded by `ARTIFACT_GRAPH_MAX_TRAVERSAL_DEPTH`, cycle-safe, and capped by `ARTIFACT_GRAPH_MAX_PATHS`.

## Invalidation

Manual invalidation starts from one source artifact and walks downstream dependencies. Each downstream artifact is marked `stale`, and the operation writes:

- One `artifact_invalidation_events` row.
- One `artifact_invalidation_items` row per affected downstream artifact.
- A serialized dependency path for each affected artifact.

Reason codes:

```txt
source_data_changed
rule_pack_changed
strategy_profile_changed
correction_accepted
replay_requested
manual_invalidation
data_quality_changed
parser_version_changed
```

Invalidation does not delete data, rerun analysis, evaluate outcomes, generate explanations, run reasoning, trigger notifications, or execute any broker workflow.

## API Contracts

Register or update an artifact:

```txt
POST /artifact-graph/artifacts
```

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "artifactType": "signal",
  "artifactId": "00000000-0000-0000-0000-000000000001",
  "metadata": {}
}
```

Fetch by artifact record id:

```txt
GET /artifact-graph/artifacts/{artifact_record_id}
```

Fetch by source identity:

```txt
GET /artifact-graph/artifacts/by-source?workspaceId=...&artifactType=signal&artifactId=...
```

Link artifacts:

```txt
POST /artifact-graph/dependencies
```

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "sourceArtifactRecordId": "00000000-0000-0000-0000-000000000001",
  "targetArtifactRecordId": "00000000-0000-0000-0000-000000000002",
  "relationshipType": "derived_from",
  "metadata": {}
}
```

Inspect dependencies:

```txt
GET /artifact-graph/artifacts/{artifact_record_id}/upstream
GET /artifact-graph/artifacts/{artifact_record_id}/downstream
GET /artifact-graph/artifacts/{source_artifact_record_id}/dependency-path/{target_artifact_record_id}
```

Invalidate downstream artifacts:

```txt
POST /artifact-graph/artifacts/{artifact_record_id}/invalidate-downstream
```

```json
{
  "reasonCode": "manual_invalidation",
  "reason": "Operator marked upstream source as changed",
  "metadata": {}
}
```

List recomputation candidates:

```txt
GET /artifact-graph/stale?workspaceId=...
```

Mark an artifact current after a future recomputation worker completes:

```txt
POST /artifact-graph/artifacts/{artifact_record_id}/mark-current
```

Summarize a workspace graph:

```txt
GET /artifact-graph/summary?workspaceId=...
```

## Future Worker Integration

A later worker can consume `GET /artifact-graph/stale` as a queue of recomputation candidates. That worker must decide what recomputation is allowed, run the appropriate deterministic or optional explanation process, register new artifact versions, link new dependencies, and then call `mark-current`. This phase intentionally does not implement that worker.
