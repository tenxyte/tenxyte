"""
Feature: z_aud_2, Property 10: Surface MCP sans amplification de privilèges

Validates: Requirements 5.3, 5.4
"""

import inspect

import pytest

from tenxyte_mcp_server import server

_EXPECTED_TOOLS = {
    "airs_token_status",
    "airs_heartbeat",
    "airs_report_usage",
    "airs_list_pending_actions",
    "airs_discovery",
}

_FORBIDDEN_SUBSTRINGS = ("create", "confirm", "deny", "revoke", "issue")


@pytest.mark.asyncio
async def test_exact_tool_set():
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    assert names == _EXPECTED_TOOLS


@pytest.mark.asyncio
async def test_no_privilege_amplifying_tool_names():
    tools = await server.mcp.list_tools()
    for tool in tools:
        lowered = tool.name.lower()
        for forbidden in _FORBIDDEN_SUBSTRINGS:
            assert forbidden not in lowered, f"tool {tool.name!r} looks privilege-amplifying ({forbidden!r})"


def test_no_configuration_option_accepts_a_user_jwt():
    """Neither MCPConfig nor AIRSClient exposes any field/parameter for a human JWT."""
    from tenxyte_mcp_server.airs_client import AIRSClient
    from tenxyte_mcp_server.config import MCPConfig

    for target in (MCPConfig, AIRSClient.__init__):
        signature = inspect.signature(target)
        for name in signature.parameters:
            assert "jwt" not in name.lower(), f"{target} accepts a JWT-shaped parameter: {name}"


def test_no_source_file_creates_agent_tokens_or_confirms_hitl():
    import pathlib

    package_root = pathlib.Path(server.__file__).parent
    forbidden_endpoint_fragments = ['tokens/", method="POST', "pending_action_confirm", "pending_action_deny"]

    for py_file in package_root.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for fragment in forbidden_endpoint_fragments:
            assert fragment not in content, f"{py_file} references a human-authority operation: {fragment!r}"
