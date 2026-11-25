import httpx
import pytest
import respx

from tenxyte_langchain import (
    TenxyteAIRSClient,
    TenxyteAIRSUnavailable,
    TenxyteCapabilityError,
    TenxyteHITLPending,
    TenxyteTokenRevokedError,
    TenxyteTokenSuspendedError,
)

from .conftest import BASE_URL


def test_discovery_is_fetched_once_and_cached(mock_airs):
    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    d1 = client.discovery
    d2 = client.discovery
    assert d1 is d2
    assert mock_airs["discovery"].call_count == 1


def test_endpoint_template_substitution(mock_airs):
    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    assert client.endpoint("heartbeat", id=42) == "/ai/tokens/42/heartbeat/"
    assert client.endpoint("tokens") == "/ai/tokens/"


def test_require_level_raises_when_absent(mock_airs):
    mock_airs["discovery"].respond(
        200, json={"airs_version": "1.0", "conformance": ["core"], "endpoints": {}, "limits": {}}
    )
    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    with pytest.raises(TenxyteCapabilityError):
        client.require_level("budget")


def test_discovery_unreachable_raises_typed_error():
    with respx.mock:
        respx.get(f"{BASE_URL}/ai/.well-known/airs/").mock(side_effect=httpx.ConnectError("refused"))
        client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
        with pytest.raises(TenxyteAIRSUnavailable):
            _ = client.discovery


def test_application_credentials_attached(mock_airs):
    route = mock_airs.post(f"{BASE_URL}/ai/tokens/1/heartbeat/", name="hb1").respond(200, json={"status": "ok"})
    client = TenxyteAIRSClient(BASE_URL, agent_token="raw", access_key="key123", access_secret="secret456")
    client.heartbeat(1)

    request = route.calls.last.request
    assert request.headers["X-Access-Key"] == "key123"
    assert request.headers["X-Access-Secret"] == "secret456"


def test_heartbeat_returns_body(mock_airs):
    mock_airs.post(f"{BASE_URL}/ai/tokens/7/heartbeat/").respond(200, json={"status": "ok"})
    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    assert client.heartbeat(7) == {"status": "ok"}


def test_suspended_token_raises_with_reason(mock_airs):
    mock_airs.post(f"{BASE_URL}/ai/tokens/7/heartbeat/").respond(
        403, json={"error": "suspended", "code": "AGENT_TOKEN_STATUS_SUSPENDED", "reason": "RATE_LIMIT"}
    )
    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    with pytest.raises(TenxyteTokenSuspendedError) as exc_info:
        client.heartbeat(7)
    assert exc_info.value.suspended_reason == "RATE_LIMIT"


def test_revoked_token_raises_distinct_type(mock_airs):
    mock_airs.post(f"{BASE_URL}/ai/tokens/7/heartbeat/").respond(
        403, json={"error": "revoked", "code": "AGENT_TOKEN_STATUS_REVOKED"}
    )
    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    with pytest.raises(TenxyteTokenRevokedError):
        client.heartbeat(7)


def test_budget_exceeded_raises_specific_type(mock_airs):
    mock_airs.post(f"{BASE_URL}/ai/tokens/7/report-usage/").respond(
        403, json={"error": "Budget exceeded", "code": "AGENT_TOKEN_STATUS_SUSPENDED", "reason": "BUDGET_EXCEEDED"}
    )
    from tenxyte_langchain import TenxyteBudgetExceededError

    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    with pytest.raises(TenxyteBudgetExceededError):
        client.report_usage(7, cost_usd=1.0)


def test_budget_exceeded_raises_specific_type_even_without_code_or_reason(mock_airs):
    """Regression: Tenxyte's real report-usage endpoint returns {"error": "Budget exceeded",
    "status": "suspended"} with NO "code"/"reason" field at all — caught while running the
    CrewAI example end-to-end, where this used to misclassify as TenxytePermissionDeniedError."""
    mock_airs.post(f"{BASE_URL}/ai/tokens/7/report-usage/").respond(
        403, json={"error": "Budget exceeded", "status": "suspended"}
    )
    from tenxyte_langchain import TenxyteBudgetExceededError

    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    with pytest.raises(TenxyteBudgetExceededError):
        client.report_usage(7, cost_usd=1.0)


def test_202_raises_hitl_pending_with_resumable_snapshot(mock_airs):
    # More specific route (header match) registered first: respx tries routes in registration
    # order and the confirmed-replay request would otherwise also match the unconditional one.
    mock_airs.post(f"{BASE_URL}/business/action/", headers={"X-Action-Confirmation": "hitl_abc123"}).respond(
        200, json={"executed": True}
    )
    mock_airs.post(f"{BASE_URL}/business/action/").respond(
        202,
        json={
            "status": "pending_confirmation",
            "confirmation_token": "hitl_abc123",
            "expires_at": "2999-01-01T00:00:00Z",
        },
    )

    client = TenxyteAIRSClient(BASE_URL, agent_token="raw")
    with pytest.raises(TenxyteHITLPending) as exc_info:
        client.request("POST", "/business/action/", json={"amount": 10})

    pending = exc_info.value
    assert pending.confirmation_token == "hitl_abc123"

    response = pending.resume()
    assert response.json() == {"executed": True}
