"""Stable, non-sensitive API error responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid4().hex))


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message, "request_id": _request_id(request)}
    if details:
        error["details"] = details
    response = JSONResponse(status_code=status_code, content={"error": error})
    response.headers["X-Request-ID"] = error["request_id"]
    return response


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        safe_details = [
            {
                "location": [str(part) for part in error.get("loc", ())],
                "message": "Invalid value.",
                "type": str(error.get("type", "value_error")),
            }
            for error in exc.errors()
        ]
        return error_response(
            request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            details=safe_details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        common = {
            401: ("authentication_required", "Authentication is required."),
            403: ("not_authorized", "You are not authorized to perform this action."),
            404: ("not_found", "The requested resource was not found."),
            405: ("method_not_allowed", "The requested method is not allowed."),
        }
        code, message = common.get(
            exc.status_code,
            ("request_error", "The request could not be completed."),
        )
        return error_response(request, status_code=exc.status_code, code=code, message=message)
