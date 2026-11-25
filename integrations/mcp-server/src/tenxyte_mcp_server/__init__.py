"""
tenxyte-mcp-server — MCP server exposing AIRS/1.0 Agent Token upkeep (spec/airs/AIRS-1.0.md) as
tools for MCP clients (Claude Desktop, and any other MCP-compatible agent host).

A pure HTTP client: never imports the `tenxyte` package (HTTP_Only_Rule). Never holds a human
JWT and never creates tokens or confirms/denies HITL actions (No_Privilege_Amplification_Rule,
design.md D3) — see `server.py` for the exact tool surface.
"""

from .airs_client import AIRSClient, AIRSError
from .config import ConfigError, MCPConfig, load_config, load_config_or_exit

__version__ = "0.1.0"

__all__ = [
    "AIRSClient",
    "AIRSError",
    "ConfigError",
    "MCPConfig",
    "load_config",
    "load_config_or_exit",
]
