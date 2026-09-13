# AIRS — AI Responsibility & Security Specification

**Version:** 1.0
**Status:** Stable
**License:** [CC BY 4.0](./LICENSE) (this document only — implementations are licensed
independently)

## Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT",
"RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

Every normative clause in this document carries a stable identifier of the form
`[AIRS-<LEVEL>-n]`, where `<LEVEL>` is one of `CORE`, `HITL`, `GUARDS`, `BUDGET`, `TRACE`, or
`DISC`. These identifiers are referenced by the [AIRS Conformance Suite](conformance/) and
MUST NOT be renumbered once published; a clause that is later removed is marked *(retired)*
rather than reused for a different rule.

This document defines a wire protocol and a set of behavioral guarantees. It does not mandate
any particular programming language, web framework, or database. **Tenxyte** is cited in the
non-normative [Annex A](#annex-a-reference-implementation-non-normative) as the reference
implementation of this specification, but nothing in the normative body of this document depends
on Tenxyte, Django, or any other implementation detail.

---

## Table of Contents

1. [Terminology](#1-terminology)
2. [Delegation Model](#2-delegation-model)
3. [Agent Token Lifecycle](#3-agent-token-lifecycle)
4. [Wire Protocol](#4-wire-protocol)
5. [Human-in-the-Loop (HITL)](#5-human-in-the-loop-hitl)
6. [Guardrails](#6-guardrails)
7. [Normative REST Endpoints](#7-normative-rest-endpoints)
8. [Error Codes](#8-error-codes)
9. [Discovery](#9-discovery)
10. [Conformance Levels](#10-conformance-levels)
11. [Security Considerations](#11-security-considerations)
- [Annex A: Reference Implementation (non-normative)](#annex-a-reference-implementation-non-normative)

---

## 1. Terminology

- **Delegating User**: the human principal who authorizes an Agent to act on their behalf. The
  Delegating User's own permissions bound what the Agent may ever be granted.
- **Agent**: an autonomous or semi-autonomous piece of software (typically, but not necessarily,
  built on a large language model) that performs actions against an AIRS-conformant server by
  presenting an Agent Token.
- **Agent Token**: a bearer credential, opaque to the Agent, issued by the server on behalf of a
  Delegating User, scoped to an explicit subset of that user's permissions, and bounded in time.
- **Granted Permissions**: the fixed set of permission codes attached to an Agent Token at
  issuance, defining the maximum scope that token can ever exercise, independent of any later
  change to the Delegating User's own permissions.
- **Double Validation**: the rule that every permission check on a request made with an Agent
  Token MUST verify, independently, both (a) that the requested permission is within the token's
  Granted Permissions, and (b) that the Delegating User currently holds that permission.
- **Guardrail**: an automated, non-bypassable control that can autonomously move an Agent Token
  out of the `ACTIVE` state without any human action in the loop (circuit breaker, dead man's
  switch, budget cap).
- **HITL (Human-in-the-Loop) Action**: an operation that a server operator has designated as
  requiring live human approval before it takes effect, even when requested by a validly
  authenticated Agent Token with sufficient Granted Permissions.
- **Confirmation Token**: a single-use, unguessable identifier issued when a HITL Action is
  requested, presented back to the server by the human to approve or deny it, and by the Agent to
  replay the original request once approved.
- **Prompt Trace ID**: an opaque, caller-supplied identifier propagated by the Agent on a request,
  intended to correlate a server-side action with the upstream user prompt or LLM invocation that
  caused it.
- **Conformance Level**: a named, independently claimable subset of this specification that an
  implementation may support (see [§10](#10-conformance-levels)).
- **AIRS Server**: any HTTP server implementing the normative behavior of this specification.
- **AIRS Client**: any Agent-side software (a library, a connector, or hand-written code) that
  issues requests conforming to [§4](#4-wire-protocol).

## 2. Delegation Model

`[AIRS-CORE-1]` An Agent MUST NOT possess or exercise any authority of its own. Every action an
Agent performs against an AIRS Server MUST be traceable to exactly one Delegating User whose own
permissions bound what that action was allowed to do.

`[AIRS-CORE-2]` An Agent Token MUST be issued only by an authenticated Delegating User, and MUST
be scoped, at issuance, to Granted Permissions that are a subset of the Delegating User's
permissions at that moment. The server MUST reject the issuance of an Agent Token that requests a
permission the Delegating User does not hold.

`[AIRS-CORE-3]` Once issued, an Agent Token's Granted Permissions are fixed. Reducing the
Delegating User's own permissions after issuance MUST take effect on the Agent Token's *effective*
authority immediately (see Double Validation, [AIRS-CORE-6]), without requiring the Agent Token
itself to be modified or reissued.

`[AIRS-CORE-4]` Double Validation ([AIRS-CORE-6]) applies to every request authenticated with an
Agent Token. There is no operation defined by this specification that bypasses it.

## 3. Agent Token Lifecycle

An Agent Token has exactly one status at any time, drawn from the following state machine:

```
                 issue
                   │
                   ▼
              ┌─────────┐
     ┌───────▶│ ACTIVE  │────────┐
     │        └────┬────┘        │
     │             │             │ revoke (human, irreversible)
     │  guardrail   │ expires_at │
     │  trip        │ elapsed    │
     │        ┌─────▼─────┐      │
     │        │  EXPIRED  │      │
     │        └───────────┘      │
     │                           ▼
┌────┴──────┐              ┌───────────┐
│ SUSPENDED │◀─────────────┤  REVOKED  │  (terminal — no transition leaves REVOKED)
└───────────┘   (no path)  └───────────┘
```

`[AIRS-CORE-5]` An Agent Token MUST have exactly one of the following four statuses at all times:
`ACTIVE`, `SUSPENDED`, `REVOKED`, or `EXPIRED`.

- **`ACTIVE`**: the token is valid and MAY be used, subject to Double Validation and Guardrails.
- **`SUSPENDED`**: the token has been automatically disabled by a Guardrail, or manually disabled
  by the Delegating User, without permanently destroying it. This specification does not define
  any operation that transitions a token out of `SUSPENDED` back to `ACTIVE`; recovery, if an
  implementation chooses to offer it, is implementation-defined and non-normative.
- **`REVOKED`**: the token has been permanently and deliberately destroyed by a human action. This
  state is terminal: no operation defined by this specification transitions a token out of
  `REVOKED`.
- **`EXPIRED`**: the token's declared lifetime has elapsed. This state is terminal in the same
  sense as `REVOKED`.

`[AIRS-CORE-6]` A request authenticated with an Agent Token MUST be accepted only if BOTH of the
following hold for every permission the request requires:
  (a) the permission is present in the token's Granted Permissions, AND
  (b) the Delegating User currently holds that permission (directly, or within the addressed
      organization context, per the server's own authorization model).
If either check fails, the server MUST reject the request with the `PERMISSION_DENIED` error
family ([§8](#8-error-codes)) and MUST NOT partially execute it.

`[AIRS-CORE-7]` When a token transitions to `SUSPENDED`, the server MUST record a
**Suspension Reason** drawn from a fixed vocabulary of exactly five values:

| Suspension Reason | Trigger |
|---|---|
| `RATE_LIMIT` | A rate or total request Guardrail threshold was exceeded ([§6.1](#61-circuit-breaker)). |
| `ANOMALY` | A failure-rate Guardrail threshold was exceeded ([§6.1](#61-circuit-breaker)). |
| `HEARTBEAT_MISSING` | The Dead Man's Switch Guardrail fired ([§6.2](#62-dead-mans-switch)). |
| `BUDGET_EXCEEDED` | The Budget Guardrail fired ([§6.3](#63-budget)). |
| `MANUAL` | A human (the Delegating User, or an operator acting on their behalf) suspended the token directly, with no automated cause. |

`[AIRS-CORE-8]` A `REVOKED` token MUST also carry a reason drawn from the same vocabulary as
[AIRS-CORE-7], defaulting to `MANUAL` when no more specific reason applies.

`[AIRS-CORE-9]` Every request authenticated with a token in any state other than `ACTIVE` MUST be
rejected before any Double Validation or business logic runs, using the corresponding error code
family in [§8](#8-error-codes). A server MUST NOT execute side effects for a non-`ACTIVE` token
under any circumstance.

`[AIRS-CORE-10]` Expiry ([§3](#3-agent-token-lifecycle), `EXPIRED`) MAY be evaluated lazily (at
the time the token is next presented) rather than by a background process; regardless of
evaluation strategy, a request presenting an Agent Token whose declared lifetime has elapsed MUST
be treated identically to one presenting a token already recorded as `EXPIRED`.

## 4. Wire Protocol

### 4.1 Authentication scheme: `AgentBearer`

`[AIRS-CORE-11]` An AIRS Client MUST authenticate every request carrying an Agent Token using the
HTTP `Authorization` header with the scheme name `AgentBearer`:

```
Authorization: AgentBearer <raw_token>
```

`[AIRS-CORE-12]` `<raw_token>` MUST be the raw, unhashed token value returned to the Delegating
User exactly once, at issuance ([§7.1](#71-token-issuance)). An AIRS Server MUST NOT persist the
raw token value anywhere, in any form, after the issuance response has been produced; only a
one-way cryptographic hash of it MAY be stored, used solely to look up the token on subsequent
requests.

`[AIRS-CORE-13]` The `AgentBearer` scheme is distinct from, and MUST NOT be accepted
interchangeably with, any scheme used to authenticate the Delegating User directly (e.g. a
standard `Bearer <jwt>` scheme for human/session authentication). A server MUST be able to
distinguish, from the `Authorization` header alone, whether a request is an Agent request or a
human request.

### 4.2 Header: `X-Action-Confirmation`

`[AIRS-HITL-1]` An AIRS Client replaying a request after a HITL Action ([§5](#5-human-in-the-loop-hitl))
was approved MUST include the approved Confirmation Token in the `X-Action-Confirmation` request
header:

```
X-Action-Confirmation: <confirmation_token>
```

### 4.3 Header: `X-Prompt-Trace-ID`

`[AIRS-TRACE-1]` An AIRS Client MAY include a Prompt Trace ID on any request via the
`X-Prompt-Trace-ID` header:

```
X-Prompt-Trace-ID: <trace_id>
```

`[AIRS-TRACE-2]` An AIRS Server MUST treat `X-Prompt-Trace-ID` as an opaque string of at most 128
characters restricted to `[A-Za-z0-9_-]`. A server MUST NOT reject a request solely because this
header is malformed or absent; it MAY instead silently discard a malformed value (i.e. behave as
if the header had not been sent) rather than persisting or propagating it.

`[AIRS-TRACE-3]` When present and well-formed, a server offering the `trace` Conformance Level
MUST persist the Prompt Trace ID alongside any HITL Action created by the same request
([§5](#5-human-in-the-loop-hitl)), so that a subsequently confirmed or denied action can be
correlated back to the prompt that triggered it.

## 5. Human-in-the-Loop (HITL)

`[AIRS-HITL-2]` A server operator MAY designate specific operations (by permission code, by
endpoint, or by both) as requiring human confirmation even when requested by an Agent Token that
already satisfies Double Validation ([AIRS-CORE-6]).

`[AIRS-HITL-3]` When an Agent Token requests an operation designated per [AIRS-HITL-2], and no
prior approval for this exact request is on record, the server MUST NOT execute the operation.
Instead it MUST:
  1. create a **Pending Action** recording, at minimum, the requested permission, the target
     endpoint, and (for state-changing methods) the request payload;
  2. generate a fresh, unguessable Confirmation Token for that Pending Action;
  3. respond with HTTP status **`202 Accepted`** and a JSON body of the shape:
     ```json
     {
       "status": "pending_confirmation",
       "confirmation_token": "<opaque, unguessable string>",
       "expires_at": "<ISO 8601 timestamp>"
     }
     ```
     (an implementation MAY include additional informational fields, e.g. a human-readable
     `message`).

`[AIRS-HITL-4]` A Pending Action MUST have a finite lifetime after which it can no longer be
confirmed or denied. The default lifetime, absent server-specific configuration, is
**10 minutes** from creation.

`[AIRS-HITL-5]` A human MUST be able to **confirm** or **deny** a Pending Action by presenting its
Confirmation Token through a channel authenticated as the Delegating User (or an operator acting
on their behalf) — never through the Agent's own `AgentBearer` credential. Confirming or denying
an action that: does not exist, has already been confirmed, has already been denied, or has
expired, MUST fail without side effect.

`[AIRS-HITL-6]` Once a Pending Action has been confirmed, the Agent MUST be able to replay the
original request (identical method, path, and body) with the addition of the
`X-Action-Confirmation` header ([§4.2](#42-header-x-action-confirmation)) carrying its
Confirmation Token, and the server MUST then execute the operation as if it had been approved
inline, exactly once. A denied, expired, or already-consumed Confirmation Token MUST NOT permit
the operation to execute.

`[AIRS-HITL-7]` A Confirmation Token MUST be single-use for the purpose of authorizing execution:
once the guarded operation has been successfully executed via [AIRS-HITL-6], presenting the same
Confirmation Token again MUST NOT execute it a second time.

## 6. Guardrails

Guardrails are automated controls that can suspend an Agent Token without any human decision in
the loop. An AIRS Server MAY implement any subset of the Guardrails below; each is independently
gated by the `guards` or `budget` Conformance Level ([§10](#10-conformance-levels)).

### 6.1 Circuit Breaker

`[AIRS-GUARDS-1]` An AIRS Server offering the `guards` Conformance Level MUST support, per Agent
Token, at least the following configurable thresholds: a maximum number of requests per a fixed
time window (e.g. per minute), a maximum number of total requests over the token's lifetime, and
a maximum number of failed requests.

`[AIRS-GUARDS-2]` When any circuit-breaker threshold configured on a token is exceeded, the server
MUST transition that token to `SUSPENDED` with reason `RATE_LIMIT` (rate or total-request
thresholds) or `ANOMALY` (failure-count threshold), and MUST reject the request that caused the
threshold to be exceeded.

### 6.2 Dead Man's Switch

`[AIRS-GUARDS-3]` An Agent Token MAY declare a required heartbeat interval. When it does, the
Agent MUST periodically signal liveness to the server within that interval; a server offering the
`guards` Conformance Level MUST expose a mechanism for the Agent to do so using its own
`AgentBearer` credential.

`[AIRS-GUARDS-4]` If a server-observed gap since the last liveness signal exceeds the token's
declared interval, the server MUST transition the token to `SUSPENDED` with reason
`HEARTBEAT_MISSING`, no later than the next time that token is presented on a request.

### 6.3 Budget

`[AIRS-BUDGET-1]` An Agent Token MAY declare a maximum cumulative monetary spend
(implementation unit: USD). A server offering the `budget` Conformance Level MUST expose a
mechanism for the Agent to report incremental usage (at minimum, a monetary cost, and SHOULD
also accept prompt/completion token counts for informational purposes) against its own token.

`[AIRS-BUDGET-2]` The server MUST accumulate reported cost against the token's running total.
Note: this specification does not require the server to compute cost from token counts or to know
any LLM provider's pricing — cost computation is the Agent's or its operator's responsibility;
the server's obligation is limited to accumulation and threshold enforcement.

`[AIRS-BUDGET-3]` When a token's accumulated reported cost reaches or exceeds its declared budget
limit, the server MUST transition the token to `SUSPENDED` with reason `BUDGET_EXCEEDED`, and the
usage-reporting response itself MUST indicate that the token is now suspended rather than
silently accepting the report.

## 7. Normative REST Endpoints

The concrete URL paths below are given **relative to a base path communicated to the Agent by the
Discovery document** ([§9](#9-discovery)); this specification does not mandate a fixed absolute
path, only a stable set of logical operations and their request/response contracts. Path segments
in `{braces}` are implementation-defined identifiers (e.g. a token ID).

| Logical name | Method | Purpose | Auth | Level |
|---|---|---|---|---|
| `tokens` (create) | `POST` | Issue a new Agent Token for the caller (the Delegating User) | human | `core` |
| `tokens` (list) | `GET` | List the caller's own Agent Tokens | human | `core` |
| `token_detail` | `GET` | Retrieve one Agent Token's status | human | `core` |
| `token_revoke` | `POST` | Revoke one Agent Token (terminal, `REVOKED`) | human | `core` |
| `token_suspend` | `POST` | Manually suspend one Agent Token (`SUSPENDED`, reason `MANUAL`) | human | `core` |
| `token_revoke_all` | `POST` | Revoke every `ACTIVE` Agent Token belonging to the caller | human | `core` |
| `heartbeat` | `POST` | Signal liveness for the Dead Man's Switch ([AIRS-GUARDS-3]) | agent | `guards` |
| `report_usage` | `POST` | Report incremental cost/usage ([AIRS-BUDGET-1]) | agent | `budget` |
| `pending_actions` (list) | `GET` | List the caller's outstanding HITL Pending Actions | human | `hitl` |
| `pending_action_confirm` | `POST` | Approve a Pending Action by Confirmation Token | human | `hitl` |
| `pending_action_deny` | `POST` | Deny a Pending Action by Confirmation Token | human | `hitl` |
| `discovery` | `GET` | Discovery document ([§9](#9-discovery)) | none | — |

`[AIRS-CORE-14]` `tokens` (create) MUST authenticate the caller as a human Delegating User, MUST
validate the requested Granted Permissions against [AIRS-CORE-2], and MUST return the raw token
value in the response body exactly once, alongside the token's identifier, initial status, and
expiry.

`[AIRS-CORE-15]` `token_revoke` and `token_revoke_all` MUST authenticate the caller as the
Delegating User who owns the target token(s) (or an operator authorized to act for them); an
Agent MUST NOT be able to revoke its own token using its `AgentBearer` credential.

`[AIRS-HITL-8]` `pending_action_confirm` and `pending_action_deny` MUST authenticate the caller as
a human, and MUST verify that the Pending Action belongs to a token whose Delegating User is the
caller (or an authorized operator), before acting on it.

## 8. Error Codes

`[AIRS-CORE-16]` A server rejecting a request authenticated with a non-`ACTIVE` Agent Token MUST
return an HTTP 4xx status and a machine-readable error code that distinguishes at least the
following families, so that an AIRS Client can react appropriately (e.g. stop retrying):

| Condition | Error family |
|---|---|
| Token not found / malformed / unknown | `AGENT_TOKEN_NOT_FOUND` |
| Token status is `SUSPENDED` | `AGENT_TOKEN_SUSPENDED` (MUST include the Suspension Reason, [AIRS-CORE-7]) |
| Token status is `REVOKED` | `AGENT_TOKEN_REVOKED` |
| Token status is `EXPIRED` | `AGENT_TOKEN_EXPIRED` |
| Double Validation failed ([AIRS-CORE-6]) | `PERMISSION_DENIED` (or a more specific agent-scoped variant) |
| AIRS support disabled server-side | `AIRS_DISABLED` |

`[AIRS-CORE-17]` An AIRS Client MUST treat every error family in [AIRS-CORE-16] as terminal for
the current token: it MUST NOT automatically retry the same request with the same token. This is
a deliberate fail-safe requirement — see [§11](#11-security-considerations).

## 9. Discovery

`[AIRS-DISC-1]` An AIRS Server SHOULD expose a **Discovery Endpoint**: an unauthenticated `GET`
endpoint, at a location the server communicates to integrators out-of-band (e.g. in its own
documentation), returning a JSON document with at least the following fields:

```json
{
  "airs_version": "1.0",
  "conformance": ["core", "hitl", "guards", "trace"],
  "endpoints": { "<logical name>": "<path>", "...": "..." },
  "limits": { "token_max_lifetime": 86400, "default_expiry": 3600 }
}
```

- `airs_version` MUST be the string version of the specification the server implements (e.g.
  `"1.0"`).
- `conformance` MUST be an array of the Conformance Level names ([§10](#10-conformance-levels))
  the server actually enforces at the time of the request — not merely which ones it is capable
  of enforcing.
- `endpoints` MUST map at least the logical names of [§7](#7-normative-rest-endpoints) that the
  server implements to concrete, resolvable paths.
- `limits` MUST report at least `token_max_lifetime` and `default_expiry`, in seconds.

`[AIRS-DISC-2]` The Discovery Endpoint MUST NOT require authentication, and its response MUST NOT
depend on the caller's identity, tenant, or any other per-request state: it advertises
**capabilities**, never data. Two requests to the Discovery Endpoint made under the same server
configuration MUST return identical bodies regardless of who calls it or what data exists in the
server at the time.

`[AIRS-DISC-3]` If AIRS support is disabled entirely on a server that would otherwise offer it,
the Discovery Endpoint MUST respond with an HTTP 404 status and MUST NOT reveal any information
beyond that AIRS is unavailable.

## 10. Conformance Levels

`[AIRS-CORE-18]` This specification defines five independently named Conformance Levels. A server
MUST advertise, via [§9](#9-discovery), exactly the set it actually enforces.

| Level | Requires | Summary |
|---|---|---|
| **`core`** | (mandatory baseline) | Agent Token issuance, `AgentBearer` authentication, Double Validation, revocation, expiry ([§2](#2-delegation-model)–[§4](#4-wire-protocol), [§7](#7-normative-rest-endpoints)). |
| **`hitl`** | `core` | The Pending Action / Confirmation Token contract ([§5](#5-human-in-the-loop-hitl)). |
| **`guards`** | `core` | Circuit breaker and Dead Man's Switch ([§6.1](#61-circuit-breaker), [§6.2](#62-dead-mans-switch)). |
| **`budget`** | `core` | Usage reporting and budget-triggered suspension ([§6.3](#63-budget)). |
| **`trace`** | `core` | Prompt Trace ID propagation and persistence ([§4.3](#43-header-x-prompt-trace-id)). |

`[AIRS-CORE-19]` `core` is the only mandatory level: an implementation claiming any conformance
with this specification at all MUST implement `core` in full. Each other level MAY be claimed or
omitted independently of the others; a server MUST NOT claim a level in its Discovery document
([AIRS-DISC-1]) without satisfying every normative clause tagged with that level's prefix in this
document.

## 11. Security Considerations

`[AIRS-CORE-20]` **Raw token handling.** The raw Agent Token value MUST be transmitted to the
Delegating User exactly once, at issuance, and MUST NOT subsequently be recoverable from the
server by any party, including server operators — only a one-way hash may be retained. Loss of
the raw value by the recipient is unrecoverable by design and requires reissuance.

`[AIRS-CORE-21]` **Privilege amplification.** Because an Agent Token grants a *subset* of a human
identity's authority, any component that holds an Agent Token and is also given the ability to
create new Agent Tokens, confirm HITL Pending Actions, or otherwise act with the Delegating User's
full authority, defeats the purpose of this specification. Implementations of AIRS Clients
(connectors, SDKs, MCP servers, and similar) intended to run **on the Agent's side** of the trust
boundary SHOULD be structurally prevented from performing any of those three operations — this is
a design property of the *client*, not something the wire protocol alone can enforce.

`[AIRS-HITL-9]` **HITL token leakage.** A Confirmation Token is bearer-equivalent for the single
action it guards: anyone who obtains it before the human confirms or denies it can act as the
approving human for that one Pending Action. Delivery channels for Confirmation Tokens (email,
webhook, chat notification, etc.) SHOULD be chosen with this in mind, and Pending Actions SHOULD
have a lifetime short enough to bound the exposure window ([AIRS-HITL-4]).

`[AIRS-TRACE-4]` **Trace-ID PII considerations.** A Prompt Trace ID is opaque to the server, but
an Agent or its operator MUST NOT embed personally identifiable information directly into the
trace identifier itself (e.g. an email address or a raw user prompt), since it may be persisted
and surfaced in audit tooling with different access controls than the original data source. A
Prompt Trace ID SHOULD be an indirection (a run ID, a request ID) that the Agent's own system can
resolve back to sensitive context, rather than the sensitive context itself.

`[AIRS-CORE-22]` **Fail-safe over fail-open.** For every condition in [§8](#8-error-codes), the
correct behavior for both the server and any AIRS Client is to stop, not to guess. A server MUST
reject ambiguous or malformed authentication rather than falling back to any lower-privilege
default; a well-behaved AIRS Client MUST surface a terminal, typed error to its operator rather
than silently retrying or ignoring the failure ([AIRS-CORE-17]).

---

## Annex A: Reference Implementation (non-normative)

This annex is informative only. It has no bearing on conformance to this specification.

**Tenxyte** (https://github.com/tenxyte/tenxyte — MIT licensed) is the reference implementation of
AIRS/1.0. Every normative clause in this document was written and verified against Tenxyte's
existing AIRS implementation (`src/tenxyte/models/agent.py`, `src/tenxyte/services/agent_service.py`,
`src/tenxyte/decorators.py`, `src/tenxyte/middleware.py`, `src/tenxyte/conf/airs.py`); the
Discovery Endpoint ([§9](#9-discovery)) is the only piece of server-side behavior this
specification introduced that did not already exist in Tenxyte prior to AIRS/1.0's publication.

Tenxyte concretely mounts the endpoints of [§7](#7-normative-rest-endpoints) under
`{api_prefix}/auth/ai/`, and its Discovery Endpoint at `{api_prefix}/auth/ai/.well-known/airs/`.
See `docs/en/airs.md` for Tenxyte's own (non-normative) integration guide, and the
[AIRS Conformance Suite](conformance/) for the executable cross-check between this document and
Tenxyte's behavior.

Known implementations of this specification (server or client) are welcome to open a pull request
adding themselves to this annex.
