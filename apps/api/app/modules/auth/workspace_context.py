from uuid import UUID

from fastapi import Request

WORKSPACE_FIELD_NAMES = ("workspace_id", "workspaceId")


async def resolve_request_workspace_id(request: Request) -> UUID | None:
    for value in request.path_params.values():
        parsed = parse_uuid(value)
        if parsed is not None and "workspace" in request.url.path:
            return parsed
    for name in WORKSPACE_FIELD_NAMES:
        value = request.query_params.get(name)
        parsed = parse_uuid(value)
        if parsed is not None:
            return parsed
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        body = await read_json_body(request)
        parsed = extract_workspace_id(body)
        if parsed is not None:
            return parsed
    header_name = request.app.state.settings.workspace_context_header_name
    return parse_uuid(request.headers.get(header_name))


async def read_json_body(request: Request) -> object:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return None
    try:
        return await request.json()
    except Exception:
        return None


def extract_workspace_id(value: object) -> UUID | None:
    if isinstance(value, dict):
        for name in WORKSPACE_FIELD_NAMES:
            parsed = parse_uuid(value.get(name))
            if parsed is not None:
                return parsed
        for nested_value in value.values():
            parsed = extract_workspace_id(nested_value)
            if parsed is not None:
                return parsed
    if isinstance(value, list):
        for item in value:
            parsed = extract_workspace_id(item)
            if parsed is not None:
                return parsed
    return None


def parse_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return UUID(value.strip())
    except ValueError:
        return None
