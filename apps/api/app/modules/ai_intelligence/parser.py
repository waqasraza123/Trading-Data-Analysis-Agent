from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.modules.action_plans.validation import ALLOWED_ACTIONS, TRADING_ACTIONS
from app.modules.ai_intelligence.models import (
    AiIntelligenceClaimSupportStatus,
    AiIntelligenceInsightType,
    AiIntelligenceSeverity,
)
from app.modules.ai_intelligence.schemas import (
    AiArtifactRef,
    AiClaimOutput,
    AiInsightOutput,
    ParsedAiIntelligence,
)
from app.modules.llm_adapters.schemas import LlmAdapterResponse


def parse_ai_intelligence_output(adapter_response: LlmAdapterResponse) -> ParsedAiIntelligence:
    payload = adapter_response.output_json or parse_text_json(adapter_response.output_text)
    if payload is None:
        return fallback_parsed("model_output_was_not_json")
    try:
        return parse_payload(payload)
    except (TypeError, ValueError, ValidationError) as exc:
        return fallback_parsed(str(exc))


def parse_payload(payload: dict[str, Any]) -> ParsedAiIntelligence:
    summary = string_value(payload.get("summary"), "AI intelligence fallback was used.")
    raw_insights = payload.get("insights")
    if not isinstance(raw_insights, list) or not raw_insights:
        raise ValueError("insights must contain at least one item")
    insights = [parse_insight(item) for item in raw_insights if isinstance(item, dict)]
    if not insights:
        raise ValueError("insights must contain object items")
    return ParsedAiIntelligence(
        summary=summary,
        insights=insights,
        limitations=string_list(payload.get("limitations")),
    )


def parse_insight(item: dict[str, Any]) -> AiInsightOutput:
    actions = normalize_safe_actions(item.get("safeFollowUpActions"))
    refs = parse_refs(item.get("evidenceRefs"))
    claims = [parse_claim(claim) for claim in list_value(item.get("claims"))]
    return AiInsightOutput(
        insight_type=insight_type(item.get("insightType")),
        severity=severity(item.get("severity")),
        title=string_value(item.get("title"), "Grounded intelligence insight"),
        summary=string_value(item.get("summary"), "Review persisted artifacts directly."),
        rationale=string_value(item.get("rationale"), "Derived from cited persisted artifacts."),
        evidence_refs=refs,
        limitations=string_list(item.get("limitations")),
        safe_follow_up_actions=actions,
        claims=claims,
    )


def parse_claim(item: object) -> AiClaimOutput:
    if not isinstance(item, dict):
        raise ValueError("claim item must be an object")
    return AiClaimOutput(
        claim=string_value(item.get("claim"), "Review cited artifact."),
        evidence_refs=parse_refs(item.get("evidenceRefs")),
        support_status=support_status(item.get("supportStatus")),
    )


def parse_refs(value: object) -> list[AiArtifactRef]:
    refs: list[AiArtifactRef] = []
    for item in list_value(value):
        if not isinstance(item, dict):
            continue
        artifact_type = string_value(item.get("artifactType"), "")
        artifact_id = item.get("artifactId")
        if artifact_type and artifact_id:
            refs.append(
                AiArtifactRef(
                    artifact_type=artifact_type,
                    artifact_id=artifact_id,
                    label=item.get("label") if isinstance(item.get("label"), str) else None,
                )
            )
    return refs


def normalize_safe_actions(value: object) -> list[str]:
    actions = string_list(value)
    output: list[str] = []
    for action in actions:
        normalized = action.strip().lower()
        if normalized in TRADING_ACTIONS:
            raise ValueError(f"trading action is not allowed: {action}")
        if normalized not in ALLOWED_ACTIONS:
            raise ValueError(f"unknown backend action: {action}")
        output.append(normalized)
    return output


def fallback_parsed(reason: str) -> ParsedAiIntelligence:
    return ParsedAiIntelligence(
        summary="The AI intelligence output could not be safely parsed.",
        insights=[
            AiInsightOutput(
                insight_type=AiIntelligenceInsightType.DATA_GAP,
                severity=AiIntelligenceSeverity.INFO,
                title="AI intelligence fallback",
                summary="Review persisted deterministic artifacts directly.",
                rationale="The model output failed parser validation.",
                evidence_refs=[],
                limitations=[reason],
                safe_follow_up_actions=["request_human_review"],
                claims=[],
            )
        ],
        limitations=[reason],
        fallback_used=True,
        error_message=reason,
    )


def parse_text_json(output_text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def insight_type(value: object) -> AiIntelligenceInsightType:
    if not isinstance(value, str):
        raise ValueError("insightType must be a string")
    return AiIntelligenceInsightType(value)


def severity(value: object) -> AiIntelligenceSeverity:
    if not isinstance(value, str):
        raise ValueError("severity must be a string")
    return AiIntelligenceSeverity(value)


def support_status(value: object) -> AiIntelligenceClaimSupportStatus:
    if not isinstance(value, str):
        return AiIntelligenceClaimSupportStatus.SUPPORTED
    return AiIntelligenceClaimSupportStatus(value)


def string_value(value: object, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def string_list(value: object) -> list[str]:
    return [item.strip() for item in list_value(value) if isinstance(item, str) and item.strip()]


def list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []
