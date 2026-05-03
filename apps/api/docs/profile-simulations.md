# Strategy Profile Simulation Sandbox

Strategy profile simulations let operators test a hypothetical config against persisted historical
signals, pattern candidates, feature snapshots, indicator snapshots, and observed outcomes.

The sandbox is diagnostic only. It does not mutate production strategy profiles, final signals,
selected pattern candidates, outcomes, diagnostics, action plans, notifications, or broker-related
state. It does not auto-apply profile changes and does not use LLMs.

## Purpose

The simulation layer answers calibration review questions such as:

```txt
What would happen if minimum_confidence were higher?
What would happen if minimum_candidate_strength were lower?
Which historical cases would have been included or excluded?
Would a stricter fakeout rule have blocked weak observed follow-through cases?
How would a proposed profile config compare against observed outcomes?
Which profile settings deserve manual review?
```

The output is for operator review. It uses safe terms such as sandbox, hypothetical config,
simulation, included historical cases, excluded historical cases, observed follow-through,
observed reversal, and calibration review.

## Safety Boundaries

The sandbox never:

- mutates `strategy_profiles`;
- mutates `signals`;
- rewrites classifier behavior;
- marks `pattern_candidates.is_selected`;
- executes broker, order, position, copy-trading, or auto-trading behavior;
- sends alerts or notifications;
- provides financial advice;
- trains ML models;
- uses LLMs for simulation.

Deterministic persisted artifacts remain the source of truth. Simulation results are stored in
separate sandbox tables.

## Supported Config Overrides

`proposedConfig` supports only:

```txt
minimumConfidence
minimumCandidateStrength
componentWeights
riskFilters
noSignalRules
allowedPatterns
excludedPatterns
```

The backend applies these overrides in memory to a copy of the selected base strategy profile.

## API

Run a simulation:

```txt
POST /profile-simulations/run
```

Request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "baseStrategyProfileKey": "breakout_continuation",
  "baseStrategyProfileVersion": "v1",
  "proposedConfig": {
    "minimumConfidence": 0.72,
    "minimumCandidateStrength": 0.70
  },
  "filters": {
    "symbolId": null,
    "timeframe": "1m",
    "patternType": null,
    "startTime": null,
    "endTime": null,
    "maxSignals": 500
  },
  "horizonsMinutes": [15, 30, 60]
}
```

Fetch a run:

```txt
GET /profile-simulations/runs/{run_id}
```

Fetch per-signal results:

```txt
GET /profile-simulations/runs/{run_id}/results?limit=500&offset=0
```

## Stored Artifacts

`strategy_profile_simulation_runs` stores run status, simulation version, base profile key/version,
the hypothetical config, filters, horizons, sampled counts, included/excluded counts, changed
decision counts, summary JSON, and failure details.

`strategy_profile_simulation_results` stores one row per sampled historical signal with original
classification fields, simulated classification fields, decision change type, observed outcome
label and horizon when available, and structured reason JSON.

Decision change values:

```txt
unchanged
included
excluded
bias_changed
pattern_changed
confidence_changed
no_candidate
```

## Future Operator UI Usage

A future UI can use the run endpoint to create an auditable sandbox run, then render:

- included and excluded historical cases;
- observed follow-through and observed reversal groupings;
- changed decision summaries;
- reason JSON for calibration review;
- links back to original signal, analysis run, candidate, and outcome artifacts.

The UI must keep the same safety boundary: simulations can inform manual calibration review, but
must not auto-apply strategy profile changes.

## Integrated Context

Operator playbooks may recommend running or reviewing a simulation when diagnostics indicate
threshold review. Dataset exports may reference simulation result identifiers in future contracts,
but they must not include unredacted artifacts or auto-apply hypothetical config.
