"""
Parity_Group D — Dashboard (spec z_aud_3, Wave D chunk 5/5, task 10.1): dashboard/stats,
dashboard/auth, dashboard/security, dashboard/gdpr, dashboard/organizations — the last 5 of Group
D's 46 endpoints, closing out Wave D. Contract extracted from `views/dashboard_views.py` (all 5
require `dashboard.view`, verified by reading the Django views directly) and
`services/stats_service.py`. `dashboard/gdpr/` now queries real data (Wave G chunk 3 wired it up
once `AccountDeletionRequestDB` landed); `dashboard/organizations/` still returns Django's own
real `{"enabled": False}` shape, since the Reference_Stack has no organizations concept disabled
by default either — see `dashboard_service.py`'s module docstring for both.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends
from tenxyte.adapters.fastapi import dashboard_service
from tenxyte.adapters.fastapi.deps import get_db_session
from tenxyte.adapters.fastapi.security import require_permission

router = APIRouter()


@router.get("/dashboard/stats/")
async def dashboard_stats(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("dashboard.view")),  # noqa: B008
):
    return await dashboard_service.get_global_stats_async(session)


@router.get("/dashboard/auth/")
async def dashboard_auth(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("dashboard.view")),  # noqa: B008
):
    return await dashboard_service.get_auth_stats_async(session)


@router.get("/dashboard/security/")
async def dashboard_security(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("dashboard.view")),  # noqa: B008
):
    return await dashboard_service.get_security_stats_async(session)


@router.get("/dashboard/gdpr/")
async def dashboard_gdpr(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("dashboard.view")),  # noqa: B008
):
    return await dashboard_service.get_gdpr_stats_async(session)


@router.get("/dashboard/organizations/")
async def dashboard_organizations(
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    _auth=Depends(require_permission("dashboard.view")),  # noqa: B008
):
    return await dashboard_service.get_organization_stats_async(session)
