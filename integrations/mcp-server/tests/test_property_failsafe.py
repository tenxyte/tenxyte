"""
Feature: z_aud_2, Property 9 (volet MCP): chaque état terminal produit une erreur MCP structurée,
process vivant.

Validates: Requirements 5.5
"""

import json
from contextlib import contextmanager

import httpx
import pytest
import respx
from hypothesis import given
from hypothesis import strategies as st
from mcp.server.mcpserver.exceptions import UnexpectedToolError

from tenxyte_mcp_server import server

from .conftest import DISCOVERY_BODY

_SUSPENSION_REASONS = ["RATE_LIMIT", "ANOMALY", "MANUAL", "HEARTBEAT_MISSING", "BUDGET_EXCEEDED"]


def _structured_cause(exc: BaseException) -> dict:
    assert exc.__cause__ is not None, "expected a structured cause carrying the JSON payload"
    return json.loads(str(exc.__cause__))


@contextmanager
def _mocked(heartbeat_response):
    with respx.mock(assert_all_called=False) as router:
        router.get("https://airs.test/ai/.well-known/airs/").respond(200, json=DISCOVERY_BODY)
        router.post("https://airs.test/ai/tokens/1/heartbeat/").mock(side_effect=heartbeat_response)
        yield router


@pytest.mark.asyncio
@given(reason=st.sampled_from(_SUSPENSION_REASONS))
async def test_property_9_every_terminal_reason_yields_structured_error_process_survives(reason):
    def _respond(request):
        return httpx.Response(
            403, json={"error": "suspended", "code": "AGENT_TOKEN_STATUS_SUSPENDED", "reason": reason}
        )

    with _mocked(_respond):
        with pytest.raises(UnexpectedToolError) as exc_info:
            await server.mcp.call_tool("airs_heartbeat", {})

        payload = _structured_cause(exc_info.value)
        assert payload["reason"] == reason
        assert payload["code"] == "AGENT_TOKEN_STATUS_SUSPENDED"

    # The process is manifestly still alive: a second, independent call still goes through the
    # framework normally rather than the whole server having gone down.
    with _mocked(lambda request: httpx.Response(200, json={"status": "ok"})):
        result = await server.mcp.call_tool("airs_heartbeat", {})
        assert result is not None


@pytest.mark.asyncio
async def test_budget_exceeded_inferred_even_without_code_or_reason():
    """Regression: Tenxyte's real report-usage endpoint returns {"error": "Budget exceeded",
    "status": "suspended"} with NO "code"/"reason" field — caught while running the CrewAI
    example end-to-end, where this used to surface as a blank code/reason."""
    with respx.mock(assert_all_called=False) as router:
        router.get("https://airs.test/ai/.well-known/airs/").respond(200, json=DISCOVERY_BODY)
        router.post("https://airs.test/ai/tokens/1/report-usage/").respond(
            403, json={"error": "Budget exceeded", "status": "suspended"}
        )
        with pytest.raises(UnexpectedToolError) as exc_info:
            await server.mcp.call_tool("airs_report_usage", {"cost_usd": 1.0})
        payload = _structured_cause(exc_info.value)
        assert payload["code"] == "BUDGET_EXCEEDED"


@pytest.mark.asyncio
async def test_property_9_revoked_yields_structured_error():
    with _mocked(lambda request: httpx.Response(403, json={"error": "revoked", "code": "AGENT_TOKEN_STATUS_REVOKED"})):
        with pytest.raises(UnexpectedToolError) as exc_info:
            await server.mcp.call_tool("airs_heartbeat", {})
        payload = _structured_cause(exc_info.value)
        assert payload["code"] == "AGENT_TOKEN_STATUS_REVOKED"


@pytest.mark.asyncio
async def test_property_9_expired_yields_structured_error():
    with _mocked(lambda request: httpx.Response(403, json={"error": "expired", "code": "AGENT_TOKEN_EXPIRED"})):
        with pytest.raises(UnexpectedToolError) as exc_info:
            await server.mcp.call_tool("airs_heartbeat", {})
        payload = _structured_cause(exc_info.value)
        assert payload["code"] == "AGENT_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_property_9_transport_failure_also_structured_not_a_bare_crash():
    """Even a non-AIRS failure (network error) is turned into a structured, JSON-shaped cause."""

    def _raise(request):
        raise httpx.ConnectError("refused")

    with _mocked(_raise):
        with pytest.raises(UnexpectedToolError) as exc_info:
            await server.mcp.call_tool("airs_heartbeat", {})
        payload = _structured_cause(exc_info.value)
        assert payload["code"] == "UNEXPECTED_ERROR"


@pytest.mark.asyncio
async def test_property_9_missing_token_id_is_structured_not_a_crash():
    server._token_id = None
    with pytest.raises(UnexpectedToolError) as exc_info:
        await server.mcp.call_tool("airs_heartbeat", {})
    payload = _structured_cause(exc_info.value)
    assert payload["code"] == "MISSING_TOKEN_ID"
