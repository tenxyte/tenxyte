"""
Contract_Suite — Parity_Group D / RBAC+applications+admin+dashboard (spec z_aud_3, task 10.2):
the same assertions, written once against the `api` fixture, run unchanged against both the
Django_Adapter and the FastAPI_Adapter.

Narrower than Groups A-C's contract coverage, for the same reason already documented in
`test_group_f_shapes.py`: every one of Group D's 46 endpoints requires a specific RBAC permission
(`users.view`, `applications.view`, `security.view`, `dashboard.view`, ...), and proving the
*successful* (permission-granted) response shape on both backends would need a Delegating User
that genuinely holds the permission on both — Django's real RBAC (roles/direct grants) versus the
Reference_Stack's `is_superuser`-only bypass for `require_permission` (documented as a foundational
Wave F/D design constraint). The `api` fixture has no shared way to promote a freshly
`register_and_login()`-ed user to either state yet.

What *is* provable identically on both backends without that promotion — and is exactly what this
file proves, across one representative endpoint per Wave D chunk
(`/permissions/`, `/applications/`, `/admin/users/`, `/admin/audit-logs/`, `/dashboard/stats/`) —
is that the auth/permission *gate* itself produces the same canonical shape on both adapters: a
missing token is rejected identically (`AUTH_REQUIRED`), and an authenticated-but-unprivileged
caller is rejected identically (`PERMISSION_REQUIRED`, the generic non-verbose message, matching
`decorators._get_permission_denied_response`'s default `VERBOSE_ERRORS=False` posture exactly the
same way `rbac_service`/`admin_user_service`/etc. replicate it on the FastAPI side). Full
Group D behavior itself (successful listings, filters, CRUD) is already covered per-chunk by each
router's own dedicated test suite (`test_rbac_router.py`, `test_applications_router.py`,
`test_admin_users_router.py`, `test_admin_security_router.py`, `test_dashboard_router.py`) — this
file's job is only to prove the two adapters agree on the gate, not to re-prove each chunk's
internal logic a second time.
"""

import pytest

from tests.contract.conftest import register_and_login

_GROUP_D_REPRESENTATIVE_PATHS = [
    "/permissions/",
    "/applications/",
    "/admin/users/",
    "/admin/audit-logs/",
    "/dashboard/stats/",
]


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
@pytest.mark.parametrize("path", _GROUP_D_REPRESENTATIVE_PATHS)
async def test_group_d_endpoint_requires_auth_identically(api, path):
    response = await api.get(path)

    assert response.status_code == 401
    assert response.body == {"error": "Authorization header required", "code": "AUTH_REQUIRED"}


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
@pytest.mark.parametrize("path", _GROUP_D_REPRESENTATIVE_PATHS)
async def test_group_d_endpoint_rejects_unprivileged_user_identically(api, path):
    access_token, _email = await register_and_login(api)

    response = await api.get(path, headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 403
    assert response.body == {"error": "Permission denied.", "code": "PERMISSION_REQUIRED"}
