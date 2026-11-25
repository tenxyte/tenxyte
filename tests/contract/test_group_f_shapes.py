"""
Contract_Suite — Parity_Group F / AIRS (spec z_aud_3, task 9.3): the same assertions, written
once against the `api` fixture, run unchanged against both the Django_Adapter and the
FastAPI_Adapter.

Narrower than Groups A-C's contract coverage: exercising `ai/tokens/` (create) here would need a
Delegating User who genuinely holds the requested permission on *both* backends — Django's real
RBAC (roles/direct grants) versus the Reference_Stack's `is_superuser`-only bypass (see
`airs_service.py`'s module docstring) — and the `api` fixture has no shared way to promote a
freshly `register_and_login()`-ed user to either state yet. Left for a future extension rather
than built as a one-off hack here; the AIRS Conformance Suite (task 9.2) already exhaustively
exercises token issuance end-to-end against both adapters, including Double Validation, so this
isn't a coverage gap for the *behavior* — only for the Contract_Suite's own reach.
"""

import pytest

from tests.contract.shapes import AIRS_DISCOVERY_FIELDS


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_discovery_has_documented_fields(api):
    response = await api.get("/ai/.well-known/airs/")

    assert response.status_code == 200
    for field in AIRS_DISCOVERY_FIELDS:
        assert field in response.body, f"Required field '{field}' missing from /ai/.well-known/airs/ response"
    assert response.body["airs_version"] == "1.0"
    assert "core" in response.body["conformance"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_discovery_identical_for_anonymous_and_authenticated_caller(api):
    """[AIRS-DISC-2]: the discovery document must not depend on caller identity."""
    from tests.contract.conftest import register_and_login

    access_token, _email = await register_and_login(api)

    anon = await api.get("/ai/.well-known/airs/")
    authed = await api.get("/ai/.well-known/airs/", headers={"Authorization": f"Bearer {access_token}"})

    assert anon.status_code == authed.status_code == 200
    assert anon.body == authed.body


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_token_list_requires_auth_on_both_adapters(api):
    """Status-code parity only, not body-shape parity — a real, pre-existing divergence: Django's
    `AgentTokenListCreateView` uses plain DRF `IsAuthenticated` (never migrated to the
    Django_Adapter's own canonical `{error, code}` format the way the rest of `agent_views.py`'s
    sibling error paths were), so its 401 body is DRF's own default
    (`{"detail": "Authentication credentials were not provided."}`) — verified directly, not
    assumed — while the FastAPI_Adapter's `require_jwt()` always returns the canonical shape. Not
    "fixed" here: porting Django's real behavior, not silently normalizing it away."""
    response = await api.get("/ai/tokens/")
    assert response.status_code == 401


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_token_list_empty_for_fresh_user(api):
    from tests.contract.conftest import register_and_login

    access_token, _email = await register_and_login(api)

    response = await api.get("/ai/tokens/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.body == []
