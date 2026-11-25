"""
tenxyte-mcp-server — MCP server exposing AIRS Agent Token upkeep as tools (spec z_aud_2,
Requirement 5).

Surface is deliberately asymmetric (design.md "Décision de conception : MCP sans amplification
de privilèges" / No_Privilege_Amplification_Rule, D3): everything here is upkeep an *agent* may
legitimately do to its own already-issued token (check status, heartbeat, report usage, see its
own pending actions, introspect the server). Nothing here creates a token, confirms or denies a
HITL action, or accepts a human credential — those stay strictly on the human side of Tenxyte's
own API, never in reach of this process.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import Any, TypeVar

from mcp.server.mcpserver import MCPServer

from .airs_client import AIRSClient, AIRSError
from .config import MCPConfig, load_config_or_exit

mcp = MCPServer("tenxyte-airs")

_client: AIRSClient | None = None
_token_id: Any = None

_F = TypeVar("_F", bound=Callable[..., Any])


def _get_client() -> AIRSClient:
    if _client is None:
        raise RuntimeError("tenxyte-mcp-server is not configured (call configure() first)")
    return _client


def configure(config: MCPConfig, *, token_id: Any = None) -> None:
    """
    Wire this module's global client from a loaded `MCPConfig`.

    `token_id` is the numeric/string id AIRS assigned this Agent Token at issuance (distinct
    from the raw token value); several endpoints are addressed by id, not by the raw token.
    When not supplied, the tools that need it (`airs_heartbeat`, `airs_report_usage`) will report
    a structured error asking for `TENXYTE_AGENT_TOKEN_ID` to be set instead of crashing.
    """
    global _client, _token_id
    _client = AIRSClient(
        config.base_url,
        config.agent_token,
        access_key=config.access_key,
        access_secret=config.access_secret,
    )
    _token_id = token_id


class MissingTokenIdError(AIRSError):
    def __init__(self):
        super().__init__("TENXYTE_AGENT_TOKEN_ID is not set", code="MISSING_TOKEN_ID")


def _require_token_id() -> Any:
    if _token_id is None:
        raise MissingTokenIdError
    return _token_id


def _structured_errors(fn: _F) -> _F:
    """
    Every tool below is wrapped with this: whatever goes wrong (a typed `AIRSError` from the
    client, or anything else — a transport failure, a bug), the tool raises a JSON-shaped
    `RuntimeError` rather than letting a bare, unstructured exception surface. The MCP framework
    itself already guarantees the *process* survives an exception raised from inside a tool
    ([AIRS-CORE-16], Requirement 5.5) — this decorator is what guarantees the *error content* is
    always structured, not just "the process didn't crash".
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except AIRSError as exc:
            raise RuntimeError(json.dumps(exc.as_dict())) from exc
        except Exception as exc:
            raise RuntimeError(json.dumps({"error": str(exc), "code": "UNEXPECTED_ERROR"})) from exc

    return wrapper  # type: ignore[return-value]


@mcp.tool()
@_structured_errors
def airs_discovery() -> dict[str, Any]:
    """Return the target server's AIRS discovery document (spec version, active Conformance
    Levels, endpoint map, limits) — capabilities only, no data ([AIRS-DISC-1])."""
    return _get_client().discovery


@mcp.tool()
@_structured_errors
def airs_token_status() -> dict[str, Any]:
    """
    Report whether this Agent Token is still usable.

    There is no dedicated agent-side "status" endpoint in AIRS/1.0 — this sends a heartbeat and
    reports success/failure, since that is the one agent-callable operation that reveals a
    token's liveness without any side effect beyond what heartbeats already do. If the token is
    suspended, revoked, or expired, this (like every tool) raises a structured error rather than
    reporting a fake "ok" status (Requirement 5.5).
    """
    client = _get_client()
    token_id = _require_token_id()
    result = client.heartbeat(token_id)
    return {"status": "ACTIVE", **result}


@mcp.tool()
@_structured_errors
def airs_heartbeat() -> dict[str, Any]:
    """Send a liveness heartbeat, maintaining the Dead Man's Switch Guardrail ([AIRS-GUARDS-3])."""
    return _get_client().heartbeat(_require_token_id())


@mcp.tool()
@_structured_errors
def airs_report_usage(cost_usd: float, prompt_tokens: int = 0, completion_tokens: int = 0) -> dict[str, Any]:
    """Report incremental LLM usage/cost against this token's budget ([AIRS-BUDGET-1]). Raises a
    structured error if this report pushes the token over its limit (BUDGET_EXCEEDED)."""
    return _get_client().report_usage(
        _require_token_id(), cost_usd=cost_usd, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )


@mcp.tool()
@_structured_errors
def airs_list_pending_actions() -> list[dict[str, Any]]:
    """
    List outstanding HITL Pending Actions.

    Note: Tenxyte's reference implementation currently scopes this listing to the Delegating
    User's own human authentication, not the Agent Token — calling this tool against Tenxyte
    will surface that as a structured PERMISSION error, not a crash. It is included for
    AIRS/1.0 implementations that do expose it to the agent side.
    """
    return _get_client().pending_actions()


@mcp.resource("airs://token/status")
def token_status_resource() -> dict[str, Any]:
    """Read-only resource mirroring `airs_token_status` (already wraps its own errors)."""
    return airs_token_status()


@mcp.resource("airs://budget")
@_structured_errors
def budget_resource() -> dict[str, Any]:
    """Read-only resource: the discovery document's `budget`-relevant limits, if any."""
    discovery = _get_client().discovery
    return {"conformance": discovery.get("conformance", []), "limits": discovery.get("limits", {})}


def main() -> None:
    import os

    config = load_config_or_exit()
    token_id = os.environ.get("TENXYTE_AGENT_TOKEN_ID")
    configure(config, token_id=token_id)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
