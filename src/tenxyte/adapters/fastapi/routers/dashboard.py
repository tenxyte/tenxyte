"""
Parity_Group D — Dashboard (spec z_aud_3, Wave D chunk 5/5, task 10.1): dashboard/stats,
dashboard/auth, dashboard/security, dashboard/gdpr, dashboard/organizations — the last 5 of Group
D's 46 endpoints, closing out Wave D. Contract extracted from `views/dashboard_views.py` (all 5
require `dashboard.view`, verified by reading the Django views directly) and
`services/stats_service.py`. See `dashboard_service.py`'s module docstring for why
`dashboard/gdpr/`/`dashboard/organizations/` return real-shaped but currently-zero/disabled
responses rather than querying tables that belong to not-yet-ported Parity_Groups (G, E).
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
