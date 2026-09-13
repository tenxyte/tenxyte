# How to give an AI agent a credit card limit

*Draft — spec z_aud_2, task 11.2. Grounded in [AIRS/1.0](../AIRS-1.0.md) and the preliminary
benchmark run in [`../../../benchmarks/airs/RESULTS.md`](../../../benchmarks/airs/RESULTS.md).
Re-run benchmarks on a dedicated machine and update the cited numbers before publishing (see
that file's own caveat).*

---

Every framework for building AI agents has converged on the same shape: give the agent a tool,
give the tool an API key, and hope the agent's judgment holds up under a prompt injection, a
hallucinated function call, or a bug in your own tool code. That bet is fine for a weekend
project. It is not fine for an agent that can issue refunds, send emails as your company, or
spend money.

The missing layer isn't a smarter model. It's the identity layer between "an agent" and "the
things an agent is allowed to do" — the same layer every other class of software got decades ago
(OAuth scopes, IAM roles, database grants) and that agent frameworks have, so far, mostly skipped.

## The three questions nobody's tooling answers

Ask these about your current agent stack:

1. **If this agent's key leaks, what's the blast radius?** For most stacks: everything the
   underlying API key can do, forever, until someone notices and rotates it.
2. **Can a human step in before an irreversible action, not just after?** For most stacks: no —
   the tool call already happened by the time anyone sees a log line.
3. **If the agent starts misbehaving — a loop, a runaway spend, a compromised prompt — what stops
   it automatically, without a human watching in real time?** For most stacks: nothing.

AIRS (AI Responsibility & Security) is our answer to all three, and as of this release it's not
just Tenxyte's internal implementation detail — it's [an open specification](../AIRS-1.0.md),
independent of Tenxyte or Django, that any server can implement and any client can target.

## The model, in one paragraph

An agent never holds its own authority. A human delegates a strict subset of their own
permissions into a short-lived **Agent Token** — scoped, time-boxed, and revocable. Every request
the agent makes is checked twice: once against what the token was granted, and once against
whether the delegating human *still* holds that permission right now (`answers question 1`).
Specific actions can require live human confirmation before they execute — a `202`, not a silent
`200` (`answers question 2`). And a set of Guardrails — a circuit breaker, a dead man's switch,
a budget cap — can suspend the token automatically, no human required (`answers question 3`).

None of this is new cryptography. It's applying identity-and-access-management discipline to a
category of software that mostly hasn't had any.

## What "giving an agent a credit card limit" actually looks like

```python
POST /ai/tokens/
Authorization: Bearer <human's own JWT>

{
  "agent_id": "expense-processing-agent",
  "permissions": ["expenses.read", "expenses.file"],
  "budget_limit_usd": 5.00,
  "circuit_breaker": {"max_requests_per_minute": 30}
}
```

That budget cap isn't advisory. Report usage against it, and the moment the agent crosses $5,
the token suspends — every subsequent request gets rejected before it reaches your business
logic, not after. On our preliminary benchmark run, the overhead of that double permission
check — the difference between a plain authenticated request and one going through full AIRS
Double Validation — was on the order of ten milliseconds. See
[`benchmarks/airs/RESULTS.md`](../../../benchmarks/airs/RESULTS.md) for the numbers and their
important caveats before you cite them.

## Why this is a spec, not a feature

We could have kept this as a Tenxyte-only feature. We didn't, for the same reason OAuth isn't
a Google-only feature: an identity layer only works as a standard if agent frameworks can target
it without depending on whoever wrote the server. That's why this release ships:

- **[AIRS/1.0](../AIRS-1.0.md)** — the normative spec itself, CC BY 4.0, with no normative
  reference to Tenxyte or Django.
- **A [Conformance Suite](../conformance/)** — a black-box HTTP test suite that validates *any*
  server against the spec, including a negative control proving it actually discriminates
  conformant from non-conformant implementations.
- **[`tenxyte-langchain`](../../../integrations/langchain/)** and
  **[`tenxyte-mcp-server`](../../../integrations/mcp-server/)** — pure HTTP connectors for the
  two places agent builders actually live, neither one importing a line of Tenxyte's own code.
- **A [CrewAI example](../../../examples/crewai/)** running the whole loop — issuance, HITL,
  budget suspension — end to end, with no LLM API key required to try it.

Tenxyte is the reference implementation. It doesn't have to be the only one.

## Try it

- Read the spec: [`spec/airs/AIRS-1.0.md`](../AIRS-1.0.md)
- Run the CrewAI example: `cd examples/crewai && docker compose up --build`
- Wire it into LangChain: `pip install tenxyte-langchain`
- Wire it into Claude Desktop: `pip install tenxyte-mcp-server` (see its README for the config
  block)

---

*Draft status: benchmark numbers cited above are preliminary (see the linked RESULTS.md) — replace
with an official run before this goes out. Author, publication venue, and exact API-key/pricing
example (currently illustrative) to be finalized before publishing.*
