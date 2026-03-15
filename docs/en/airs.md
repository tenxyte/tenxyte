# Tenxyte AIRS (AI Responsibility & Security)

## Table of Contents

- [Overview](#overview)
- [1. Core Agentic Parity — AgentToken](#1-core-agentic-parity--agenttoken)
- [2. Circuit Breaker & Rate Limiting](#2-circuit-breaker--rate-limiting)
- [3. Human in the Loop (HITL)](#3-human-in-the-loop-hitl)
- [4. Guardrails: PII Redaction & Budget Tracking](#4-guardrails-pii-redaction--budget-tracking)
- [5. Forensic Audit](#5-forensic-audit)
- [Configuration Reference](#configuration-reference)

---

## Overview

Tenxyte AIRS is a comprehensive suite of responsibility, security, and safeguards for integrated AI agents. It addresses major challenges posed by LLMs and agentic models in production environments (e.g., EchoLeak, Shadow Escape, runaway spend).

**Core principle**: An AI agent never acts on its own authority. It borrows a human user's identity and permissions via a scoped, time-limited token (`AgentToken`), and every action it takes is auditable, controllable, and suspendable.

---

## 1. Core Agentic Parity — AgentToken

An `AgentToken` is the identity token issued to an AI agent. It enables **secure delegation**: the agent acts on behalf of a human user, with a strict subset of their permissions, without ever handling user credentials.

### Creation (API)

```http
POST /ai/tokens/
Authorization: Bearer <user_jwt>
Content-Type: application/json

{
  "agent_id": "finance-agent-v2",
  "expires_in": 3600,
  "permissions": ["read:reports", "write:invoices"],
  "organization": "acme-corp",
  "budget_limit_usd": 5.00,
  "circuit_breaker": {
    "max_requests_per_minute": 30,
    "max_requests_total": 500
  }
}
```

**Response (201):**
```json
{
  "id": 42,
  "token": "eKj3...raw_token...Xz9",
  "agent_id": "finance-agent-v2",
  "status": "ACTIVE",
  "expires_at": "2024-01-20T16:00:00Z"
}
```

> ⚠️ The raw `token` value is returned **only once** at creation. Store it securely — only its SHA-256 hash is persisted in the database.

The agent then uses `AgentBearer <token>` in the `Authorization` header for all subsequent requests.

### Double RBAC Validation

Every request made with an `AgentToken` goes through two permission checks:

1. **Agent scope check**: Does the `AgentToken` include the required permission in its `granted_permissions`?
2. **Human check**: Does the delegating user *still* hold that permission in the database (or within the organization)?

If either check fails, the request is rejected with `403 Forbidden`.

### Token Lifecycle

| Status | Description |
|---|---|
| `ACTIVE` | Token is valid and can be used |
| `SUSPENDED` | Automatically disabled (circuit breaker, budget, heartbeat) |
| `REVOKED` | Manually revoked — permanent, irreversible |
| `EXPIRED` | Lifetime exceeded `expires_at` |

---

## 2. Circuit Breaker & Rate Limiting

The circuit breaker is an autonomous firewall that protects against runaway agent behavior: infinite loops, data exfiltration spikes, or unexpected failure cascades.

### Configurable thresholds (per token)

| Field | Default | Description |
|---|---|---|
| `max_requests_per_minute` | 60 | Sliding window RPM limit (via cache) |
| `max_requests_total` | 1000 | Absolute request cap for the token lifetime |
| `max_failed_requests` | 10 | Max consecutive errors before suspension |

If any threshold is exceeded, the token is automatically moved to `SUSPENDED` status with the appropriate reason:

| Reason | Trigger |
|---|---|
| `RATE_LIMIT` | RPM or total requests exceeded |
| `ANOMALY` | Max failed requests exceeded |
| `HEARTBEAT_MISSING` | Dead Man's Switch timeout |
| `BUDGET_EXCEEDED` | LLM cost exceeded budget limit |

### Dead Man's Switch

If `heartbeat_required_every` (seconds) is set, the agent must periodically call:

```http
POST /ai/tokens/{id}/heartbeat/
Authorization: AgentBearer <raw_token>
```

If no heartbeat is received within the configured interval, the token is automatically suspended with `HEARTBEAT_MISSING`. This guarantees that if the orchestration container crashes or is compromised, the agent loses its access automatically.

### Emergency Kill Switch

To immediately revoke **all** active tokens for a user (nuclear option):

```http
POST /ai/tokens/revoke-all/
Authorization: Bearer <user_jwt>
```

---

## 3. Human in the Loop (HITL)

Some actions are too sensitive for an AI agent to execute autonomously. HITL ensures a human must explicitly approve them before they execute.

### How it works

Endpoints decorated with `@require_agent_clearance(human_in_the_loop_required=True)` behave differently when called by an agent:

1. The agent calls the endpoint normally.
2. Instead of executing, Tenxyte creates an `AgentPendingAction` and returns **`202 Accepted`** (not `200`).
3. The human is notified (email, webhook, etc.) with a `confirmation_token`.
4. The human confirms or denies via the API.
5. The agent can poll or be notified to retry.

### Global HITL actions

Configure actions that **always** require human approval in `settings.py`:

```python
TENXYTE_AIRS_CONFIRMATION_REQUIRED = [
    "users.delete",
    "billing.refund",
    "data.export_all",
]
```

### Confirm/Deny endpoints

```http
# Human approves
POST /ai/pending-actions/confirm/
{ "token": "hitl_a1b2c3d4..." }

# Human denies
POST /ai/pending-actions/deny/
{ "token": "hitl_a1b2c3d4..." }
```

The agent's pending actions can also be listed:

```http
GET /ai/pending-actions/
Authorization: Bearer <user_jwt>
```

---

## 4. Guardrails: PII Redaction & Budget Tracking

### PII Redaction

When `TENXYTE_AIRS_REDACT_PII = True`, a middleware intercepts all JSON responses sent to an `AgentBearer` requester and automatically anonymizes sensitive fields (emails, phone numbers, IBANs, etc.) by replacing them with `***REDACTED***`.

This prevents LLMs from ingesting or memorizing personally identifiable information from your backend.

---

### Budget Tracking

Budget tracking allows you to cap the financial impact an agent can have via LLM API calls (OpenAI, Anthropic, Google, etc.).

> **Important**: Tenxyte does **not** know LLM pricing. It is model-agnostic. Your code is responsible for converting token counts into a USD cost and reporting it. Tenxyte only accumulates the reported `cost_usd` and suspends the agent when the limit is reached.

#### Enable in settings

```python
TENXYTE_AIRS_BUDGET_TRACKING_ENABLED = True
```

#### Create a token with a budget cap

```python
from tenxyte.services.agent_service import AgentTokenService

service = AgentTokenService()
token = service.create(
    triggered_by=user,
    application=app,
    granted_permissions=[],
    budget_limit_usd=1.00,  # $1.00 maximum
)
```

#### Calculate the cost in your LLM wrapper

You are responsible for maintaining a pricing table and computing costs:

```python
# Example pricing table (keep updated as providers change rates)
MODEL_PRICING = {
    "claude-sonnet-4-5":    {"input": 3.00,  "output": 15.00},  # per million tokens
    "gemini-1.5-pro":       {"input": 3.50,  "output": 10.50},
    "gpt-4o":               {"input": 5.00,  "output": 15.00},
}

def calculate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (
        (prompt_tokens    / 1_000_000) * pricing["input"] +
        (completion_tokens / 1_000_000) * pricing["output"]
    )
```

#### Report usage after each LLM call

**Via Python service:**
```python
# After calling your LLM (Anthropic, Google, OpenAI, etc.)
prompt_tokens     = response.usage.input_tokens    # from provider's response
completion_tokens = response.usage.output_tokens

cost = calculate_cost_usd("claude-sonnet-4-5", prompt_tokens, completion_tokens)

success = service.report_usage(token, cost_usd=cost)

if not success:
    # Budget exceeded → token is now SUSPENDED
    # The agent will receive 401/403 errors on subsequent requests
    raise Exception("Agent budget exhausted")
```

**Via REST API (from within the agent itself):**
```http
POST /ai/tokens/{id}/report-usage/
Authorization: AgentBearer <raw_token>
Content-Type: application/json

{
  "cost_usd": 0.042,
  "prompt_tokens": 1250,
  "completion_tokens": 450
}
```

**Response when budget is exceeded (403):**
```json
{
  "error": "Budget exceeded",
  "status": "suspended"
}
```

#### What happens internally

```
report_usage(cost_usd=0.60, budget_limit=0.50)
    ↓
current_spend_usd += 0.60   →  0.60
current_spend_usd (0.60) >= budget_limit (0.50)
    ↓
token.status      = SUSPENDED
token.suspended_reason = BUDGET_EXCEEDED
    ↓
return False  (all future requests with this token → 403)
```

---

## 5. Forensic Audit

Every agent request can carry an `X-Prompt-Trace-ID` header. This ID is:

- Stored in `AgentPendingAction.prompt_trace_id`
- Linked in the `AuditLog`

This allows precise traceability: *"which user prompt triggered which backend action"*, enabling post-incident investigation and compliance reporting.

```http
POST /ai/tokens/{id}/some-action/
Authorization: AgentBearer <raw_token>
X-Prompt-Trace-ID: trace_7f3a2b9c-...
```

---

## Configuration Reference

All settings are defined in `settings.py`. Defaults are managed via `src/tenxyte/conf/airs.py`.

| Setting | Default | Description |
|---|---|---|
| `TENXYTE_AIRS_ENABLED` | `True` | Master switch for AIRS |
| `TENXYTE_AIRS_TOKEN_MAX_LIFETIME` | `86400` | Maximum token lifetime (seconds) |
| `TENXYTE_AIRS_DEFAULT_EXPIRY` | `3600` | Default token expiry if not specified (seconds) |
| `TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS` | `True` | Tokens must declare explicit permissions |
| `TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED` | `True` | Enable/disable circuit breaker |
| `TENXYTE_AIRS_DEFAULT_MAX_RPM` | `60` | Default max requests per minute |
| `TENXYTE_AIRS_DEFAULT_MAX_TOTAL` | `1000` | Default total request cap |
| `TENXYTE_AIRS_DEFAULT_MAX_FAILURES` | `10` | Default max failed requests before suspension |
| `TENXYTE_AIRS_CONFIRMATION_REQUIRED` | `[]` | List of permission codes always requiring HITL |
| `TENXYTE_AIRS_REDACT_PII` | `False` | Enable PII redaction for agent responses |
| `TENXYTE_AIRS_BUDGET_TRACKING_ENABLED` | `False` | Enable LLM budget tracking |
