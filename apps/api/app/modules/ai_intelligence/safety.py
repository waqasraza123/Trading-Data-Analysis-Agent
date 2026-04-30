from app.modules.reasoning.safety import ReasoningSafetyResult, check_reasoning_safety


def check_ai_intelligence_safety(output_text: str) -> ReasoningSafetyResult:
    return check_reasoning_safety(output_text)
