# tenxyte-mcp-server

An MCP (Model Context Protocol) server exposing [AIRS/1.0](../../spec/airs/AIRS-1.0.md) Agent
Token upkeep — status, heartbeat, usage reporting, pending actions, discovery — as tools any MCP
client (Claude Desktop and others) can call. A pure HTTP client: it never imports the `tenxyte`
package and works against any AIRS-conformant server.

## Install & run

```bash
uvx tenxyte-mcp-server
```

or `pip install tenxyte-mcp-server && tenxyte-mcp-server`.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `TENXYTE_BASE_URL` | Yes | Base URL of the AIRS-hosting API (e.g. `https://your-server.example.com/api/v1/auth`). |
| `TENXYTE_AGENT_TOKEN` | Yes | The raw Agent Token value, issued once by a human via Tenxyte's own API. This server never creates tokens itself. |
| `TENXYTE_AGENT_TOKEN_ID` | Recommended | The token's id (returned alongside the raw value at issuance). Tenxyte's `heartbeat`/`report_usage` endpoints are addressed by id, not by the raw token — omit this and `airs_heartbeat`/`airs_report_usage` return a structured `MISSING_TOKEN_ID` error instead of guessing. |
| `TENXYTE_ACCESS_KEY` | No | Application `X-Access-Key`, if your Tenxyte deployment requires one. |
| `TENXYTE_ACCESS_SECRET` | No | Application `X-Access-Secret`, paired with the above. |

Missing `TENXYTE_BASE_URL` or `TENXYTE_AGENT_TOKEN` fails fast at startup — an explicit message
on stderr and a non-zero exit code, never a partial/degraded start.

## Tools

| Tool | Maps to | Notes |
|---|---|---|
| `airs_discovery()` | `GET .../.well-known/airs/` | Capabilities only — spec version, active Conformance Levels, endpoint map, limits. |
| `airs_token_status()` | `POST .../heartbeat/` | No dedicated status endpoint exists in AIRS/1.0; this sends a heartbeat and reports the result — the one agent-callable operation that reveals liveness. |
| `airs_heartbeat()` | `POST .../heartbeat/` | Maintains the Dead Man's Switch Guardrail. |
| `airs_report_usage(cost_usd, prompt_tokens=0, completion_tokens=0)` | `POST .../report-usage/` | Reports LLM cost/usage against the token's budget. |
| `airs_list_pending_actions()` | `GET .../pending-actions/` | Tenxyte's reference implementation currently scopes this to the Delegating User's own human authentication — expect a structured `PERMISSION_DENIED`-shaped error against Tenxyte specifically; kept for AIRS/1.0 servers that do expose it to the agent side. |

Every tool that fails (suspended, revoked, expired token; a capability the server doesn't
announce) raises a structured error — a JSON-shaped message carrying `code`/`reason` — rather
than crashing the server process (spec/airs/AIRS-1.0.md §8, Requirement 5.5).

**Deliberately absent** (No_Privilege_Amplification_Rule, design.md D3): no tool creates an
Agent Token, and no tool confirms or denies a HITL Pending Action. Both stay strictly on the
human side of Tenxyte's own API — this server never holds a human credential.

## Claude Desktop configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tenxyte-airs": {
      "command": "uvx",
      "args": ["tenxyte-mcp-server"],
      "env": {
        "TENXYTE_BASE_URL": "https://your-server.example.com/api/v1/auth",
        "TENXYTE_AGENT_TOKEN": "the-raw-token-value-returned-at-issuance",
        "TENXYTE_AGENT_TOKEN_ID": "42"
      }
    }
  }
}
```

## Resources

- `airs://token/status` — read-only mirror of `airs_token_status()`.
- `airs://budget` — the discovery document's active Conformance Levels and configured limits.

## License

MIT (this package). The AIRS/1.0 specification it implements is separately licensed CC BY 4.0 —
see [`spec/airs/LICENSE`](../../spec/airs/LICENSE).
