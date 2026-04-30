from app.config import Settings, get_settings
from app.modules.llm_adapters.registry import LlmAdapterRegistry
from app.modules.llm_adapters.schemas import LlmAdapterRequest, LlmAdapterResponse


class LlmAdapterService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.registry = LlmAdapterRegistry(self.settings)

    async def generate_structured(self, request: LlmAdapterRequest) -> LlmAdapterResponse:
        adapter = self.registry.resolve(request.provider, request.model)
        return await adapter.generate_structured(request)
