from app.config import Settings, get_settings
from app.modules.llm_adapters.anthropic import AnthropicLlmAdapter
from app.modules.llm_adapters.base import LlmAdapter
from app.modules.llm_adapters.errors import UnknownLlmProviderError
from app.modules.llm_adapters.mock import MockLlmAdapter
from app.modules.llm_adapters.openai_compatible import OpenAICompatibleLlmAdapter


class LlmAdapterRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def resolve(self, provider: str | None = None, model: str | None = None) -> LlmAdapter:
        provider_key = (provider or self.settings.llm_default_provider).strip().lower()
        model_name = (model or self.settings.llm_default_model).strip()
        if provider_key == "mock":
            return MockLlmAdapter(model_name)
        if provider_key in {"openai", "openai_compatible", "openai-compatible"}:
            return OpenAICompatibleLlmAdapter(self.settings, model_name)
        if provider_key == "anthropic":
            return AnthropicLlmAdapter(self.settings, model_name)
        raise UnknownLlmProviderError(f"Unsupported LLM provider: {provider_key}")
