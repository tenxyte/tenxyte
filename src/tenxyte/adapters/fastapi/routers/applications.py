"""
Parity_Group D — Applications (spec z_aud_3, Wave D chunk 2/5, task 10.1): applications/* — 7 of
Group D's 46 endpoints. Contract extracted from `views/application_views.py`,
`serializers/application_serializers.py`, and `filters.py`'s `apply_application_filters`. Reuses
`ApplicationDB` (created in Wave A for `X-Access-Key`/`X-Access-Secret` auth — see
`application_auth.py`) rather than a new table; a Wave A follow-up column set
(`description`/`updated_at`) was added to `models_sa.py` alongside this chunk since the original
Wave A columns only covered what `ApplicationAuthMiddleware` itself needed, not the full CRUD
surface this router exposes.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi import application_service
from tenxyte.adapters.fastapi.deps import get_db_session
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.pagination import get_page_params, paginated_response
from tenxyte.adapters.fastapi.schemas import (
    ApplicationCreateRequest,
    ApplicationRegenerateRequest,
    ApplicationToggleRequest,
    ApplicationUpdateRequest,
)
from tenxyte.adapters.fastapi.security import require_permission

router = APIRouter()


@router.get("/applications/")
async def list_applications(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("applications.view")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    is_active_param = request.query_params.get("is_active")
    is_active = None
    if is_active_param is not None:
        is_active = is_active_param.lower() in ("true", "1", "yes")

    rows, total = await application_service.list_applications_async(
        session,
        search=request.query_params.get("search", "").strip(),
        is_active=is_active,
        ordering=request.query_params.get("ordering", "name"),
        page=page,
        page_size=page_size,
    )
    items = [application_service.serialize_application(a) for a in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.post("/applications/", status_code=201)
async def create_application(
    body: ApplicationCreateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("applications.create")),  # noqa: B008
):
    app, raw_secret = await application_service.create_application_async(
        session, name=body.name, description=body.description, allowed_origins=body.allowed_origins
    )
    return {
        "message": "Application created successfully",
        "application": application_service.serialize_application(app),
        "credentials": {"access_key": app.access_key, "access_secret": raw_secret},
        "warning": "Save the access_secret now! It will never be shown again.",
    }


@router.get("/applications/{app_id}/")
async def get_application(
    app_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("applications.view")),  # noqa: B008
):
    app = await application_service.get_application_by_id_async(session, app_id)
    if app is None:
        raise TenxyteAPIError("Application not found", code="NOT_FOUND", status_code=404)
    return application_service.serialize_application(app)


@router.put("/applications/{app_id}/")
async def update_application(
    app_id: str,
    body: ApplicationUpdateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("applications.update")),  # noqa: B008
):
    app = await application_service.get_application_by_id_async(session, app_id)
    if app is None:
        raise TenxyteAPIError("Application not found", code="NOT_FOUND", status_code=404)
    updated = await application_service.update_application_async(
        session,
        app,
        name=body.name,
        description=body.description,
        is_active=body.is_active,
        allowed_origins=body.allowed_origins,
    )
    return application_service.serialize_application(updated)


@router.patch("/applications/{app_id}/")
async def toggle_application(
    app_id: str,
    body: ApplicationToggleRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("applications.update")),  # noqa: B008
):
    app = await application_service.get_application_by_id_async(session, app_id)
    if app is None:
        raise TenxyteAPIError("Application not found", code="NOT_FOUND", status_code=404)

    if body.is_active is None:
        raise TenxyteAPIError("No valid fields provided", code="INVALID_FIELDS", status_code=400)

    updated = await application_service.toggle_application_active_async(session, app, body.is_active)
    action = "activated" if body.is_active else "deactivated"
    return {
        "message": f"Application {action} successfully",
        "application": application_service.serialize_application(updated),
    }


@router.delete("/applications/{app_id}/")
async def delete_application(
    app_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("applications.delete")),  # noqa: B008
):
    app = await application_service.get_application_by_id_async(session, app_id)
    if app is None:
        raise TenxyteAPIError("Application not found", code="NOT_FOUND", status_code=404)
    app_name = app.name
    await application_service.delete_application_async(session, app)
    return {"message": f'Application "{app_name}" deleted successfully'}


@router.post("/applications/{app_id}/regenerate/")
async def regenerate_application_credentials(
    app_id: str,
    body: ApplicationRegenerateRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("applications.regenerate")),  # noqa: B008
):
    if body.confirmation != "REGENERATE":
        raise TenxyteAPIError("Confirmation required", code="CONFIRMATION_REQUIRED", status_code=400)

    app = await application_service.get_application_by_id_async(session, app_id)
    if app is None:
        raise TenxyteAPIError("Application not found", code="NOT_FOUND", status_code=404)

    credentials = await application_service.regenerate_credentials_async(session, app)
    return {
        "message": "Credentials regenerated successfully",
        "application": application_service.serialize_application(app),
        "credentials": credentials,
        "warning": "Save the access_secret now! It will never be shown again.",
        "old_credentials_invalidated": True,
    }
