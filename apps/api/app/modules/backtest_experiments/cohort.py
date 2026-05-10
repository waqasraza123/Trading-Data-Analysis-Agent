from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.backtest_experiments.models import (
    BacktestCohortLabel,
    BacktestExperimentCohort,
)
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.signals.models import Signal

UNKNOWN_VALUE = "unknown"
ALL_COHORT_KEY = "all_signals"


@dataclass(frozen=True)
class BacktestOutcomeRow:
    signal: Signal
    outcome: SignalOutcome
    news_correlation_label: str | None = None


class BacktestCohortBuilder:
    def build_cohorts(
        self,
        workspace_id: UUID,
        experiment_run_id: UUID,
        rows: list[BacktestOutcomeRow],
        dimensions: list[str],
        minimum_sample_size: int,
    ) -> list[BacktestExperimentCohort]:
        grouped: dict[tuple[str, int], list[BacktestOutcomeRow]] = {}
        for row in rows:
            key = cohort_key(row, dimensions)
            grouped.setdefault((key, row.outcome.horizon_minutes), []).append(row)
        cohorts = []
        for (key, horizon_minutes), group_rows in sorted(grouped.items(), key=lambda item: item[0]):
            cohorts.append(
                cohort_from_rows(
                    workspace_id=workspace_id,
                    experiment_run_id=experiment_run_id,
                    cohort_key_value=key,
                    dimensions=dimensions,
                    rows=group_rows,
                    horizon_minutes=horizon_minutes,
                    minimum_sample_size=minimum_sample_size,
                )
            )
        return cohorts


def cohort_from_rows(
    workspace_id: UUID,
    experiment_run_id: UUID,
    cohort_key_value: str,
    dimensions: list[str],
    rows: list[BacktestOutcomeRow],
    horizon_minutes: int,
    minimum_sample_size: int,
) -> BacktestExperimentCohort:
    evaluated_rows = [
        row for row in rows if row.outcome.evaluation_status == OutcomeEvaluationStatus.EVALUATED
    ]
    evaluated_outcomes = [row.outcome for row in evaluated_rows]
    continuation_count = count_label(evaluated_outcomes, OutcomeLabel.CONTINUATION)
    partial_count = count_label(evaluated_outcomes, OutcomeLabel.PARTIAL_FOLLOW_THROUGH)
    no_follow_count = count_label(evaluated_outcomes, OutcomeLabel.NO_FOLLOW_THROUGH)
    reversal_count = count_label(evaluated_outcomes, OutcomeLabel.REVERSAL)
    insufficient_count = count_label([row.outcome for row in rows], OutcomeLabel.INSUFFICIENT_DATA)
    sample_size = len(rows)
    evaluated_count = len(evaluated_rows)
    continuation_rate = rate(continuation_count, evaluated_count)
    reversal_rate = rate(reversal_count, evaluated_count)
    no_follow_rate = rate(no_follow_count, evaluated_count)
    label = cohort_label(
        sample_size=sample_size,
        evaluated_count=evaluated_count,
        minimum_sample_size=minimum_sample_size,
        continuation_rate=continuation_rate,
        reversal_rate=reversal_rate,
        no_follow_rate=no_follow_rate,
    )
    return BacktestExperimentCohort(
        workspace_id=workspace_id,
        experiment_run_id=experiment_run_id,
        cohort_key=cohort_key_value,
        cohort_dimensions_json=cohort_dimensions(rows[0], dimensions) if rows else {},
        horizon_minutes=horizon_minutes,
        sample_size=sample_size,
        evaluated_count=evaluated_count,
        continuation_count=continuation_count,
        partial_follow_through_count=partial_count,
        no_follow_through_count=no_follow_count,
        reversal_count=reversal_count,
        insufficient_data_count=insufficient_count,
        continuation_rate=continuation_rate,
        reversal_rate=reversal_rate,
        no_follow_through_rate=no_follow_rate,
        average_confidence_score=average_decimal(
            [row.signal.confidence_score for row in evaluated_rows]
        ),
        average_max_favorable_move=average_decimal(
            [outcome.max_favorable_move for outcome in evaluated_outcomes]
        ),
        average_max_adverse_move=average_decimal(
            [outcome.max_adverse_move for outcome in evaluated_outcomes]
        ),
        average_net_move=average_decimal([outcome.net_move for outcome in evaluated_outcomes]),
        average_max_favorable_pips=average_optional_decimal(
            [outcome.max_favorable_pips for outcome in evaluated_outcomes]
        ),
        average_max_adverse_pips=average_optional_decimal(
            [outcome.max_adverse_pips for outcome in evaluated_outcomes]
        ),
        average_net_pips=average_optional_decimal(
            [outcome.net_pips for outcome in evaluated_outcomes]
        ),
        average_max_favorable_ticks=average_optional_decimal(
            [outcome.max_favorable_ticks for outcome in evaluated_outcomes]
        ),
        average_max_adverse_ticks=average_optional_decimal(
            [outcome.max_adverse_ticks for outcome in evaluated_outcomes]
        ),
        average_net_ticks=average_optional_decimal(
            [outcome.net_ticks for outcome in evaluated_outcomes]
        ),
        cohort_label=label,
        summary=cohort_summary(
            label, sample_size, evaluated_count, continuation_rate, reversal_rate
        ),
        metadata_json={
            "minimumSampleSize": minimum_sample_size,
            "followThroughObservationRate": str(
                rate(continuation_count + partial_count, evaluated_count)
            ),
        },
    )


def cohort_key(row: BacktestOutcomeRow, dimensions: list[str]) -> str:
    values = cohort_dimensions(row, dimensions)
    if not values:
        return ALL_COHORT_KEY
    return "|".join(f"{key}={values[key]}" for key in sorted(values))


def cohort_dimensions(row: BacktestOutcomeRow, dimensions: list[str]) -> dict[str, object]:
    values: dict[str, object] = {}
    for dimension in dimensions:
        value = cohort_dimension_value(row, dimension)
        if value is None:
            continue
        values[dimension] = str(value)
    return values


def cohort_dimension_value(row: BacktestOutcomeRow, dimension: str) -> object | None:
    if dimension == "strategy_profile_key":
        return row.outcome.strategy_profile_key or UNKNOWN_VALUE
    if dimension == "pattern_type":
        return row.outcome.pattern_type or UNKNOWN_VALUE
    if dimension == "symbol_id":
        return row.outcome.symbol_id
    if dimension == "timeframe":
        return row.outcome.timeframe
    if dimension == "bias":
        return row.outcome.bias
    if dimension == "classification_status":
        return row.outcome.classification_status
    if dimension == "confidence_label":
        return row.signal.confidence_label
    if dimension == "news_correlation_label":
        return row.news_correlation_label or UNKNOWN_VALUE
    return None


def cohort_label(
    sample_size: int,
    evaluated_count: int,
    minimum_sample_size: int,
    continuation_rate: Decimal,
    reversal_rate: Decimal,
    no_follow_rate: Decimal,
) -> str:
    if sample_size == 0 or evaluated_count == 0:
        return BacktestCohortLabel.INSUFFICIENT_DATA
    if sample_size < minimum_sample_size:
        return BacktestCohortLabel.LOW_SAMPLE
    if continuation_rate >= Decimal("0.600000") and reversal_rate <= Decimal("0.200000"):
        return BacktestCohortLabel.STRONG_FOLLOW_THROUGH
    if reversal_rate >= Decimal("0.400000"):
        return BacktestCohortLabel.REVERSAL_PRONE
    if no_follow_rate >= Decimal("0.400000"):
        return BacktestCohortLabel.MIXED_BEHAVIOR
    return BacktestCohortLabel.NEUTRAL


def cohort_summary(
    label: str,
    sample_size: int,
    evaluated_count: int,
    continuation_rate: Decimal,
    reversal_rate: Decimal,
) -> str:
    return (
        f"{label} cohort with {sample_size} stored outcomes, {evaluated_count} evaluated outcomes, "
        f"{continuation_rate:.2%} continuation observations, and "
        f"{reversal_rate:.2%} reversal observations."
    )


def count_label(outcomes: list[SignalOutcome], label: OutcomeLabel) -> int:
    return sum(1 for outcome in outcomes if outcome.outcome_label == label)


def rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)


def average_decimal(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def average_optional_decimal(values: list[Decimal | None]) -> Decimal | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present, Decimal("0")) / Decimal(len(present))
