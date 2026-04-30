from dataclasses import dataclass

from app.modules.ai_intelligence.models import AiIntelligenceGroundingStatus
from app.modules.ai_intelligence.schemas import AiArtifactRef, ParsedAiIntelligence


@dataclass(frozen=True)
class AiIntelligenceGroundingResult:
    status: AiIntelligenceGroundingStatus
    issues: list[str]


def check_ai_intelligence_grounding(
    allowed_refs: list[AiArtifactRef],
    parsed: ParsedAiIntelligence,
) -> AiIntelligenceGroundingResult:
    allowed = {(ref.artifact_type, str(ref.artifact_id)) for ref in allowed_refs}
    issues: list[str] = []
    for insight_index, insight in enumerate(parsed.insights):
        if not insight.evidence_refs:
            issues.append(f"insight {insight_index} has no evidence refs")
        for ref in insight.evidence_refs:
            if (ref.artifact_type, str(ref.artifact_id)) not in allowed:
                issues.append(f"insight {insight_index} cites unknown artifact")
        for claim_index, claim in enumerate(insight.claims):
            if not claim.evidence_refs:
                issues.append(f"claim {insight_index}.{claim_index} has no evidence refs")
            for ref in claim.evidence_refs:
                if (ref.artifact_type, str(ref.artifact_id)) not in allowed:
                    issues.append(f"claim {insight_index}.{claim_index} cites unknown artifact")
    if issues:
        return AiIntelligenceGroundingResult(AiIntelligenceGroundingStatus.FAILED, issues)
    return AiIntelligenceGroundingResult(AiIntelligenceGroundingStatus.GROUNDED, [])
