"""
pytest plugin supplying `revoke_delegating_user_permission` for Tenxyte's own CI run of the
Conformance Suite (spec z_aud_2, task 4.4).

Loaded only for this job via `pytest -p spec.airs.conformance.tenxyte_ci.revoke_permission_hook`;
never shipped as part of the portable suite third parties consume. Implements the optional hook
contract documented in spec/airs/conformance/conftest.py by calling Tenxyte's own RBAC endpoint
(`DELETE {API_PREFIX}/auth/users/<id>/permissions/`) — the CI-provisioned test user is granted
`users.permissions.remove` (and `users.permissions.view`, to resolve its own id via `/me/`)
specifically so this hook can act.
"""

import httpx
import pytest


def _api_prefix(discovery):
    # Derive the mounted API prefix (e.g. "/api/v1/auth/") from the discovery document itself,
    # rather than hardcoding it, so this hook keeps working if the demo project's prefix changes.
    return discovery["endpoints"]["tokens"].rsplit("ai/tokens/", 1)[0]


def _user_id(c, api_prefix, user_jwt):
    c.headers["Authorization"] = f"Bearer {user_jwt}"
    me = c.get(f"{api_prefix}me/")
    me.raise_for_status()
    return me.json()["id"]


@pytest.fixture()
def revoke_delegating_user_permission(base_url, app_headers, discovery):
    def _revoke(user_jwt: str, permission_code: str) -> None:
        api_prefix = _api_prefix(discovery)
        with httpx.Client(base_url=base_url, headers=dict(app_headers), timeout=10) as c:
            user_id = _user_id(c, api_prefix, user_jwt)
            response = c.request(
                "DELETE",
                f"{api_prefix}users/{user_id}/permissions/",
                json={"permission_codes": [permission_code]},
            )
            response.raise_for_status()

    return _revoke


@pytest.fixture()
def grant_delegating_user_permission(base_url, app_headers, discovery):
    """
    Counterpart to `revoke_delegating_user_permission`, so tests using the revoke hook can
    restore state afterward instead of permanently mutating the shared CI user's permissions
    for every other test in the same run.
    """

    def _grant(user_jwt: str, permission_code: str) -> None:
        api_prefix = _api_prefix(discovery)
        with httpx.Client(base_url=base_url, headers=dict(app_headers), timeout=10) as c:
            user_id = _user_id(c, api_prefix, user_jwt)
            response = c.post(
                f"{api_prefix}users/{user_id}/permissions/",
                json={"permission_codes": [permission_code]},
            )
            response.raise_for_status()

    return _grant
