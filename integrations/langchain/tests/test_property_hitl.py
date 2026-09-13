"""
Feature: z_aud_2, Property 7: Contrat HITL du connecteur

Validates: Requirements 4.6
"""

import json

import httpx
from hypothesis import HealthCheck, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from tenxyte_langchain import TenxyteAIRSClient, TenxyteHITLPending

from .conftest import BASE_URL

_METHODS = ["POST", "PUT", "PATCH"]
_PATHS = ["/business/refund/", "/business/invoice/123/", "/actions/do-thing/"]


@hyp_settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    method=st.sampled_from(_METHODS),
    path=st.sampled_from(_PATHS),
    body=st.dictionaries(st.text(min_size=1, max_size=8), st.integers(min_value=0, max_value=1000), max_size=5),
    confirmation_token=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=8, max_size=32),
)
def test_property_7_hitl_pending_then_resume_replays_identically(mock_airs, method, path, body, confirmation_token):
    """
    For any 202 response, the connector raises TenxyteHITLPending carrying the exact
    confirmation_token, does not execute the effect, and resume() replays the original request
    (method/url/body identical) plus X-Action-Confirmation.
    """
    seen_confirmed_bodies = []
    seen_unconfirmed_count = 0

    def _handler(request):
        nonlocal seen_unconfirmed_count
        if request.headers.get("X-Action-Confirmation") == confirmation_token:
            seen_confirmed_bodies.append(json.loads(request.content) if request.content else {})
            return httpx.Response(200, json={"executed": True})
        seen_unconfirmed_count += 1
        return httpx.Response(
            202,
            json={
                "status": "pending_confirmation",
                "confirmation_token": confirmation_token,
                "expires_at": "2999-01-01T00:00:00Z",
            },
        )

    mock_airs.request(method, f"{BASE_URL}{path}").mock(side_effect=_handler)

    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")

    try:
        client.request(method, path, json=body)
        raise AssertionError("expected TenxyteHITLPending")
    except TenxyteHITLPending as pending:
        assert pending.confirmation_token == confirmation_token
        assert seen_unconfirmed_count == 1
        assert seen_confirmed_bodies == []  # not executed yet

        response = pending.resume()

    assert response.status_code == 200
    assert seen_confirmed_bodies == [body]
