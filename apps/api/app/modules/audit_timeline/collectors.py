from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from app.modules.audit_timeline.schemas import (
    ArtifactEdge,
    ArtifactGraph,
    ArtifactNode,
    ArtifactRelationship,
    AuditTimelineCompleteness,
    AuditTimelineEvent,
    AuditTimelineSeverity,
    CompletenessLabel,
)

MAX_TIMELINE_EVENTS = 500
MAX_TEXT_LENGTH = 1200
MAX_LIST_ITEMS = 25
MAX_MAPPING_KEYS = 50

BANNED_TIMELINE_PHRASES = (
    "buy now",
    "sell now",
    "enter trade",
    "exit trade",
    "use leverage",
    "guaranteed profit",
    "place order",
    "execute trade",
)

SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "database_url",
    "authorization",
    "credential",
    "private_key",
)

RAW_PAYLOAD_KEY_PARTS = (
    "image_bytes",
    "image_base64",
    "raw_image",
    "screenshot_bytes",
    "screenshot_base64",
    "raw_payload",
    "provider_payload",
    "raw_provider",
    "candle_series",
    "raw_candles",
    "ohlc_rows",
)


def timeline_event(
    event_time: datetime,
    event_type: str,
    source_type: str,
    source_id: UUID | str,
    title: str,
    summary: str,
    severity: AuditTimelineSeverity = AuditTimelineSeverity.INFO,
    metadata: Mapping[str, Any] | None = None,
    include_metadata: bool = True,
) -> AuditTimelineEvent:
    return AuditTimelineEvent(
        event_time=event_time,
        event_type=event_type,
        source_type=source_type,
        source_id=str(source_id),
        title=sanitize_text(title),
        summary=sanitize_text(summary),
        severity=severity,
        metadata=(
            safe_metadata(metadata if metadata is not None else {})
            if include_metadata
            else {}
        ),
    )


def bounded_timeline(
    events: Sequence[AuditTimelineEvent],
    limit: int,
) -> list[AuditTimelineEvent]:
    capped_limit = min(limit, MAX_TIMELINE_EVENTS)
    return sorted(events, key=lambda item: item.event_time)[:capped_limit]


def completeness_from_components(components: Mapping[str, bool]) -> AuditTimelineCompleteness:
    if not components:
        score = 0.0
        missing_sections: list[str] = []
    else:
        present_count = sum(1 for present in components.values() if present)
        score = round(present_count / len(components), 4)
        missing_sections = sorted(name for name, present in components.items() if not present)
    if score >= 0.80:
        label = CompletenessLabel.COMPLETE
    elif score >= 0.45:
        label = CompletenessLabel.PARTIAL
    else:
        label = CompletenessLabel.SPARSE
    return AuditTimelineCompleteness(
        score=score,
        label=label,
        missing_sections=missing_sections,
    )


class ArtifactGraphBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, ArtifactNode] = {}
        self.edges: set[tuple[str, str, ArtifactRelationship]] = set()

    def add_node(
        self,
        artifact_id: UUID | str | None,
        artifact_type: str,
        label: str,
        status: str | None = None,
    ) -> str | None:
        if artifact_id is None:
            return None
        node_id = artifact_key(artifact_type, artifact_id)
        self.nodes[node_id] = ArtifactNode(
            id=node_id,
            type=artifact_type,
            label=sanitize_text(label),
            status=status,
        )
        return node_id

    def add_edge(
        self,
        from_id: str | None,
        to_id: str | None,
        relationship: ArtifactRelationship,
    ) -> None:
        if from_id is None or to_id is None:
            return
        self.edges.add((from_id, to_id, relationship))

    def build(self, include_graph: bool) -> ArtifactGraph:
        if not include_graph:
            return ArtifactGraph()
        return ArtifactGraph(
            nodes=list(self.nodes.values()),
            edges=[
                ArtifactEdge(from_=from_id, to=to_id, relationship=relationship)
                for from_id, to_id, relationship in sorted(
                    self.edges,
                    key=lambda item: (item[0], item[1], item[2].value),
                )
            ],
        )


def artifact_key(artifact_type: str, artifact_id: UUID | str) -> str:
    return f"{artifact_type}:{artifact_id}"


def safe_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    safe_value = to_timeline_value(value)
    return safe_value if isinstance(safe_value, dict) else {}


def to_timeline_value(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_MAPPING_KEYS:
                result["_truncated_keys"] = len(value) - MAX_MAPPING_KEYS
                break
            key_text = str(key)
            normalized_key = normalize_key(key_text)
            if any(part in normalized_key for part in SECRET_KEY_PARTS):
                result[key_text] = "[redacted]"
            elif any(part in normalized_key for part in RAW_PAYLOAD_KEY_PARTS):
                result[key_text] = summarize_raw_value(item)
            else:
                result[key_text] = to_timeline_value(item)
        return result
    if isinstance(value, list | tuple):
        items = [to_timeline_value(item) for item in value[:MAX_LIST_ITEMS]]
        if len(value) > MAX_LIST_ITEMS:
            items.append({"truncated_items": len(value) - MAX_LIST_ITEMS})
        return items
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        if looks_like_base64_payload(value):
            return "[redacted base64 payload]"
        return sanitize_text(value)
    return value


def summarize_raw_value(value: object) -> dict[str, object]:
    if isinstance(value, list):
        return {"redacted": True, "item_count": len(value)}
    if isinstance(value, Mapping):
        return {
            "redacted": True,
            "key_count": len(value),
            "keys": sorted(str(key) for key in value)[:MAX_MAPPING_KEYS],
        }
    if value is None:
        return {"redacted": True, "present": False}
    return {"redacted": True, "present": True}


def sanitize_text(value: str) -> str:
    if "traceback" in value.lower() or "stack trace" in value.lower():
        return "[redacted stack trace]"
    sanitized = value[:MAX_TEXT_LENGTH]
    if len(value) > MAX_TEXT_LENGTH:
        sanitized = f"{sanitized}...[truncated]"
    lowered = sanitized.lower()
    for phrase in BANNED_TIMELINE_PHRASES:
        while phrase in lowered:
            start = lowered.index(phrase)
            end = start + len(phrase)
            sanitized = (
                sanitized[:start]
                + "[redacted unsafe trading language]"
                + sanitized[end:]
            )
            lowered = sanitized.lower()
    return sanitized


def normalize_key(value: str) -> str:
    normalized = []
    for character in value:
        if character.isupper():
            normalized.append("_")
            normalized.append(character.lower())
        else:
            normalized.append(character.lower())
    return "".join(normalized).strip("_")


def looks_like_base64_payload(value: str) -> bool:
    if len(value) < 500:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r")
    return all(character in allowed for character in value[:1000])


def bounded_artifacts(items: Sequence[Mapping[str, Any]], limit: int) -> dict[str, Any]:
    safe_limit = min(limit, 500)
    values = [to_timeline_value(dict(item)) for item in items[:safe_limit]]
    return {
        "items": values,
        "returned_count": len(values),
        "total_count": len(items),
        "truncated": len(items) > safe_limit,
    }


def contains_banned_timeline_phrase(value: object) -> bool:
    serialized = str(to_timeline_value(value)).lower()
    return any(phrase in serialized for phrase in BANNED_TIMELINE_PHRASES)
