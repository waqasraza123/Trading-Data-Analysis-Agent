from app.config import Settings
from app.modules.llm_adapters.errors import LlmProviderNotConfiguredError
from app.modules.llm_adapters.schemas import LlmAdapterRequest, LlmAdapterResponse


class AnthropicLlmAdapter:
    provider_key = "anthropic"

    def __init__(self, settings: Settings, model_name: str) -> None:
        self.settings = settings
        self.model_name = model_name

    async def generate_structured(self, request: LlmAdapterRequest) -> LlmAdapterResponse:
        raise LlmProviderNotConfiguredError(
            "Anthropic adapter integration point exists, but provider calls are not enabled"
        )
