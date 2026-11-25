"""
Environment-variable configuration for tenxyte-mcp-server (spec z_aud_2, Requirement 5.2).

Configured exclusively through environment variables — never a config file, never a CLI flag
carrying secrets. Missing required variables fail loudly at startup (stderr + non-zero exit),
never a degraded/partial start (design.md: "Démarrage : variables d'env manquantes → message
d'erreur explicite sur stderr + exit != 0").
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

REQUIRED_VARS = ("TENXYTE_BASE_URL", "TENXYTE_AGENT_TOKEN")
OPTIONAL_VARS = ("TENXYTE_ACCESS_KEY", "TENXYTE_ACCESS_SECRET")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class MCPConfig:
    base_url: str
    agent_token: str
    access_key: str | None = None
    access_secret: str | None = None


def load_config(env: dict[str, str] | None = None) -> MCPConfig:
    """
    Read and validate configuration from the environment.

    `TENXYTE_BASE_URL` and `TENXYTE_AGENT_TOKEN` are required — the No_Privilege_Amplification_Rule
    (design.md D3) means this server never holds anything more privileged than one already-issued
    Agent Token, so there is no "create a token" fallback to fall back to. `TENXYTE_ACCESS_KEY` /
    `TENXYTE_ACCESS_SECRET` are optional (only needed if the target requires application
    credentials).
    """
    env = os.environ if env is None else env

    missing = [name for name in REQUIRED_VARS if not env.get(name)]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". tenxyte-mcp-server needs TENXYTE_BASE_URL and TENXYTE_AGENT_TOKEN to start; "
            + "TENXYTE_ACCESS_KEY / TENXYTE_ACCESS_SECRET are optional. See README.md."
        )

    return MCPConfig(
        base_url=env["TENXYTE_BASE_URL"].rstrip("/"),
        agent_token=env["TENXYTE_AGENT_TOKEN"],
        access_key=env.get("TENXYTE_ACCESS_KEY"),
        access_secret=env.get("TENXYTE_ACCESS_SECRET"),
    )


def load_config_or_exit(env: dict[str, str] | None = None) -> MCPConfig:
    """Same as `load_config`, but prints to stderr and calls `sys.exit(2)` on failure — the
    entry point CLI should use this, tests should use `load_config` directly."""
    try:
        return load_config(env)
    except ConfigError as exc:
        print(f"tenxyte-mcp-server: {exc}", file=sys.stderr)
        sys.exit(2)
