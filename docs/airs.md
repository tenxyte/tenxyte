# Tenxyte AIRS (AI Responsibility & Security)

## Table of Contents

- [Tenxyte AIRS (AI Responsibility & Security)](#tenxyte-airs-ai-responsibility-security)
  - [Key Features](#key-features)
    - [1. Core Agentic Parity (AgentToken)](#1-core-agentic-parity-agenttoken)
    - [2. Circuit Breaker & Rate Limiting](#2-circuit-breaker-rate-limiting)
    - [3. Human in the Loop (HITL)](#3-human-in-the-loop-hitl)
    - [4. Guardrails: PII Redaction & Budget](#4-guardrails-pii-redaction-budget)
    - [5. Forensic Audit](#5-forensic-audit)
  - [Configuration](#configuration)

---

Tenxyte AIRS is a comprehensive suite of responsibility, security, and safeguards for integrated AI agents. It addresses major challenges posed by LLMs and agentic models in production environments (e.g., EchoLeak, Shadow Escape).

## Key Features

### 1. Core Agentic Parity (AgentToken)
The `AgentToken` concept encapsulates an agent's security information.
- **Secure Delegation**: An agent borrows a user's permissions without handling their credentials.
- **Strict RBAC**: Double permission check; the agent must be authorized, and the delegating user must also hold the underlying rights.

### 2. Circuit Breaker & Rate Limiting
An autonomous firewall to prevent runaway behavior (infinite loops, exfiltration):
- **Automatic Disabling**: Triggers on abnormal requests (sliding window).
- **Dead Man's Switch**: Requires periodic heartbeats to prove the control container is intact. Otherwise, automatic suspension.

### 3. Human in the Loop (HITL)
Decorators like `@require_agent_clearance` redirect agent requests if human confirmation is needed, returning `202 Accepted` and pausing execution until the workflow is approved.
- **Global List**: Configurable actions (`TENXYTE_AIRS_CONFIRMATION_REQUIRED`) that will always go through HITL.

### 4. Guardrails: PII Redaction & Budget
- **PII RedactionMiddleware**: Automatically intercepts and anonymizes PII (`***REDACTED***`) in JSON responses for agent requesters, preventing LLMs from ingesting sensitive data.
- **Budget Tracking**: Precise LLM cost tracking (`POST /ai/tokens/{id}/report-usage/`) to limit an agent's financial impact.

### 5. Forensic Audit
- **Traceability via X-Prompt-Trace-ID**: Linked in the `AuditLog` to precisely map "Which prompt resulted in which backend action".

## Configuration

Settings available to be defined in your Django `settings.py` (defaults managed via `src/tenxyte/conf/airs.py`):
- `TENXYTE_AIRS_ENABLED` (Default: `True`)
- `TENXYTE_AIRS_TOKEN_MAX_LIFETIME` (Default: `86400`)
- `TENXYTE_AIRS_DEFAULT_EXPIRY` (Default: `3600`)
- `TENXYTE_AIRS_REQUIRE_EXPLICIT_PERMISSIONS` (Default: `True`)
- `TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED` (Default: `True`)
- `TENXYTE_AIRS_DEFAULT_MAX_RPM` (Default: `60`)
- `TENXYTE_AIRS_DEFAULT_MAX_TOTAL` (Default: `1000`)
- `TENXYTE_AIRS_DEFAULT_MAX_FAILURES` (Default: `10`)
- `TENXYTE_AIRS_CONFIRMATION_REQUIRED` (Array of permission codes, e.g., `['users.delete']`)
- `TENXYTE_AIRS_REDACT_PII` (Default: `False`)
- `TENXYTE_AIRS_BUDGET_TRACKING_ENABLED` (Default: `False`)
