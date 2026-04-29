from fastapi import Request

from app.core.errors import get_request_id


def current_request_id(request: Request) -> str:
    return get_request_id(request)
