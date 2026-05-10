from uuid import uuid4

import pytest

from app.modules.ai_intelligence.grounding import check_ai_intelligence_grounding
from app.modules.ai_intelligence.models import AiIntelligenceGroundingStatus
from app.modules.ai_intelligence.parser import parse_ai_intelligence_output
from app.modules.ai_intelligence.safety import check_ai_intelligence_safety
from app.modules.ai_intelligence.schemas import AiArtifactRef
from app.modules.llm_adapters.mock import MockLlmAdapter
from app.modules.llm_adapters.schemas import LlmAdapterRequest, LlmAdapterResponse


def test_ai_intelligence_parser_accepts_cited_insight() -> None:
    signal_id = uuid4()
    response = LlmAdapterResponse(
        provider="mock",
        model="mock",
        output_text="Grounded advisory insight.",
        output_json={
            "summary": "Grounded summary",
            "insights": [
                {
                    "insightType": "confidence_alignment",
                    "severity": "medium",
                    "title": "Confidence needs context",
                    "summary": "Confidence should be reviewed against stored outcomes.",
                    "rationale": "The cited signal is available.",
                    "evidenceRefs": [{"artifactType": "signal", "artifactId": str(signal_id)}],
                    "limitations": ["Advisory only."],
                    "safeFollowUpActions": ["evaluate_outcome_after_horizon"],
                    "claims": [
                        {
                            "claim": "The signal has persisted evidence.",
                            "evidenceRefs": [
                                {"artifactType": "signal", "artifactId": str(signal_id)}
                            ],
                            "supportStatus": "supported",
                        }
                    ],
                }
            ],
            "limitations": ["No trading advice."],
        },
    )

    parsed = parse_ai_intelligence_output(response)

    assert parsed.summary == "Grounded summary"
    assert parsed.insights[0].safe_follow_up_actions == ["evaluate_outcome_after_horizon"]
    assert parsed.insights[0].claims[0].evidence_refs[0].artifact_id == signal_id


def test_ai_intelligence_parser_rejects_trading_action() -> None:
    response = LlmAdapterResponse(
        provider="mock",
        model="mock",
        output_text="Bad output",
        output_json={
            "summary": "Bad output",
            "insights": [
                {
                    "insightType": "general_context",
                    "severity": "info",
                    "title": "Unsafe",
                    "summary": "Unsafe",
                    "rationale": "Unsafe",
                    "evidenceRefs": [],
                    "safeFollowUpActions": ["buy"],
                    "claims": [],
                }
            ],
        },
    )

    parsed = parse_ai_intelligence_output(response)

    assert parsed.fallback_used is True
    assert "trading action" in (parsed.error_message or "")


def test_ai_intelligence_grounding_requires_known_refs() -> None:
    signal_id = uuid4()
    parsed = parse_ai_intelligence_output(
        LlmAdapterResponse(
            provider="mock",
            model="mock",
            output_text="Grounded advisory insight.",
            output_json={
                "summary": "Grounded summary",
                "insights": [
                    {
                        "insightType": "general_context",
                        "severity": "info",
                        "title": "Known ref",
                        "summary": "Known ref",
                        "rationale": "Known ref",
                        "evidenceRefs": [{"artifactType": "signal", "artifactId": str(signal_id)}],
                        "claims": [
                            {
                                "claim": "Known claim",
                                "evidenceRefs": [
                                    {"artifactType": "signal", "artifactId": str(signal_id)}
                                ],
                            }
                        ],
                    }
                ],
            },
        )
    )

    grounded = check_ai_intelligence_grounding(
        [AiArtifactRef(artifact_type="signal", artifact_id=signal_id)],
        parsed,
    )
    failed = check_ai_intelligence_grounding([], parsed)

    assert grounded.status == AiIntelligenceGroundingStatus.GROUNDED
    assert failed.status == AiIntelligenceGroundingStatus.FAILED


def test_ai_intelligence_safety_blocks_trade_advice() -> None:
    result = check_ai_intelligence_safety("You should buy now with guaranteed profit.")

    assert result.passed is False
    assert "buy now" in result.blocked_terms


@pytest.mark.anyio
async def test_mock_adapter_returns_ai_intelligence_schema() -> None:
    signal_id = uuid4()
    adapter = MockLlmAdapter()
    response = await adapter.generate_structured(
        LlmAdapterRequest(
            provider="mock",
            model="mock-ai",
            system_prompt="system",
            user_prompt="user",
            input_json={"artifactRefs": [{"artifactType": "signal", "artifactId": str(signal_id)}]},
            response_schema_name="ai_intelligence_v1",
            max_output_tokens=100,
            temperature=0,
            timeout_seconds=1,
            metadata={},
        )
    )

    assert response.output_json is not None
    assert response.output_json["insights"][0]["evidenceRefs"][0]["artifactId"] == str(signal_id)
