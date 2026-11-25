import pytest

from tenxyte_mcp_server import server
from tenxyte_mcp_server.config import MCPConfig

DISCOVERY_BODY = {
    "airs_version": "1.0",
    "conformance": ["core", "hitl", "guards", "budget", "trace"],
    "endpoints": {
        "heartbeat": "/ai/tokens/{id}/heartbeat/",
        "report_usage": "/ai/tokens/{id}/report-usage/",
        "pending_actions": "/ai/pending-actions/",
    },
    "limits": {"token_max_lifetime": 86400, "default_expiry": 3600},
}


@pytest.fixture(autouse=True)
def _configured_server():
    server.configure(MCPConfig(base_url="https://airs.test", agent_token="raw-token"), token_id=1)
    yield
    server._client = None
    server._token_id = None
