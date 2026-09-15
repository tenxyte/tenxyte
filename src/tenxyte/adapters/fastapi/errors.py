"""
Canonical error format for the FastAPI_Adapter (spec z_aud_3, Requirement 3.6).

Every error response — including ones FastAPI/Starlette produce natively (422 validation, 404,
405, ...) — is normalized to `{"error": ..., "code": ..., "details": ...}` (`details` omitted
when there is none), the same shape the Django_Adapter uses throughout its views. Registered via
`register_exception_handlers(app)` in the App_Factory.

`code` is itself omittable (`TenxyteAPIError(..., code=None)`) for the rare Django view whose real
error responses genuinely never carry one — verified by reading the actual `return Response(...)`
call sites, not assumed from `@extend_schema`/`OpenApiExample` docs that invent a `code` Django
never emits (Parity_Group E's `organization_views.py`/`services/organization_service.py` errors
are the first case of this in the port; see `org_service.py`'s module docstring). Every other
Wave A-D error path does carry a real `code`, so this stays the exception, not a new default.
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.exceptions import HTTPException as StarletteHTTPException

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class TenxyteAPIError(Exception):
    """Raise this from a handler/dependency to produce a canonical error response directly,
    without going through an `HTTPException`'s single free-form `detail` string.

    `extra` merges additional top-level fields into the response body, alongside `error`/`code`/
    `details` — needed for parity with a few Django_Adapter error responses that carry more than
    just those three (e.g. `login/email/`'s 423 also reports `retry_after`, and its 401
    `2FA_REQUIRED` also reports `requires_2fa: true`). Left as `None` (the default) for every
    error that only needs the base three fields.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        self.extra = extra


class AgentClearancePending(Exception):
    """Raised by `airs_clearance.require_agent_clearance` (spec z_aud_3, Wave F, task 9.2) to
    short-circuit a business endpoint with AIRS/1.0's [AIRS-HITL-3] `202 pending_confirmation`
    contract — the FastAPI equivalent of the Django_Adapter's `@require_agent_clearance` decorator
    returning early instead of calling the wrapped view."""

    def __init__(self, confirmation_token: str, expires_at: str):
        super().__init__("Action requires human approval")
        self.confirmation_token = confirmation_token
        self.expires_at = expires_at


def _canonical_body(
    error: str, code: str | None, details: Any = None, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"error": error}
    if code is not None:
        body["code"] = code
    if details is not None:
        body["details"] = details
    if extra:
        body.update(extra)
    return body


async def _handle_tenxyte_error(request: Request, exc: TenxyteAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content=_canonical_body(exc.message, exc.code, exc.details, exc.extra)
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 (FastAPI/Pydantic's native validation failure) -> canonical 400, per design.md's error
    table — parity with the Django_Adapter's `{"error": "Validation error", "details": ...}`.

    **`exc.errors()` is run through `jsonable_encoder` before it reaches `JSONResponse`** — a
    real, previously-undiscovered bug found via a user's own manual testing, reproduced directly
    (not just read): `exc.errors()`'s `"input"` field echoes back the raw value Pydantic actually
    received, which for a body that never parsed as JSON to begin with (e.g. a client sending the
    wrong `Content-Type`, as PowerShell's `curl` alias — really `Invoke-WebRequest` — does by
    default) is the literal raw `bytes` payload. `JSONResponse.render()` uses the stdlib's
    `json.dumps()`, which cannot serialize `bytes` — so this handler itself crashed with
    `TypeError: Object of type bytes is not JSON serializable`, turning an intended clean 400
    `VALIDATION_ERROR` into an unhandled 500 `INTERNAL_ERROR` instead. `jsonable_encoder` (already
    a FastAPI dependency, no new import) safely converts `bytes` and any other non-JSON-native
    value `exc.errors()` might carry to a JSON-safe representation."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_canonical_body("Validation error", "VALIDATION_ERROR", details=jsonable_encoder(exc.errors())),
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # An HTTPException already carrying a canonical dict (error+code) is passed through as-is;
    # a bare string `detail` (FastAPI's/Starlette's own default, e.g. 404/405) is wrapped.
    if isinstance(exc.detail, dict) and "error" in exc.detail and "code" in exc.detail:
        content = exc.detail
    else:
        content = _canonical_body(str(exc.detail), f"HTTP_{exc.status_code}")
    return JSONResponse(status_code=exc.status_code, content=content, headers=getattr(exc, "headers", None))


async def _handle_agent_clearance_pending(request: Request, exc: AgentClearancePending) -> JSONResponse:
    return JSONResponse(
        status_code=202,
        content={
            "status": "pending_confirmation",
            "message": "This action requires human approval.",
            "confirmation_token": exc.confirmation_token,
            "expires_at": exc.expires_at,
        },
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Never leak internals — the same fail-closed posture as the Django_Adapter's generic 500s.
    logger.exception("Unhandled exception in FastAPI_Adapter request")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_canonical_body("An unexpected error occurred.", "INTERNAL_ERROR"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(TenxyteAPIError, _handle_tenxyte_error)
    app.add_exception_handler(AgentClearancePending, _handle_agent_clearance_pending)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
