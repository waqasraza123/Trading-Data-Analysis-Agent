from app.modules.ai_intelligence.schemas import AiIntelligenceInputSnapshot

PROMPT_VERSION = "ai_intelligence_v1"
RESPONSE_SCHEMA_NAME = "ai_intelligence_v1"


def build_ai_intelligence_prompts(snapshot: AiIntelligenceInputSnapshot) -> tuple[str, str]:
    system_prompt = (
        "You are a backend market intelligence analyst. Produce structured advisory insights "
        "from supplied persisted artifacts only. Do not classify signals, override deterministic "
        "signals, recommend trades, imply financial advice, claim news causation, invent prices, "
        "invent indicators, invent outcomes, or suggest broker/order/position actions."
    )
    user_prompt = (
        "Return JSON with summary, insights, and limitations. Each insight must include "
        "insightType, severity, title, summary, rationale, evidenceRefs, limitations, "
        "safeFollowUpActions, and claims. Every claim must cite artifactRefs from the supplied "
        "artifactRefs list. Safe follow-up actions may only name backend investigation work and "
        "must not create or imply trading execution.\n\n"
        f"Input snapshot:\n{snapshot.model_dump_json(by_alias=True)}"
    )
    return system_prompt, user_prompt
