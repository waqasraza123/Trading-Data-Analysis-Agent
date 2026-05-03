from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from app.modules.reasoning.models import (
    ReasoningGroundingStatus,
    ReasoningRunStatus,
    ReasoningSafetyStatus,
    ScenarioHypothesis,
    ScenarioType,
)
from app.modules.scenario_ensembles.models import (
    ScenarioConsensusLabel,
    ScenarioEnsembleItemStatus,
)


@dataclass(frozen=True)
class EnsembleScenario:
    scenario_type: str
    possibility_label: str
    suggested_actions: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    conflicting_evidence: tuple[str, ...]


@dataclass(frozen=True)
class EnsembleProviderOutput:
    provider: str
    model: str
    status: str
    safety_status: str
    grounding_status: str
    scenarios: tuple[EnsembleScenario, ...]


@dataclass(frozen=True)
class ConsensusScenarioResult:
    scenario_type: str
    agreement_count: int
    disagreement_count: int
    possibility_labels: list[str]
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    consensus_label: ScenarioConsensusLabel
    metadata: dict[str, object]


@dataclass(frozen=True)
class ConsensusSummary:
    consensus_score: Decimal
    consensus_label: ScenarioConsensusLabel
    safety_status: str
    grounding_status: str
    summary: str
    metadata: dict[str, object]
    results: list[ConsensusScenarioResult] = field(default_factory=list)


def build_provider_output(
    provider: str,
    model: str,
    status: str,
    safety_status: str,
    grounding_status: str,
    scenarios: list[ScenarioHypothesis],
) -> EnsembleProviderOutput:
    return EnsembleProviderOutput(
        provider=provider,
        model=model,
        status=status,
        safety_status=safety_status,
        grounding_status=grounding_status,
        scenarios=tuple(
            EnsembleScenario(
                scenario_type=scenario.scenario_type,
                possibility_label=scenario.possibility_label,
                suggested_actions=tuple(scenario.suggested_backend_actions_json),
                supporting_evidence=tuple(scenario.supporting_evidence_json),
                conflicting_evidence=tuple(scenario.conflicting_evidence_json),
            )
            for scenario in scenarios
        ),
    )


def compute_consensus(
    outputs: list[EnsembleProviderOutput],
    min_agreement_ratio: Decimal,
) -> ConsensusSummary:
    valid_outputs = [output for output in outputs if is_valid_output(output)]
    invalid_count = len(outputs) - len(valid_outputs)
    if not outputs:
        return failed_summary("No provider/model requests were available.")
    if not valid_outputs:
        label = (
            ScenarioConsensusLabel.FAILED
            if all(output.status == ScenarioEnsembleItemStatus.FAILED.value for output in outputs)
            else ScenarioConsensusLabel.INSUFFICIENT_CONTEXT
        )
        return ConsensusSummary(
            consensus_score=Decimal("0.0000"),
            consensus_label=label,
            safety_status=aggregate_safety_status(outputs),
            grounding_status=aggregate_grounding_status(outputs),
            summary="No valid grounded provider outputs were available for scenario consensus.",
            metadata={
                "validProviderCount": 0,
                "totalProviderCount": len(outputs),
                "invalidProviderCount": invalid_count,
            },
            results=[],
        )
    top_scenarios = [primary_scenario(output) for output in valid_outputs]
    scenario_counts = Counter(scenario.scenario_type for scenario in top_scenarios)
    top_scenario, top_count = scenario_counts.most_common(1)[0]
    raw_ratio = Decimal(top_count) / Decimal(len(valid_outputs))
    score = bounded_score(raw_ratio - Decimal("0.1000") * Decimal(invalid_count))
    label = consensus_label_for(
        top_scenario=top_scenario,
        agreement_ratio=raw_ratio,
        valid_provider_count=len(valid_outputs),
        min_agreement_ratio=min_agreement_ratio,
    )
    results = scenario_results(valid_outputs, scenario_counts, len(valid_outputs), label)
    return ConsensusSummary(
        consensus_score=score,
        consensus_label=label,
        safety_status=aggregate_safety_status(outputs),
        grounding_status=aggregate_grounding_status(outputs),
        summary=summary_text(label, top_scenario, top_count, len(valid_outputs), invalid_count),
        metadata={
            "validProviderCount": len(valid_outputs),
            "totalProviderCount": len(outputs),
            "invalidProviderCount": invalid_count,
            "topScenarioType": top_scenario,
            "topScenarioAgreementRatio": str(quantize_score(raw_ratio)),
            "topScenarioPossibilityAgreementRatio": str(
                possibility_agreement_ratio(top_scenarios)
            ),
            "topScenarioActionAgreementRatio": str(action_agreement_ratio(top_scenarios)),
            "minAgreementRatio": str(quantize_score(min_agreement_ratio)),
        },
        results=results,
    )


def is_valid_output(output: EnsembleProviderOutput) -> bool:
    return (
        output.status == ReasoningRunStatus.COMPLETED.value
        and output.safety_status == ReasoningSafetyStatus.PASSED.value
        and output.grounding_status == ReasoningGroundingStatus.GROUNDED.value
        and bool(output.scenarios)
    )


def primary_scenario(output: EnsembleProviderOutput) -> EnsembleScenario:
    return output.scenarios[0]


def possibility_agreement_ratio(scenarios: list[EnsembleScenario]) -> Decimal:
    if not scenarios:
        return Decimal("0.0000")
    counts = Counter(scenario.possibility_label for scenario in scenarios)
    return quantize_score(Decimal(counts.most_common(1)[0][1]) / Decimal(len(scenarios)))


def action_agreement_ratio(scenarios: list[EnsembleScenario]) -> Decimal:
    if not scenarios:
        return Decimal("0.0000")
    counts = Counter(tuple(sorted(scenario.suggested_actions)) for scenario in scenarios)
    return quantize_score(Decimal(counts.most_common(1)[0][1]) / Decimal(len(scenarios)))


def consensus_label_for(
    top_scenario: str,
    agreement_ratio: Decimal,
    valid_provider_count: int,
    min_agreement_ratio: Decimal,
) -> ScenarioConsensusLabel:
    if valid_provider_count < 2:
        return ScenarioConsensusLabel.INSUFFICIENT_CONTEXT
    if top_scenario == ScenarioType.INSUFFICIENT_CONTEXT.value:
        return ScenarioConsensusLabel.INSUFFICIENT_CONTEXT
    if agreement_ratio == Decimal("1"):
        return ScenarioConsensusLabel.STRONG_AGREEMENT
    if agreement_ratio >= min_agreement_ratio:
        return ScenarioConsensusLabel.PARTIAL_AGREEMENT
    return ScenarioConsensusLabel.DISAGREEMENT


def scenario_results(
    outputs: list[EnsembleProviderOutput],
    scenario_counts: Counter[str],
    valid_count: int,
    run_label: ScenarioConsensusLabel,
) -> list[ConsensusScenarioResult]:
    scenarios_by_type: dict[str, list[EnsembleScenario]] = defaultdict(list)
    for output in outputs:
        seen_types: set[str] = set()
        for scenario in output.scenarios:
            if scenario.scenario_type not in seen_types:
                scenarios_by_type[scenario.scenario_type].append(scenario)
                seen_types.add(scenario.scenario_type)
    results: list[ConsensusScenarioResult] = []
    for scenario_type, scenarios in sorted(
        scenarios_by_type.items(),
        key=lambda item: (-len(item[1]), item[0]),
    ):
        agreement_count = scenario_counts.get(scenario_type, len(scenarios))
        disagreement_count = max(0, valid_count - agreement_count)
        results.append(
            ConsensusScenarioResult(
                scenario_type=scenario_type,
                agreement_count=agreement_count,
                disagreement_count=disagreement_count,
                possibility_labels=sorted(
                    {scenario.possibility_label for scenario in scenarios}
                ),
                supporting_evidence=dedupe_text(
                    text
                    for scenario in scenarios
                    for text in scenario.supporting_evidence
                ),
                conflicting_evidence=dedupe_text(
                    text
                    for scenario in scenarios
                    for text in scenario.conflicting_evidence
                ),
                consensus_label=run_label,
                metadata={
                    "suggestedBackendActions": sorted(
                        {
                            action
                            for scenario in scenarios
                            for action in scenario.suggested_actions
                        }
                    ),
                    "providerScenarioCount": len(scenarios),
                },
            )
        )
    return results


def aggregate_safety_status(outputs: list[EnsembleProviderOutput]) -> str:
    statuses = {output.safety_status for output in outputs}
    if ReasoningSafetyStatus.BLOCKED.value in statuses:
        return ReasoningSafetyStatus.BLOCKED.value
    if ReasoningSafetyStatus.FAILED.value in statuses:
        return ReasoningSafetyStatus.FAILED.value
    if ReasoningSafetyStatus.FALLBACK_USED.value in statuses:
        return ReasoningSafetyStatus.FALLBACK_USED.value
    return ReasoningSafetyStatus.PASSED.value


def aggregate_grounding_status(outputs: list[EnsembleProviderOutput]) -> str:
    statuses = {output.grounding_status for output in outputs}
    if ReasoningGroundingStatus.FAILED.value in statuses:
        return ReasoningGroundingStatus.FAILED.value
    if ReasoningGroundingStatus.NOT_CHECKED.value in statuses:
        return ReasoningGroundingStatus.NOT_CHECKED.value
    if ReasoningGroundingStatus.QUESTIONABLE.value in statuses:
        return ReasoningGroundingStatus.QUESTIONABLE.value
    return ReasoningGroundingStatus.GROUNDED.value


def bounded_score(value: Decimal) -> Decimal:
    return quantize_score(max(Decimal("0"), min(Decimal("1"), value)))


def quantize_score(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def failed_summary(message: str) -> ConsensusSummary:
    return ConsensusSummary(
        consensus_score=Decimal("0.0000"),
        consensus_label=ScenarioConsensusLabel.FAILED,
        safety_status=ReasoningSafetyStatus.FAILED.value,
        grounding_status=ReasoningGroundingStatus.NOT_CHECKED.value,
        summary=message,
        metadata={"validProviderCount": 0, "totalProviderCount": 0, "invalidProviderCount": 0},
        results=[],
    )


def summary_text(
    label: ScenarioConsensusLabel,
    top_scenario: str,
    agreement_count: int,
    valid_count: int,
    invalid_count: int,
) -> str:
    warning = f" {invalid_count} provider output(s) were excluded from consensus." if invalid_count else ""
    if label == ScenarioConsensusLabel.INSUFFICIENT_CONTEXT:
        return (
            "Scenario ensemble did not have enough valid grounded provider agreement for a "
            f"diagnostic consensus.{warning}"
        )
    if label == ScenarioConsensusLabel.DISAGREEMENT:
        return (
            "Scenario ensemble found provider disagreement across grounded scenario outputs."
            f"{warning}"
        )
    return (
        f"Scenario ensemble found {agreement_count} of {valid_count} valid provider output(s) "
        f"agreeing on {top_scenario}.{warning}"
    )


def dedupe_text(values: object) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized and normalized not in seen:
                output.append(normalized)
                seen.add(normalized)
    return output
