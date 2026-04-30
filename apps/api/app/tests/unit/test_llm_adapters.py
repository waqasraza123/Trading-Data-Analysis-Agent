import pytest

from app.config import Settings
from app.modules.llm_adapters.errors import UnknownLlmProviderError
from app.modules.llm_adapters.mock import MockLlmAdapter
from app.modules.llm_adapters.registry import LlmAdapterRegistry
from app.modules.llm_adapters.schemas import LlmAdapterRequest


def request_payload() -> LlmAdapterRequest:
    return LlmAdapterRequest(
        provider="mock",
        model="mock-scenario-v1",
        system_prompt="Use only facts.",
        user_prompt="Return JSON.",
        input_json={
            "bias": "bullish",
            "classificationStatus": "signal",
            "patternType": "breakout",
            "signalEvidence": [{"message": "Stored breakout evidence."}],
            "riskNotes": [],
            "outcomeHistory": {"items": []},
        },
        response_schema_name="scenario_reasoning_output_v1",
        max_output_tokens=450,
        temperature=0.2,
        timeout_seconds=12,
        metadata={},
    )


@pytest.mark.anyio
async def test_mock_adapter_returns_structured_response() -> None:
    response = await MockLlmAdapter().generate_structured(request_payload())

    assert response.output_json is not None
    assert response.output_json["scenarios"][0]["scenarioType"] == "continuation"
    assert response.provider == "mock"
    assert response.tokens_input is not None


def test_adapter_registry_resolves_mock_provider() -> None:
    registry = LlmAdapterRegistry(Settings(_env_file=None))

    adapter = registry.resolve("mock", "mock-scenario-v1")

    assert adapter.provider_key == "mock"


def test_adapter_registry_rejects_missing_provider() -> None:
    registry = LlmAdapterRegistry(Settings(_env_file=None))

    with pytest.raises(UnknownLlmProviderError):
        registry.resolve("missing", "model")
