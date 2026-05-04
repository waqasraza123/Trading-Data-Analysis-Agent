from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class NotificationAdapterRequest:
    workspace_id: UUID
    event_id: UUID
    channel_id: UUID
    event_type: str
    severity: str
    title: str
    summary: str
    payload_json: dict[str, object]
    config_json: dict[str, object]
    secret_ref: str | None
    timeout_seconds: int
    user_agent: str


@dataclass(frozen=True)
class NotificationAdapterResult:
    delivered: bool
    skipped: bool
    blocked: bool
    response_status_code: int | None = None
    response_body_excerpt: str | None = None
    error_message: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)


class NotificationAdapter(ABC):
    channel_type: str

    @abstractmethod
    async def deliver(self, request: NotificationAdapterRequest) -> NotificationAdapterResult:
        raise NotImplementedError
