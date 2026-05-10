from app.modules.llm_explanations.schemas import LlmExplanationInputPayload

PROMPT_VERSION = "grounded_v1"


def build_llm_prompt(input_payload: LlmExplanationInputPayload) -> str:
    return (
        "You are explaining a precomputed deterministic market analysis.\n"
        "Do not classify direction, do not change the signal, do not invent new values, "
        "and do not provide financial advice.\n"
        "Use only the supplied structured artifacts. Mention uncertainty and risk notes "
        "where present.\n"
        "Do not say buy, sell, enter, exit, must enter, take this trade, use leverage, "
        "or guarantee outcomes.\n"
        "Keep language cautious and avoid causation claims that go beyond deterministic evidence.\n"
        "If news/event correlations are present, describe them only as possible correlations. "
        "Do not say an event definitely caused, confirmed, or guaranteed the move.\n"
        "If no news/event correlations are present, do not mention news, events, announcements, "
        "or headlines.\n"
        "For no_signal or unclear cases, explain what prevented a directional signal.\n"
        "Do not use markdown tables.\n"
        "\n"
        "Input artifacts:\n"
        f"{input_payload.model_dump(mode='json')}\n"
        "\n"
        "Output format:\n"
        "Summary paragraph: concise explanation of directional result and context.\n"
        "Evidence explanation: describe key evidence rows and confidence components used.\n"
        "Confidence explanation: explain confidence level and why.\n"
        "Risk/uncertainty explanation: explain risk notes and uncertainty.\n"
        "Include this disclaimer exactly once: "
        '"This is analysis based on available backend data, not a trade instruction."\n'
        "Use plain text only."
    )
