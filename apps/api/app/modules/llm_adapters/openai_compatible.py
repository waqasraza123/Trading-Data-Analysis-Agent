from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from urllib import error, request

from app.config import Settings, secret_is_empty
from app.modules.llm_adapters.errors import LlmAdapterError, LlmProviderNotConfiguredError
from app.modules.llm_adapters.schemas import LlmAdapterRequest, LlmAdapterResponse


class OpenAICompatibleLlmAdapter:
    provider_key = "openai_compatible"

    def __init__(self, settings: Settings, model_name: str) -> None:
        if secret_is_empty(settings.openai_api_key):
            raise LlmProviderNotConfiguredError(
                "OPENAI_API_KEY is required for OpenAI-compatible provider"
            )
        if settings.openai_api_key is None:
            raise LlmProviderNotConfiguredError(
                "OPENAI_API_KEY is required for OpenAI-compatible provider"
            )
        self.api_key = settings.openai_api_key.get_secret_value()
        self.base_url = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        self.model_name = model_name

    async def generate_structured(self, adapter_request: LlmAdapterRequest) -> LlmAdapterResponse:
        return await asyncio.to_thread(self._generate_sync, adapter_request)

    def _generate_sync(self, adapter_request: LlmAdapterRequest) -> LlmAdapterResponse:
        started = time.perf_counter()
        body = json.dumps(
            {
                "model": adapter_request.model,
                "messages": [
                    {"role": "system", "content": adapter_request.system_prompt},
                    {"role": "user", "content": adapter_request.user_prompt},
                ],
                "temperature": adapter_request.temperature,
                "max_tokens": adapter_request.max_output_tokens,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        api_request = request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(api_request, timeout=adapter_request.timeout_seconds) as response:
                raw_payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raise LlmAdapterError(
                f"OpenAI-compatible provider request failed with {exc.code}"
            ) from exc
        except error.URLError as exc:
            raise LlmAdapterError("OpenAI-compatible provider request failed") from exc
        payload = json.loads(raw_payload)
        if not isinstance(payload, dict):
            raise LlmAdapterError("OpenAI-compatible provider returned invalid JSON")
        output_text = extract_chat_output_text(payload)
        output_json = parse_output_json(output_text)
        usage = payload.get("usage")
        tokens_input: int | None = None
        tokens_output: int | None = None
        if isinstance(usage, dict):
            tokens_input = optional_int(usage.get("prompt_tokens"))
            tokens_output = optional_int(usage.get("completion_tokens"))
        return LlmAdapterResponse(
            provider=adapter_request.provider,
            model=adapter_request.model,
            output_text=output_text,
            output_json=output_json,
            finish_reason=extract_finish_reason(payload),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            raw_response_json=safe_metadata(payload),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )


def extract_chat_output_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LlmAdapterError("OpenAI-compatible response did not include choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise LlmAdapterError("OpenAI-compatible choice was invalid")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise LlmAdapterError("OpenAI-compatible choice did not include a message")
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    raise LlmAdapterError("OpenAI-compatible response did not include output text")


def parse_output_json(output_text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def extract_finish_reason(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        finish_reason = choices[0].get("finish_reason")
        if isinstance(finish_reason, str):
            return finish_reason
    return None


def safe_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in ("id", "model", "created", "usage"):
        value = payload.get(key)
        if isinstance(value, str | int | float | bool | dict):
            metadata[key] = value
    return metadata


def optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None
