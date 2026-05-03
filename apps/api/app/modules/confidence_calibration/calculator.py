from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.modules.confidence_calibration.models import ConfidenceCalibrationLabel
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.signals.models import SignalBias, SignalClassificationStatus


@dataclass(frozen=True)
class ConfidenceCalibrationThresholds:
    overconfident_threshold: Decimal
    underconfident_threshold: Decimal


@dataclass(frozen=True)
class ConfidenceBinDefinition:
    label: str
    minimum: Decimal
    maximum: Decimal


@dataclass(frozen=True)
class CalibrationOutcome:
    signal_id: UUID
    horizon_minutes: int
    bias: str
    classification_status: str
    evaluation_status: str
    outcome_label: str
    confidence_score: Decimal


@dataclass(frozen=True, kw_only=True)
class ConfidenceCalibrationBinResult:
    horizon_minutes: int
    bin_label: str
    bin_min: Decimal
    bin_max: Decimal
    sample_size: int
    evaluated_count: int
    continuation_count: int
    partial_follow_through_count: int
    no_follow_through_count: int
    reversal_count: int
    insufficient_data_count: int
    continuation_rate: Decimal
    reversal_rate: Decimal
    no_follow_through_rate: Decimal
    average_confidence_score: Decimal
    confidence_alignment_score: Decimal
    calibration_label: ConfidenceCalibrationLabel
    metadata_json: dict[str, object] = field(default_factory=dict)


class ConfidenceCalibrationCalculator:
    def calculate_bins(
        self,
        outcomes: list[CalibrationOutcome],
        horizons_minutes: list[int],
        bin_definitions: list[ConfidenceBinDefinition],
        minimum_sample_size: int,
        thresholds: ConfidenceCalibrationThresholds,
    ) -> list[ConfidenceCalibrationBinResult]:
        return [
            self.calculate_bin(
                horizon_minutes=horizon,
                bin_definition=bin_definition,
                outcomes=[
                    outcome
                    for outcome in outcomes
                    if outcome.horizon_minutes == horizon
                    and confidence_in_bin(outcome.confidence_score, bin_definition)
                ],
                minimum_sample_size=minimum_sample_size,
                thresholds=thresholds,
            )
            for horizon in horizons_minutes
            for bin_definition in bin_definitions
        ]

    def calculate_bin(
        self,
        horizon_minutes: int,
        bin_definition: ConfidenceBinDefinition,
        outcomes: list[CalibrationOutcome],
        minimum_sample_size: int,
        thresholds: ConfidenceCalibrationThresholds,
    ) -> ConfidenceCalibrationBinResult:
        directional = directional_outcomes(outcomes)
        evaluated = evaluated_alignment_outcomes(directional)
        continuation_count = count_label(evaluated, OutcomeLabel.CONTINUATION.value)
        partial_count = count_label(evaluated, OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value)
        no_follow_count = count_label(evaluated, OutcomeLabel.NO_FOLLOW_THROUGH.value)
        reversal_count = count_label(evaluated, OutcomeLabel.REVERSAL.value)
        insufficient_count = count_label(directional, OutcomeLabel.INSUFFICIENT_DATA.value)
        evaluated_count = len(evaluated)
        observed_follow_through_rate = rate(continuation_count + partial_count, evaluated_count)
        reversal_rate = rate(reversal_count, evaluated_count)
        no_follow_rate = rate(no_follow_count, evaluated_count)
        average_confidence = average_decimal([outcome.confidence_score for outcome in evaluated])
        alignment_score = confidence_alignment_score(
            average_confidence=average_confidence,
            observed_follow_through_rate=observed_follow_through_rate,
            evaluated_count=evaluated_count,
        )
        label = calibration_label(
            sample_size=len(directional),
            evaluated_count=evaluated_count,
            observed_follow_through_rate=observed_follow_through_rate,
            reversal_rate=reversal_rate,
            no_follow_through_rate=no_follow_rate,
            average_confidence=average_confidence,
            minimum_sample_size=minimum_sample_size,
            thresholds=thresholds,
        )
        return ConfidenceCalibrationBinResult(
            horizon_minutes=horizon_minutes,
            bin_label=bin_definition.label,
            bin_min=quantize_score(bin_definition.minimum),
            bin_max=quantize_score(bin_definition.maximum),
            sample_size=len(directional),
            evaluated_count=evaluated_count,
            continuation_count=continuation_count,
            partial_follow_through_count=partial_count,
            no_follow_through_count=no_follow_count,
            reversal_count=reversal_count,
            insufficient_data_count=insufficient_count,
            continuation_rate=quantize_rate(observed_follow_through_rate),
            reversal_rate=quantize_rate(reversal_rate),
            no_follow_through_rate=quantize_rate(no_follow_rate),
            average_confidence_score=quantize_rate(average_confidence),
            confidence_alignment_score=quantize_rate(alignment_score),
            calibration_label=label,
            metadata_json={
                "observedFollowThroughRate": str(quantize_rate(observed_follow_through_rate)),
                "alignmentDenominator": evaluated_count,
                "minimumSampleSize": minimum_sample_size,
                "overconfidentThreshold": str(thresholds.overconfident_threshold),
                "underconfidentThreshold": str(thresholds.underconfident_threshold),
            },
        )


def parse_bin_config(raw_config: str) -> list[ConfidenceBinDefinition]:
    definitions: list[ConfidenceBinDefinition] = []
    for raw_part in raw_config.split(","):
        part = raw_part.strip()
        if not part:
            continue
        bounds = [value.strip() for value in part.split("-", maxsplit=1)]
        if len(bounds) != 2:
            msg = f"Invalid confidence calibration bin: {part}"
            raise ValueError(msg)
        minimum = Decimal(bounds[0])
        maximum = Decimal(bounds[1])
        if minimum < 0 or maximum > 1 or minimum > maximum:
            msg = f"Invalid confidence calibration bin range: {part}"
            raise ValueError(msg)
        definitions.append(
            ConfidenceBinDefinition(
                label=f"{minimum}-{maximum}",
                minimum=minimum,
                maximum=maximum,
            )
        )
    if not definitions:
        msg = "At least one confidence calibration bin is required"
        raise ValueError(msg)
    return definitions


def bin_config_json(definitions: list[ConfidenceBinDefinition]) -> list[dict[str, object]]:
    return [
        {
            "label": definition.label,
            "minimum": str(quantize_score(definition.minimum)),
            "maximum": str(quantize_score(definition.maximum)),
        }
        for definition in definitions
    ]


def directional_outcomes(outcomes: list[CalibrationOutcome]) -> list[CalibrationOutcome]:
    return [
        outcome
        for outcome in outcomes
        if outcome.classification_status == SignalClassificationStatus.SIGNAL.value
        and outcome.bias in {SignalBias.BULLISH.value, SignalBias.BEARISH.value}
    ]


def evaluated_alignment_outcomes(outcomes: list[CalibrationOutcome]) -> list[CalibrationOutcome]:
    return [
        outcome
        for outcome in outcomes
        if outcome.evaluation_status == OutcomeEvaluationStatus.EVALUATED.value
        and outcome.outcome_label
        in {
            OutcomeLabel.CONTINUATION.value,
            OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value,
            OutcomeLabel.NO_FOLLOW_THROUGH.value,
            OutcomeLabel.REVERSAL.value,
        }
    ]


def confidence_in_bin(confidence_score: Decimal, definition: ConfidenceBinDefinition) -> bool:
    return definition.minimum <= confidence_score <= definition.maximum


def count_label(outcomes: list[CalibrationOutcome], label: str) -> int:
    return sum(1 for outcome in outcomes if outcome.outcome_label == label)


def rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)


def average_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def confidence_alignment_score(
    average_confidence: Decimal,
    observed_follow_through_rate: Decimal,
    evaluated_count: int,
) -> Decimal:
    if evaluated_count == 0:
        return Decimal("0")
    score = Decimal("1") - abs(average_confidence - observed_follow_through_rate)
    return min(Decimal("1"), max(Decimal("0"), score))


def calibration_label(
    sample_size: int,
    evaluated_count: int,
    observed_follow_through_rate: Decimal,
    reversal_rate: Decimal,
    no_follow_through_rate: Decimal,
    average_confidence: Decimal,
    minimum_sample_size: int,
    thresholds: ConfidenceCalibrationThresholds,
) -> ConfidenceCalibrationLabel:
    if sample_size == 0 or evaluated_count == 0:
        return ConfidenceCalibrationLabel.INSUFFICIENT_DATA
    if evaluated_count < minimum_sample_size:
        return ConfidenceCalibrationLabel.LOW_SAMPLE
    confidence_gap = average_confidence - observed_follow_through_rate
    if confidence_gap >= thresholds.overconfident_threshold:
        return ConfidenceCalibrationLabel.OVERCONFIDENT
    if -confidence_gap >= thresholds.underconfident_threshold:
        return ConfidenceCalibrationLabel.UNDERCONFIDENT
    if observed_follow_through_rate > 0 and (reversal_rate > 0 or no_follow_through_rate > 0):
        return ConfidenceCalibrationLabel.MIXED
    return ConfidenceCalibrationLabel.WELL_ALIGNED


def quantize_rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def quantize_score(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))
