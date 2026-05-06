from app.config import Settings
from app.modules.observability.schemas import TracingStatusRead


def tracing_status(settings: Settings) -> TracingStatusRead:
    enabled = settings.tracing_enabled
    return TracingStatusRead(
        enabled=enabled,
        provider_required_at_startup=False,
        mode="local_hooks" if enabled else "disabled",
        hooks=[
            "request_id",
            "request_duration",
            "request_status",
            "optional_trace_context",
        ],
        service=settings.service_name,
        notes=[
            "Tracing hooks do not require an external provider at startup.",
            "No request bodies, secrets, API keys, tokens, or database URLs are captured.",
        ],
    )
