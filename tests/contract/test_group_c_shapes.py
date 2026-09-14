"""
Contract_Suite — Parity_Group C (spec z_aud_3, task 7.3): the same assertions, written once
against the `api` fixture, run unchanged against both the Django_Adapter and the FastAPI_Adapter.
"""

import uuid

import pytest

from tests.contract.shapes import AUTH_REQUIRED_FIELDS, TWOFA_STATUS_FIELDS


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_twofa_status_has_documented_fields(api):
    from tests.contract.conftest import register_and_login

    access_token, _email = await register_and_login(api)

    response = await api.get("/2fa/status/", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    for field in TWOFA_STATUS_FIELDS:
        assert field in response.body, f"Required field '{field}' missing from /2fa/status/ response"
    assert response.body["is_enabled"] is False


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_twofa_status_requires_auth(api):
    response = await api.get("/2fa/status/")

    assert response.status_code == 401
    for field in AUTH_REQUIRED_FIELDS:
        assert field in response.body, f"Required field '{field}' missing from /2fa/status/ 401 response"
    assert response.body["code"] == "AUTH_REQUIRED"


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_otp_request_requires_auth(api):
    response = await api.post("/otp/request/", json={"otp_type": "email"})

    assert response.status_code == 401
    assert response.body["code"] == "AUTH_REQUIRED"


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_magic_link_request_success_message(api):
    response = await api.post(
        "/magic-link/request/",
        json={"email": f"contract-{uuid.uuid4().hex}@example.com", "validation_url": "https://a.example/verify"},
    )

    assert response.status_code == 200
    assert response.body["message"] == "If this email is registered, a magic link has been sent."


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_magic_link_request_anti_enumeration_identical_shape(api):
    """Property 3 (spec z_aud_3): unlike password/reset/request, magic-link/request returns a
    byte-identical body for a known vs. an unknown email — no empty-body quirk on this endpoint."""
    from tests.contract.conftest import register_and_login

    _access_token, email = await register_and_login(api)
    unknown_email = f"nonexistent-{uuid.uuid4().hex}@example.com"

    known_response = await api.post(
        "/magic-link/request/", json={"email": email, "validation_url": "https://a.example/verify"}
    )
    unknown_response = await api.post(
        "/magic-link/request/", json={"email": unknown_email, "validation_url": "https://a.example/verify"}
    )

    assert known_response.status_code == unknown_response.status_code == 200
    assert known_response.body == unknown_response.body
