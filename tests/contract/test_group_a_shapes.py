"""
Contract_Suite — Parity_Group A (spec z_aud_3, task 3.2, Property 2): the same assertions,
written once against the `api` fixture, run unchanged against both the Django_Adapter and the
FastAPI_Adapter. Shape constants come from `tests/contract/shapes.py`, the single source of truth
also used by the Django_Adapter's own snapshot tests — the two suites can't silently drift apart.
"""

import uuid

import pytest

from tests.contract.shapes import LOGIN_EMAIL_REQUIRED_FIELDS, REGISTER_REQUIRED_FIELDS, REGISTER_USER_FIELDS


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_register_success_has_documented_top_level_fields(api):
    email = f"contract-{uuid.uuid4().hex}@example.com"
    response = await api.post("/register/", json={"email": email, "password": "Correct-Horse-Battery-Staple-1"})

    assert response.status_code == 201
    for field in REGISTER_REQUIRED_FIELDS:
        assert field in response.body, f"Required field '{field}' missing from /register/ success response"


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_register_success_user_object_has_documented_fields(api):
    email = f"contract-{uuid.uuid4().hex}@example.com"
    response = await api.post("/register/", json={"email": email, "password": "Correct-Horse-Battery-Staple-1"})

    assert response.status_code == 201
    user_data = response.body["user"]
    for field in REGISTER_USER_FIELDS:
        assert field in user_data, f"User field '{field}' missing from /register/ success response"


@pytest.mark.django_db(transaction=True)
@pytest.mark.anyio
async def test_login_email_success_has_documented_fields(api):
    email = f"contract-{uuid.uuid4().hex}@example.com"
    password = "Correct-Horse-Battery-Staple-1"
    register_response = await api.post("/register/", json={"email": email, "password": password})
    assert register_response.status_code == 201

    response = await api.post("/login/email/", json={"email": email, "password": password})

    assert response.status_code == 200
    for field in LOGIN_EMAIL_REQUIRED_FIELDS:
        assert field in response.body, f"Required field '{field}' missing from /login/email/ success response"
    assert response.body["token_type"] == "Bearer"
