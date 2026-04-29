from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def create_error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    error_response = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=get_request_id(request),
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def handle_http_exception(request: Request, exception: Exception) -> JSONResponse:
    if not isinstance(exception, HTTPException):
        return await handle_unexpected_exception(request, exception)
    message = (
        str(exception.detail) if exception.detail else HTTPStatus(exception.status_code).phrase
    )
    return create_error_response(
        request=request,
        status_code=exception.status_code,
        code="http_error",
        message=message,
    )


async def handle_validation_exception(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, RequestValidationError):
        return await handle_unexpected_exception(request, exception)
    validation_details = [
        {
            "location": [str(location_part) for location_part in error["loc"]],
            "message": str(error["msg"]),
            "type": str(error["type"]),
        }
        for error in exception.errors()
    ]
    return create_error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=validation_details,
    )


async def handle_unexpected_exception(request: Request, exception: Exception) -> JSONResponse:
    request.app.state.logger.exception(
        "unexpected_error",
        extra={"request_id": get_request_id(request)},
    )
    return create_error_response(
        request=request,
        status_code=500,
        code="internal_error",
        message="Unexpected server error",
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_exception)
    app.add_exception_handler(Exception, handle_unexpected_exception)
