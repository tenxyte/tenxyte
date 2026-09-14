"""
Contract_Suite — Parity_Group B (spec z_aud_3, task 7.3): the same assertions, written once
against the `api` fixture, run unchanged against both the Django_Adapter and the FastAPI_Adapter.
"""

import uuid

import pytest

from tests.contract.shapes import PASSWORD_REQUIREMENTS_FIELDS, PASSWORD_RESET_REQUEST_KNOWN_ACCOUNT_FIELDS


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_password_requirements_has_documented_fields(api):
    response = await api.get("/password/requirements/")

    assert response.status_code == 200
    for field in PASSWORD_REQUIREMENTS_FIELDS:
        assert field in response.body, f"Required field '{field}' missing from /password/requirements/ response"


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_password_reset_request_known_account_has_documented_fields(api):
    from tests.contract.conftest import register_and_login

    _access_token, email = await register_and_login(api)

    response = await api.post("/password/reset/request/", json={"email": email})

    assert response.status_code == 200
    for field in PASSWORD_RESET_REQUEST_KNOWN_ACCOUNT_FIELDS:
        assert field in response.body, f"Required field '{field}' missing from /password/reset/request/ response"


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_password_reset_request_anti_enumeration_status_code(api):
    """Property 3 (spec z_aud_3): an unregistered email must not surface a different status code
    or an error than a registered one — same 200 either way. NOT a full body-shape match: Django's
    own `PasswordResetRequestView` deliberately returns a genuinely empty body (no JSON, not even
    `{}`) for the unknown-account branch, distinct from the known-account branch's populated body
    — replicated by both adapters (see `routers/password.py`'s module docstring), so only the
    status-code/no-error half of anti-enumeration holds here, not full shape identity."""
    unknown_email = f"nonexistent-{uuid.uuid4().hex}@example.com"

    response = await api.post("/password/reset/request/", json={"email": unknown_email})

    assert response.status_code == 200
    assert "error" not in response.body
