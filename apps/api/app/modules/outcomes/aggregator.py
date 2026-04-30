from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.outcomes.schemas import OutcomePerformanceRead


@dataclass(frozen=True)
class OutcomeAggregateGroup:
    group_key: str
    pattern_type: str | None
    strategy_profile_key: str | None
    symbol_id: UUID | None
    timeframe: str | None
    outcomes: list[SignalOutcome]


class OutcomeAggregator:
    def aggregate_by_patterns(
        self,
        outcomes: list[SignalOutcome],
        horizon_minutes: int,
    ) -> list[OutcomePerformanceRead]:
        return self.aggregate(
            outcomes=outcomes,
            horizon_minutes=horizon_minutes,
            key_builder=lambda outcome: outcome.pattern_type or "unknown_pattern",
            group_builder=lambda key, rows: OutcomeAggregateGroup(
                group_key=key,
                pattern_type=None if key == "unknown_pattern" else key,
                strategy_profile_key=None,
                symbol_id=None,
                timeframe=None,
                outcomes=rows,
            ),
        )

    def aggregate_by_strategy_profiles(
        self,
        outcomes: list[SignalOutcome],
        horizon_minutes: int,
    ) -> list[OutcomePerformanceRead]:
        return self.aggregate(
            outcomes=outcomes,
            horizon_minutes=horizon_minutes,
            key_builder=lambda outcome: outcome.strategy_profile_key or "unknown_strategy_profile",
            group_builder=lambda key, rows: OutcomeAggregateGroup(
                group_key=key,
                pattern_type=None,
                strategy_profile_key=None if key == "unknown_strategy_profile" else key,
                symbol_id=None,
                timeframe=None,
                outcomes=rows,
            ),
        )

    def aggregate_by_symbols(
        self,
        outcomes: list[SignalOutcome],
        horizon_minutes: int,
    ) -> list[OutcomePerformanceRead]:
        return self.aggregate(
            outcomes=outcomes,
            horizon_minutes=horizon_minutes,
            key_builder=lambda outcome: f"{outcome.symbol_id}:{outcome.timeframe}",
            group_builder=lambda key, rows: OutcomeAggregateGroup(
                group_key=key,
                pattern_type=None,
                strategy_profile_key=None,
                symbol_id=rows[0].symbol_id if rows else None,
                timeframe=rows[0].timeframe if rows else None,
                outcomes=rows,
            ),
        )

    def aggregate(
        self,
        outcomes: list[SignalOutcome],
        horizon_minutes: int,
        key_builder: Callable[[SignalOutcome], str],
        group_builder: Callable[[str, list[SignalOutcome]], OutcomeAggregateGroup],
    ) -> list[OutcomePerformanceRead]:
        grouped: dict[str, list[SignalOutcome]] = {}
        for outcome in outcomes:
            grouped.setdefault(key_builder(outcome), []).append(outcome)
        return [
            performance_from_group(group_builder(key, rows), horizon_minutes)
            for key, rows in sorted(grouped.items(), key=lambda item: item[0])
        ]


def performance_from_group(
    group: OutcomeAggregateGroup,
    horizon_minutes: int,
) -> OutcomePerformanceRead:
    evaluated = [
        outcome
        for outcome in group.outcomes
        if outcome.evaluation_status == OutcomeEvaluationStatus.EVALUATED
    ]
    continuation_count = count_label(evaluated, OutcomeLabel.CONTINUATION)
    partial_count = count_label(evaluated, OutcomeLabel.PARTIAL_FOLLOW_THROUGH)
    reversal_count = count_label(evaluated, OutcomeLabel.REVERSAL)
    no_follow_count = count_label(evaluated, OutcomeLabel.NO_FOLLOW_THROUGH)
    insufficient_count = count_label(group.outcomes, OutcomeLabel.INSUFFICIENT_DATA)
    evaluated_count = len(evaluated)
    return OutcomePerformanceRead(
        group_key=group.group_key,
        pattern_type=group.pattern_type,
        strategy_profile_key=group.strategy_profile_key,
        symbol_id=group.symbol_id,
        timeframe=group.timeframe,
        horizon_minutes=horizon_minutes,
        evaluated_count=evaluated_count,
        continuation_count=continuation_count,
        partial_follow_through_count=partial_count,
        reversal_count=reversal_count,
        no_follow_through_count=no_follow_count,
        insufficient_data_count=insufficient_count,
        continuation_rate=rate(continuation_count, evaluated_count),
        reversal_rate=rate(reversal_count, evaluated_count),
        historical_follow_through_rate=rate(continuation_count + partial_count, evaluated_count),
        average_max_favorable_move=average_decimal(
            [outcome.max_favorable_move for outcome in evaluated]
        ),
        average_max_adverse_move=average_decimal(
            [outcome.max_adverse_move for outcome in evaluated]
        ),
        average_net_move=average_decimal([outcome.net_move for outcome in evaluated]),
        average_max_favorable_pips=average_optional_decimal(
            [outcome.max_favorable_pips for outcome in evaluated]
        ),
        average_max_adverse_pips=average_optional_decimal(
            [outcome.max_adverse_pips for outcome in evaluated]
        ),
        average_net_pips=average_optional_decimal([outcome.net_pips for outcome in evaluated]),
        average_max_favorable_ticks=average_optional_decimal(
            [outcome.max_favorable_ticks for outcome in evaluated]
        ),
        average_max_adverse_ticks=average_optional_decimal(
            [outcome.max_adverse_ticks for outcome in evaluated]
        ),
        average_net_ticks=average_optional_decimal([outcome.net_ticks for outcome in evaluated]),
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
