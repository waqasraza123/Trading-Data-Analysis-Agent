from decimal import Decimal

from app.modules.reasoning.models import (
    ReasoningGroundingStatus,
    ReasoningRunStatus,
    ReasoningSafetyStatus,
    ScenarioType,
)
from app.modules.scenario_ensembles.consensus import (
    EnsembleProviderOutput,
    EnsembleScenario,
    compute_consensus,
)
from app.modules.scenario_ensembles.models import ScenarioConsensusLabel


def provider_output(scenario_type: str) -> EnsembleProviderOutput:
    return EnsembleProviderOutput(
        provider="mock",
        model=f"mock-{scenario_type}",
        status=ReasoningRunStatus.COMPLETED.value,
        safety_status=ReasoningSafetyStatus.PASSED.value,
        grounding_status=ReasoningGroundingStatus.GROUNDED.value,
        scenarios=(
            EnsembleScenario(
                scenario_type=scenario_type,
                possibility_label="medium",
                suggested_actions=("evaluate_outcome_after_horizon",),
                supporting_evidence=("stored evidence",),
                conflicting_evidence=(),
            ),
        ),
    )


def test_consensus_strong_agreement_when_top_scenarios_match() -> None:
    result = compute_consensus(
        [
            provider_output(ScenarioType.CONTINUATION.value),
            provider_output(ScenarioType.CONTINUATION.value),
        ],
        Decimal("0.6000"),
    )

    assert result.consensus_label == ScenarioConsensusLabel.STRONG_AGREEMENT
    assert result.consensus_score == Decimal("1.0000")
    assert result.metadata["topScenarioType"] == ScenarioType.CONTINUATION.value


def test_consensus_disagreement_when_outputs_split_below_threshold() -> None:
    result = compute_consensus(
        [
            provider_output(ScenarioType.CONTINUATION.value),
            provider_output(ScenarioType.REVERSAL.value),
            provider_output(ScenarioType.CONSOLIDATION.value),
        ],
        Decimal("0.6000"),
    )

    assert result.consensus_label == ScenarioConsensusLabel.DISAGREEMENT
    assert result.consensus_score == Decimal("0.3333")


def test_consensus_excludes_failed_or_unsafe_outputs() -> None:
    unsafe = EnsembleProviderOutput(
        provider="mock",
        model="unsafe",
        status=ReasoningRunStatus.BLOCKED.value,
        safety_status=ReasoningSafetyStatus.BLOCKED.value,
        grounding_status=ReasoningGroundingStatus.NOT_CHECKED.value,
        scenarios=(),
    )

    result = compute_consensus(
        [
            provider_output(ScenarioType.CONTINUATION.value),
            provider_output(ScenarioType.CONTINUATION.value),
            unsafe,
        ],
        Decimal("0.6000"),
    )

    assert result.consensus_label == ScenarioConsensusLabel.STRONG_AGREEMENT
    assert result.consensus_score == Decimal("0.9000")
    assert result.metadata["invalidProviderCount"] == 1
