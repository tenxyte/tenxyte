"""
Contract_Suite — Parity_Group G / WebAuthn, Social, GDPR (spec z_aud_3, task 12.2): the same
assertions, written once against the `api` fixture, run unchanged against both the Django_Adapter
and the FastAPI_Adapter.

**GDPR user endpoints get real, successful round-trip coverage** (register+login, then a genuine
`account-deletion-status/` call for a fresh user) — same reasoning as Group E's
`create_organization`/`list_organizations`: these need only `@require_jwt`/`IsAuthenticated`, no
RBAC permission promotion the `api` fixture can't grant.

**WebAuthn/Social/GDPR-admin get gate-level or fixed-error-shape proofs only, not full round
trips** — same narrower-than-A-C pattern as Groups D/E/F, for two different reasons:
- WebAuthn's real round trip needs a genuine FIDO2 authenticator (real P-256 keys, real CBOR,
  real signatures) on *both* backends — `_webauthn_authenticator.py`'s `VirtualAuthenticator`
  already exhaustively proves this end-to-end against the FastAPI_Adapter
  (`test_webauthn_router.py`) and the Django_Adapter has its own equivalent coverage
  (`test_webauthn.py`) — not a coverage gap for the *behavior*, only for the Contract_Suite's own
  reach, same reasoning `test_group_f_shapes.py`'s module docstring already gives for AIRS.
- `admin/deletion-requests/` needs `gdpr.admin`, which (like Group F's Delegating User) the `api`
  fixture has no shared way to promote a freshly `register_and_login()`-ed user to on both
  backends — only the permission-denied gate is provable here.

Social's `PROVIDER_NOT_SUPPORTED` error IS a full real-shape proof despite needing no auth and no
real OAuth round trip at all — `SocialAuthView.post`'s `provider` URL kwarg is supplied via
`view_kwargs={"provider": ...}` (see `conftest.py`'s `_register_group_g_views` docstring for why
`DjangoContractClient` needs that instead of real URL routing).
"""

import pytest

from tests.contract.conftest import register_and_login


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_webauthn_register_begin_requires_auth_identically(api):
    response = await api.post("/webauthn/register/begin/", json={})

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_social_provider_not_supported_identical_shape(api):
    response = await api.post("/social/linkedin/", json={"access_token": "x"}, view_kwargs={"provider": "linkedin"})

    assert response.status_code == 400
    assert response.body == {
        "error": "Provider 'linkedin' is not supported or not enabled.",
        "code": "PROVIDER_NOT_SUPPORTED",
        "supported_providers": ["google", "github", "microsoft", "facebook", "apple"],
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_request_deletion_reauth_required_identical_shape(api):
    access_token, _email = await register_and_login(api)

    response = await api.post(
        "/request-account-deletion/", json={}, headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 400
    assert response.body == {
        "error": "Current password or a valid OTP code is required",
        "code": "REAUTH_REQUIRED",
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_deletion_status_empty_for_fresh_user_identical_shape(api):
    access_token, _email = await register_and_login(api)

    response = await api.get("/account-deletion-status/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.body == {"total_requests": 0, "active_request": None, "history": []}


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_confirm_deletion_unknown_token_identical_shape(api):
    response = await api.post("/confirm-account-deletion/", json={"token": "does-not-exist"})

    assert response.status_code == 400
    assert response.body == {"error": "Invalid or expired confirmation token"}


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_admin_deletion_requests_permission_required_identical_shape(api):
    access_token, _email = await register_and_login(api)

    response = await api.get("/admin/deletion-requests/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 403
    assert response.body == {"error": "Permission denied.", "code": "PERMISSION_REQUIRED"}
