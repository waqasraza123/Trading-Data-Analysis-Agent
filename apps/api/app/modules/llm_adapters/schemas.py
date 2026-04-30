from decimal import Decimal
from typing import Any

from app.core.schemas import ApiSchema


class LlmAdapterRequest(ApiSchema):
    provider: str
    model: str
    system_prompt: str
    user_prompt: str
    input_json: dict[str, Any]
    response_schema_name: str
    max_output_tokens: int
    temperature: float
    timeout_seconds: float
    metadata: dict[str, Any]


class LlmAdapterResponse(ApiSchema):
    provider: str
    model: str
    output_text: str
    output_json: dict[str, Any] | None = None
    finish_reason: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    estimated_cost: Decimal | None = None
    raw_response_json: dict[str, Any] | None = None
    latency_ms: int | None = None
