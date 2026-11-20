"""
Feature: z_aud_3, Property 9: Format d'erreur canonique universel

Every error the FastAPI_Adapter produces — including ones FastAPI/Starlette raise natively —
carries the canonical `{"error", "code"}` shape (plus `details` where applicable).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st
from pydantic import BaseModel

from tenxyte.adapters.fastapi.errors import TenxyteAPIError, register_exception_handlers


class _Body(BaseModel):
    email: str
    age: int


def _build_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/echo")
    async def echo(body: _Body):
        return {"email": body.email, "age": body.age}

    @app.get("/boom")
    async def boom():
        raise TenxyteAPIError("Custom failure", code="CUSTOM_FAILURE", status_code=409, details={"x": 1})

    @app.get("/crash")
    async def crash():
        raise RuntimeError("something broke")

    return app


@pytest.fixture()
def client():
    with TestClient(_build_test_app(), raise_server_exceptions=False) as c:
        yield c


def _assert_canonical_shape(body: dict):
    assert "error" in body
    assert "code" in body
    assert isinstance(body["error"], str)
    assert isinstance(body["code"], str)


@given(
    payload=st.one_of(
        st.just({}),  # missing both fields
        st.just({"email": "x@example.com"}),  # missing age
        st.just({"email": "x@example.com", "age": "not-a-number"}),  # wrong type
        st.just({"age": 30}),  # missing email
        st.dictionaries(st.text(min_size=1, max_size=5), st.integers(), max_size=3),  # arbitrary garbage
    )
)
@hyp_settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_9_validation_errors_are_canonical(client, payload):
    response = client.post("/echo", json=payload)
    assert response.status_code == 400
    body = response.json()
    _assert_canonical_shape(body)
    assert body["code"] == "VALIDATION_ERROR"
    assert "details" in body


def test_property_9_malformed_json_is_canonical(client):
    response = client.post("/echo", content=b"{not-json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    _assert_canonical_shape(response.json())


def test_property_9_wrong_content_type_is_canonical_not_a_500(client):
    """Real bug found via a user's own manual testing (not just read, reproduced directly): a
    client sending valid JSON *bytes* but the wrong `Content-Type` (PowerShell's `curl` alias —
    really `Invoke-WebRequest` — does exactly this by default) makes Pydantic's
    `RequestValidationError.errors()` echo the raw `bytes` payload back in its `"input"` field.
    `_handle_validation_error` used to pass that straight into `JSONResponse`, whose `render()`
    uses the stdlib's `json.dumps()` — which cannot serialize `bytes` — crashing the handler
    itself and turning an intended clean 400 into an unhandled 500. Fixed by running
    `exc.errors()` through `jsonable_encoder` first."""
    response = client.post(
        "/echo",
        content=b'{"email": "x@example.com", "age": 30}',
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 400
    body = response.json()
    _assert_canonical_shape(body)
    assert body["code"] == "VALIDATION_ERROR"
    # not raw bytes — jsonable_encoder ran, and details is DRF's {field: [messages]} object
    assert all(isinstance(m, str) for msgs in body["details"].values() for m in msgs)


def test_property_9_validation_details_are_keyed_by_field(client):
    """`details` mirrors the Django_Adapter's `serializer.errors` (`{field: [messages]}`), not
    Pydantic's raw list — the SDK maps field errors by name (tenxyte-js MT-2, 2026-10-26)."""
    response = client.post("/echo", json={"email": "x@example.com", "age": "not-a-number"})
    details = response.json()["details"]
    assert isinstance(details, dict)
    assert list(details) == ["age"]
    assert all(isinstance(m, str) for m in details["age"])


def test_property_9_unknown_route_404_is_canonical(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    _assert_canonical_shape(response.json())


def test_property_9_wrong_method_405_is_canonical(client):
    response = client.get("/echo")
    assert response.status_code == 405
    _assert_canonical_shape(response.json())


def test_property_9_custom_tenxyte_error_passes_through_canonical():
    with TestClient(_build_test_app(), raise_server_exceptions=False) as client:
        response = client.get("/boom")
    assert response.status_code == 409
    body = response.json()
    assert body == {"error": "Custom failure", "code": "CUSTOM_FAILURE", "details": {"x": 1}}


def test_property_9_unhandled_exception_masked_as_internal_error(client):
    response = client.get("/crash")
    assert response.status_code == 500
    body = response.json()
    _assert_canonical_shape(body)
    assert body["code"] == "INTERNAL_ERROR"
    assert "RuntimeError" not in body["error"]
    assert "something broke" not in body["error"]
