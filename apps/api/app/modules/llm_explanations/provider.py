from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from urllib import error, request

from app.config import Settings, secret_is_empty


class LlmProviderError(RuntimeError):
    pass


class ProviderNotConfiguredError(LlmProviderError):
    pass


@dataclass(frozen=True)
class LlmExplanationInput:
    prompt: str
    input_json: dict[str, object]


@dataclass(frozen=True)
class LlmProviderResult:
    output_text: str
    tokens_input: int | None = None
    tokens_output: int | None = None
    estimated_cost: Decimal | None = None
    raw_response_json: dict[str, object] | None = None


class LlmProvider(Protocol):
    async def generate_explanation(self, input_payload: LlmExplanationInput) -> LlmProviderResult:
        raise NotImplementedError


class MockLlmProvider:
    def __init__(self, output_text: str | None = None) -> None:
        self.output_text = output_text

    async def generate_explanation(self, input_payload: LlmExplanationInput) -> LlmProviderResult:
        payload = input_payload.input_json
        status = str(payload.get("classification_status", "unknown"))
        bias = str(payload.get("bias", "unknown"))
        confidence = payload.get("confidence")
        confidence_label = "unknown"
        if isinstance(confidence, dict):
            confidence_label = str(confidence.get("label", "unknown"))
        output_text = self.output_text or (
            "Summary paragraph: The deterministic backend classified this analysis as "
            f"{status} with {bias} bias, using only the persisted signal artifacts. "
            "Evidence explanation: The explanation is grounded in stored evidence rows, "
            "confidence components, and the deterministic explanation snapshot. "
            f"Confidence explanation: The persisted confidence label is {confidence_label}. "
            "Risk/uncertainty explanation: Risk notes and no-signal context should be "
            "reviewed where present, and the result remains uncertain. "
            "This is analysis based on available backend data, not a trade instruction."
        )
        return LlmProviderResult(
            output_text=output_text,
            tokens_input=_rough_token_count(input_payload.prompt),
            tokens_output=_rough_token_count(output_text),
        )


class OpenAILlmProvider:
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, settings: Settings) -> None:
        if secret_is_empty(settings.openai_api_key):
            raise ProviderNotConfiguredError("OPENAI_API_KEY is required for provider openai")
        if settings.openai_api_key is None:
            raise ProviderNotConfiguredError("OPENAI_API_KEY is required for provider openai")
        self.api_key = settings.openai_api_key.get_secret_value()
        self.model = settings.llm_model
        self.timeout_seconds = settings.llm_timeout_seconds
        self.max_output_tokens = settings.llm_max_output_tokens

    async def generate_explanation(self, input_payload: LlmExplanationInput) -> LlmProviderResult:
        return await asyncio.to_thread(self._generate_sync, input_payload)

    def _generate_sync(self, input_payload: LlmExplanationInput) -> LlmProviderResult:
        body = json.dumps(
            {
                "model": self.model,
                "input": input_payload.prompt,
                "max_output_tokens": self.max_output_tokens,
            }
        ).encode("utf-8")
        api_request = request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:
                raw_payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raise LlmProviderError(f"OpenAI provider request failed with {exc.code}") from exc
        except error.URLError as exc:
            raise LlmProviderError("OpenAI provider request failed") from exc
        payload = json.loads(raw_payload)
        if not isinstance(payload, dict):
            raise LlmProviderError("OpenAI provider returned an invalid response")
        output_text = extract_openai_output_text(payload)
        usage = payload.get("usage")
        tokens_input: int | None = None
        tokens_output: int | None = None
        if isinstance(usage, dict):
            tokens_input = optional_int(usage.get("input_tokens"))
            tokens_output = optional_int(usage.get("output_tokens"))
        return LlmProviderResult(
            output_text=output_text,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            raw_response_json=safe_openai_metadata(payload),
        )


def build_provider(settings: Settings) -> LlmProvider:
    provider = settings.llm_provider.strip().lower()
    if provider == "mock":
        return MockLlmProvider()
    if provider == "openai":
        return OpenAILlmProvider(settings)
    raise ProviderNotConfiguredError(f"Unsupported LLM provider: {provider}")


def extract_openai_output_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    output = payload.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        if parts:
            return "\n".join(parts).strip()
    raise LlmProviderError("OpenAI provider response did not include output text")


def safe_openai_metadata(payload: dict[str, Any]) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for key in ("id", "model", "created_at", "status", "usage"):
        value = payload.get(key)
        if isinstance(value, (str, int, float, bool, dict)):
            metadata[key] = value
    return metadata


def optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _rough_token_count(value: str) -> int:
    return max(1, len(value.split()))
