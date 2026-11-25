"""
Parity_Group G chunk 4/4 (spec z_aud_3, task 12.1) — GDPR admin: `admin/deletion-requests/`,
`admin/deletion-requests/{id}/`, `admin/deletion-requests/{id}/process/`,
`admin/deletion-requests/process-expired/` — the last 4 of Group G's 17 endpoints, closing out
Wave G. Contract extracted from `views/gdpr_admin_views.py` and
`serializers/gdpr_admin_serializers.py`, read in full — see `gdpr_service.py`'s `# GDPR admin`
section for the two-permission split, the real serializer fields, the dead `grace_period_expiring`
filter, the literal (not shared-helper) ordering replication, and the undocumented `"request"`
field `ProcessDeletionView`'s real success response carries.

**`request_id` path params are UUID strings here**, not Django's integer `AutoField` id — same
convention swap as every other Wave D/E/G table in this port.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from tenxyte.adapters.fastapi import gdpr_service
from tenxyte.adapters.fastapi.deps import get_db_session
from tenxyte.adapters.fastapi.errors import TenxyteAPIError
from tenxyte.adapters.fastapi.pagination import get_page_params, paginated_response
from tenxyte.adapters.fastapi.schemas import ProcessDeletionRequest
from tenxyte.adapters.fastapi.security import AuthContext, require_permission

router = APIRouter()


@router.get("/admin/deletion-requests/")
async def list_deletion_requests(
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("gdpr.admin")),  # noqa: B008
):
    page, page_size = get_page_params(request)
    rows, total = await gdpr_service.list_deletion_requests_async(
        session,
        user_id=request.query_params.get("user_id"),
        status=request.query_params.get("status"),
        date_from=request.query_params.get("date_from"),
        date_to=request.query_params.get("date_to"),
        ordering=request.query_params.get("ordering", "-requested_at"),
        page=page,
        page_size=page_size,
    )
    items = [await gdpr_service.serialize_deletion_request_async(session, r) for r in rows]
    return paginated_response(request, items=items, count=total, page=page, page_size=page_size)


@router.get("/admin/deletion-requests/{request_id}/")
async def get_deletion_request(
    request_id: str,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("gdpr.admin")),  # noqa: B008
):
    deletion_request = await gdpr_service.get_deletion_request_async(session, request_id)
    if deletion_request is None:
        raise TenxyteAPIError("Deletion request not found", code="NOT_FOUND", status_code=404)
    return await gdpr_service.serialize_deletion_request_async(session, deletion_request)


@router.post("/admin/deletion-requests/{request_id}/process/")
async def process_deletion(
    request_id: str,
    body: ProcessDeletionRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_permission("gdpr.process")),  # noqa: B008
):
    deletion_request = await gdpr_service.get_deletion_request_async(session, request_id)
    if deletion_request is None:
        raise TenxyteAPIError("Deletion request not found", code="NOT_FOUND", status_code=404)

    success, data, error, error_code = await gdpr_service.process_deletion_async(
        session,
        deletion_request,
        confirmation=body.confirmation,
        admin_notes=body.admin_notes,
        admin_id=auth.user.id,
    )
    if not success:
        status_code = 400 if error_code in ("REQUEST_NOT_CONFIRMED", "CONFIRMATION_REQUIRED") else 500
        raise TenxyteAPIError(error, code=error_code, status_code=status_code)
    return data


@router.post("/admin/deletion-requests/process-expired/")
async def process_expired_deletions(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    auth: AuthContext = Depends(require_permission("gdpr.process")),  # noqa: B008
):
    return await gdpr_service.process_expired_deletions_async(session, admin_id=auth.user.id)
