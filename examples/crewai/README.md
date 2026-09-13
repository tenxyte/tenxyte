# AIRS + CrewAI example

A two-agent [CrewAI](https://www.crewai.com/) crew — a Researcher and a Finance Writer — sharing
one delegated [AIRS/1.0](../../spec/airs/AIRS-1.0.md) Agent Token, demonstrating in one run:

1. **Issuance** — a human (this script, standing in for one) logs in and issues an Agent Token
   scoped to exactly one permission and a small budget.
2. **AgentBearer** — every tool call is authenticated with the token via
   [`tenxyte-langchain`](../../integrations/langchain/).
3. **HITL** — filing an expense report is gated: the server responds `202 pending_confirmation`,
   a human approves it (auto-approved after a short delay in this non-interactive demo — see
   `CREWAI_DEMO_AUTO_CONFIRM` below), and the agent replays the request.
4. **Budget suspension** — reported usage accumulates until the token's budget limit is crossed,
   at which point further usage reports raise `TenxyteBudgetExceededError` — the agent stops,
   which is the point.

This corresponds to `manual_tests.md` **MT-4** in `specs/z_aud_2/` — record the outcome of your
run there.

## Run it

```bash
cd examples/crewai
docker compose up --build
```

This starts two containers:

- `tenxyte` — an ephemeral Tenxyte instance (the same demo project the AIRS Conformance Suite's
  CI job uses, `spec/airs/conformance/tenxyte_ci/`), seeded with a demo user, an application, and
  the `conformance.test` permission, exposing two demo endpoints gated by
  `@require_agent_clearance` (a plain one and an HITL one) — exactly what any real Tenxyte
  integration would write for its own protected business logic.
- `crew` — the CrewAI crew itself (`crew.py`), using a deterministic `FakeScriptedLLM` — **no
  API key required**.

Expect output roughly like:

```
Logging in as the demo user at http://tenxyte:8000/api/v1/auth ...
Issuing a delegated Agent Token (budget_limit_usd=0.05) ...
Agent Token id=1, status=ACTIVE
... crew executes the Researcher and Finance Writer tasks ...

>>> HITL: action pending human approval. confirmation_token=...
>>> CREWAI_DEMO_AUTO_CONFIRM=1: confirming automatically for this walkthrough.

=== Crew result ===
...

=== Demonstrating budget suspension ===
Usage reported; token still active.
Usage reported; token still active.
Token suspended as expected: ...BUDGET_EXCEEDED...
```

## Using a real LLM

Set `USE_REAL_LLM=1` in `docker-compose.yml`'s `crew` service environment, and configure your
provider's API key the way CrewAI/LangChain expects (e.g. `OPENAI_API_KEY`) — then edit
`crew.py`'s `llm = ...` line to construct your provider's LangChain chat model instead of
`FakeScriptedLLM`.

## Environment variables (`crew` service)

| Variable | Default | Purpose |
|---|---|---|
| `TENXYTE_BASE_URL` | `http://tenxyte:8000/api/v1/auth` | Where the crew logs in and issues its Agent Token. |
| `CREWAI_DEMO_BUDGET_USD` | `0.05` | The Agent Token's budget limit, kept small to trigger suspension quickly. |
| `CREWAI_DEMO_AUTO_CONFIRM` | `1` | Auto-confirm the HITL action after a short delay (non-interactive demo). Set to `0` to pause for a real human `Enter` keypress instead. |
| `USE_REAL_LLM` | `0` | `1` to use a real LLM instead of the deterministic fake. |

## Running without Docker

```bash
pip install -r requirements.txt
pip install -e ../../integrations/langchain
# In another terminal: python -m spec.airs.conformance.tenxyte_ci.seed_and_serve --port 8811
TENXYTE_BASE_URL=http://localhost:8811/api/v1/auth python crew.py
```
