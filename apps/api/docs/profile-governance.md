# Strategy Profile Governance

Strategy profile governance provides a controlled backend workflow for drafting, validating,
reviewing, approving, and promoting market-reading profile changes.

This is not auto-tuning. It does not mutate active strategy profiles automatically, does not apply
calibration recommendations, does not classify with an LLM, and does not perform broker execution,
auto-trading, alerts, or financial advice.

## Workflow

1. Create a draft with `POST /strategy-profile-drafts`.
2. Attach optional simulation and diagnostic references with create or patch requests.
3. Validate deterministically with `POST /strategy-profile-drafts/{draft_id}/validate`.
4. Submit a valid or valid-with-warnings draft with `POST /strategy-profile-drafts/{draft_id}/submit`.
5. Approve or reject the submitted draft.
6. Promote only an approved draft with `POST /strategy-profile-drafts/{draft_id}/promote`.
7. Read draft history with `GET /strategy-profile-drafts/{draft_id}/events`.

An approved draft is not active. Promotion is the only operation that creates a new active
`strategy_profiles` row.

## Validation Rules

Validation is deterministic and checks the proposed profile config before review or promotion:

- `draft_key` is required.
- `draft_version` is required.
- `allowed_patterns_json` must contain at least one supported pattern.
- `minimum_candidate_strength` must be between 0 and 1.
- `minimum_confidence` must be between 0 and 1.
- `component_weights_json` must be a non-empty object with non-negative weights.
- Component weights should sum close to `1.0`; otherwise validation returns warnings.
- `risk_filters_json` must be an object.
- `no_signal_rules_json` must be an object.
- Excluded patterns must not fully overlap allowed patterns.
- Broker, order, position, execution, quantity, margin, buy, sell, entry, exit, and leverage fields
  are rejected recursively anywhere in the config.
- Pattern names are checked against the current deterministic profile taxonomy when available.

Validation statuses:

```txt
not_validated
valid
valid_with_warnings
invalid
```

## Diff Behavior

Every draft stores a deterministic diff between the base profile config and the proposed config:

- allowed patterns added and removed
- excluded patterns added and removed
- minimum threshold changes
- component weight changes
- risk filter changes
- no-signal rule changes

The diff is stored on the draft so operators and future UI surfaces can show what changed before
approval or promotion.

## Promotion Safety

Promotion has explicit constraints:

- Only `approved` drafts can be promoted.
- Promotion creates a new `strategy_profiles` row using `proposed_config_json`.
- Promotion does not delete old profiles.
- Promotion does not affect past signals because signals already store profile snapshots.
- Older active versions remain active unless `deactivatePrevious=true` is sent.
- When `deactivatePrevious=true`, active profiles with the same draft key are marked inactive and the
  deactivated profile ids are stored in the promotion event metadata.
- The draft keeps validation, diff, reviewer, and promotion metadata for audit.

## APIs

```txt
POST /strategy-profile-drafts
GET /strategy-profile-drafts
GET /strategy-profile-drafts/{draft_id}
PATCH /strategy-profile-drafts/{draft_id}
POST /strategy-profile-drafts/{draft_id}/validate
POST /strategy-profile-drafts/{draft_id}/submit
POST /strategy-profile-drafts/{draft_id}/approve
POST /strategy-profile-drafts/{draft_id}/reject
POST /strategy-profile-drafts/{draft_id}/promote
POST /strategy-profile-drafts/{draft_id}/archive
GET /strategy-profile-drafts/{draft_id}/events
```

Draft statuses:

```txt
draft
ready_for_review
approved
rejected
promoted
archived
```

Event types:

```txt
created
validated
submitted_for_review
approved
rejected
promoted
archived
note_added
```

## Future Operator UI Use

The backend stores enough state for a future UI to show:

- base profile version and draft version
- proposed config
- deterministic validation errors and warnings
- field-level profile diff
- linked simulation and diagnostic runs
- reviewer, approver, rejecter, and promoter metadata
- complete draft event timeline

The UI should keep approval and promotion as separate explicit operator actions.
## Integrated Engine Boundary

Profile drafts are manual governance records. Aggregation context, provider polling, scenario
ensembles, and backtest experiments may provide evidence for operator review, but drafts are not
auto-promoted, are not used for production classification until explicitly promoted, and never mutate
historical final signals.
