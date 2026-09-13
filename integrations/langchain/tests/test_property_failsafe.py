"""
Feature: z_aud_2, Property 9 (volet LangChain): Fail-safe des connecteurs sur token invalide

For every terminal Agent Token state (5 suspension reasons, revoked, expired), the connector
raises a typed exception and issues no retry.

Validates: Requirements 4.8
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tenxyte_langchain import (
    TenxyteAIRSClient,
    TenxyteBudgetExceededError,
    TenxyteTokenExpiredError,
    TenxyteTokenNotFoundError,
    TenxyteTokenRevokedError,
    TenxyteTokenSuspendedError,
)

BASE_URL = "https://airs.test"

_SUSPENSION_REASONS = ["RATE_LIMIT", "ANOMALY", "MANUAL", "HEARTBEAT_MISSING"]


def _discovery_response():
    return {
        "airs_version": "1.0",
        "conformance": ["core", "guards", "budget"],
        "endpoints": {"heartbeat": "/ai/tokens/{id}/heartbeat/"},
        "limits": {},
    }


@given(reason=st.sampled_from(_SUSPENSION_REASONS))
def test_property_9_suspended_reasons_raise_typed_suspended_error(reason):
    import respx

    with respx.mock(assert_all_called=False) as router:
        router.get(f"{BASE_URL}/ai/.well-known/airs/").respond(200, json=_discovery_response())
        router.post(f"{BASE_URL}/ai/tokens/1/heartbeat/").respond(
            403, json={"error": "suspended", "code": "AGENT_TOKEN_STATUS_SUSPENDED", "reason": reason}
        )

        client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
        with pytest.raises(TenxyteTokenSuspendedError) as exc_info:
            client.heartbeat(1)
        assert exc_info.value.suspended_reason == reason


def test_property_9_budget_exceeded_raises_specific_subtype():
    import respx

    with respx.mock(assert_all_called=False) as router:
        router.get(f"{BASE_URL}/ai/.well-known/airs/").respond(200, json=_discovery_response())
        router.post(f"{BASE_URL}/ai/tokens/1/heartbeat/").respond(
            403, json={"error": "budget exceeded", "code": "AGENT_TOKEN_STATUS_SUSPENDED", "reason": "BUDGET_EXCEEDED"}
        )

        client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
        with pytest.raises(TenxyteBudgetExceededError):
            client.heartbeat(1)


def test_property_9_revoked_raises_typed_error():
    import respx

    with respx.mock(assert_all_called=False) as router:
        router.get(f"{BASE_URL}/ai/.well-known/airs/").respond(200, json=_discovery_response())
        router.post(f"{BASE_URL}/ai/tokens/1/heartbeat/").respond(
            403, json={"error": "revoked", "code": "AGENT_TOKEN_STATUS_REVOKED"}
        )
        client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
        with pytest.raises(TenxyteTokenRevokedError):
            client.heartbeat(1)


def test_property_9_expired_raises_typed_error():
    import respx

    with respx.mock(assert_all_called=False) as router:
        router.get(f"{BASE_URL}/ai/.well-known/airs/").respond(200, json=_discovery_response())
        router.post(f"{BASE_URL}/ai/tokens/1/heartbeat/").respond(
            403, json={"error": "expired", "code": "AGENT_TOKEN_EXPIRED"}
        )
        client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
        with pytest.raises(TenxyteTokenExpiredError):
            client.heartbeat(1)


def test_property_9_not_found_raises_typed_error():
    import respx

    with respx.mock(assert_all_called=False) as router:
        router.get(f"{BASE_URL}/ai/.well-known/airs/").respond(200, json=_discovery_response())
        router.post(f"{BASE_URL}/ai/tokens/1/heartbeat/").respond(
            403, json={"error": "not found", "code": "AGENT_TOKEN_NOT_FOUND"}
        )
        client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
        with pytest.raises(TenxyteTokenNotFoundError):
            client.heartbeat(1)


def test_property_9_client_does_not_retry_automatically():
    """A single logical call issues exactly one HTTP request, even on a terminal error."""
    import respx

    call_count = {"n": 0}

    def _count(request):
        import httpx

        call_count["n"] += 1
        return httpx.Response(403, json={"error": "revoked", "code": "AGENT_TOKEN_STATUS_REVOKED"})

    with respx.mock(assert_all_called=False) as router:
        router.get(f"{BASE_URL}/ai/.well-known/airs/").respond(200, json=_discovery_response())
        router.post(f"{BASE_URL}/ai/tokens/1/heartbeat/").mock(side_effect=_count)

        client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
        with pytest.raises(TenxyteTokenRevokedError):
            client.heartbeat(1)

    assert call_count["n"] == 1
