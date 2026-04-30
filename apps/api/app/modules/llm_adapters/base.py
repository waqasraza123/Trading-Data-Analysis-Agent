from typing import Protocol

from app.modules.llm_adapters.schemas import LlmAdapterRequest, LlmAdapterResponse


class LlmAdapter(Protocol):
    provider_key: str
    model_name: str

    async def generate_structured(self, request: LlmAdapterRequest) -> LlmAdapterResponse:
        raise NotImplementedError
