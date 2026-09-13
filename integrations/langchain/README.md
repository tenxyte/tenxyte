# tenxyte-langchain

LangChain / LangGraph connector for [AIRS/1.0](../../spec/airs/AIRS-1.0.md) — the open
specification for AI agent identity, delegation, and Human-in-the-Loop governance that
[Tenxyte](https://github.com/tenxyte/tenxyte) implements.

A pure HTTP client: it never imports the `tenxyte` package, and works against any
AIRS-conformant server (discovered at runtime, never hardcoded).

## Install

```bash
pip install tenxyte-langchain
```

## Minimal example

```python
import httpx
from tenxyte_langchain import TenxyteAIRSClient, TenxyteAgentAuth, TenxyteHITLPending

# 1. A human issues the Agent Token once, out-of-band (e.g. via Tenxyte's own /ai/tokens/ API
#    with their own Bearer JWT) — this connector never creates tokens itself.
AGENT_TOKEN = "the-raw-token-value-returned-at-issuance"
TOKEN_ID = 42

client = TenxyteAIRSClient("https://your-tenxyte-server.example.com", agent_token=AGENT_TOKEN)

auth = TenxyteAgentAuth(
    AGENT_TOKEN,
    client=client,
    token_id=TOKEN_ID,
    heartbeat_required_every=300,  # matches what the token was issued with, if a DMS is set
)

with httpx.Client(base_url=client.base_url, auth=auth) as http:
    # Every request through `http` now carries AgentBearer + X-Prompt-Trace-ID automatically.
    response = http.post(client.endpoint("report_usage", id=TOKEN_ID), json={"cost_usd": 0.01})

try:
    client.request("POST", "/business/invoices/", json={"amount": 500})
except TenxyteHITLPending as pending:
    # A human approves pending.confirmation_token through Tenxyte's own API — outside this
    # package, by design (see spec/airs/AIRS-1.0.md §11, privilege amplification).
    ...
    response = pending.resume()  # after approval
```

## Budget tracking with a LangChain chain

```python
from tenxyte_langchain import TenxyteBudgetCallbackHandler, TenxyteBudgetExceededError

budget_callback = TenxyteBudgetCallbackHandler(
    client, TOKEN_ID, cost_per_prompt_token=3e-6, cost_per_completion_token=15e-6
)

try:
    llm.invoke("...", config={"callbacks": [budget_callback]})
except TenxyteBudgetExceededError:
    # The token has been suspended server-side — stop the agent, don't retry.
    raise
```

## HITL with LangGraph `interrupt()`

```python
from langgraph.types import interrupt
from tenxyte_langchain import TenxyteHITLPending


def sensitive_tool(payload):
    try:
        return client.request("POST", "/business/refunds/", json=payload)
    except TenxyteHITLPending as pending:
        # Suspend the graph; a human approves confirmation_token via Tenxyte's own API.
        interrupt({"confirmation_token": pending.confirmation_token, "expires_at": pending.expires_at})
        return pending.resume()
```

## Design notes

- **`TenxyteAIRSClient`**: low-level, resolves every endpoint through the target's Discovery
  Endpoint — nothing is hardcoded.
- **`TenxyteAgentAuth`**: an `httpx.Auth` — attach it to any `httpx.Client(auth=...)` for
  automatic `AgentBearer` + `X-Prompt-Trace-ID` on every request, plus an optional background
  heartbeat thread.
- **Fail-safe by design**: every terminal Agent Token condition (suspended, revoked, expired,
  budget-exceeded) raises a distinct, typed exception. None of them are meant to be retried with
  the same token — see [AIRS-CORE-17] and [AIRS-CORE-22] in the specification.
- **No privilege amplification**: this package never creates Agent Tokens and never confirms or
  denies a HITL action itself — both stay strictly on the human side of Tenxyte's own API.

## License

MIT (this package). The AIRS/1.0 specification it implements is separately licensed CC BY 4.0 —
see [`spec/airs/LICENSE`](../../spec/airs/LICENSE).
