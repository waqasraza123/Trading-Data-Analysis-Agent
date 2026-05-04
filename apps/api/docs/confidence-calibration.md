# Confidence Calibration

Confidence calibration summarizes how stored deterministic confidence aligned with observed outcome
labels across historical samples. It produces calibration runs and bins for reliability review.

This module does not train models, adjust strategy profiles, rewrite confidence scores, mutate final
signals, or provide financial advice.

## Tables

- `confidence_calibration_runs`
- `confidence_calibration_bins`

## Settings

```txt
CONFIDENCE_CALIBRATION_VERSION=v1
CONFIDENCE_CALIBRATION_DEFAULT_BINS=0-0.39,0.40-0.64,0.65-0.79,0.80-1.0
CONFIDENCE_CALIBRATION_MINIMUM_SAMPLE_SIZE=20
CONFIDENCE_CALIBRATION_OVERCONFIDENT_THRESHOLD=0.15
CONFIDENCE_CALIBRATION_UNDERCONFIDENT_THRESHOLD=0.15
```

## APIs

```txt
POST /confidence-calibration/run
GET /confidence-calibration/runs
GET /confidence-calibration/runs/{run_id}
GET /confidence-calibration/runs/{run_id}/bins
```

## Safe Terms

Use calibration alignment, reliability table, historical follow-through rate, continuation rate,
overconfidence review, and underconfidence review. Avoid broker-accounting, certainty, direct order
advice, and auto-tuning language.
