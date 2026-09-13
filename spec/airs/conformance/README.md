# AIRS Conformance Suite

A black-box, HTTP-only pytest suite that validates any server against
[AIRS/1.0](../AIRS-1.0.md). It never imports server-side code — every test speaks only the wire
protocol the specification defines, discovered at runtime via the target's
[Discovery Endpoint](../AIRS-1.0.md#9-discovery).

## Quick start

```bash
pip install -r requirements.txt
pytest . -m "not negative_control" \
    --airs-base-url https://your-server.example.com \
    --airs-discovery-path /api/v1/auth/ai/.well-known/airs/ \
    --airs-user-jwt "$USER_JWT" \
    --airs-test-permission conformance.test
```

Test modules are skipped automatically for any Conformance Level your target's discovery document
does not announce (`core` is the only one that always runs).

## Options

| Option | Required | Purpose |
|---|---|---|
| `--airs-base-url` | Yes | Scheme + host of the target (no path). |
| `--airs-discovery-path` | No (default `/ai/.well-known/airs/`) | Path of the Discovery Endpoint. |
| `--airs-user-jwt` | Yes | Bearer JWT for the Delegating User the suite acts as. |
| `--airs-test-permission` | No (default `conformance.test`) | A permission code this user holds. |
| `--airs-other-permission` | No (default `security.view`) | A *second* permission the user holds, used only to scope a token away from `--airs-test-permission`. |
| `--airs-app-key` / `--airs-app-secret` | No | Application credentials, if your target requires them. |
| `--airs-conformance-probe-path` | No | See "Why a probe endpoint?" below. |
| `--airs-hitl-probe-path` | No | Same, for the HITL contract. |
| `--airs-audit-log-path` | No | A human-authenticated endpoint listing recent audit entries, used only to verify [AIRS-TRACE-3] persistence is *publicly* retrievable (optional — the clause itself only requires operator-level persistence). |

## Why a probe endpoint?

AIRS's core guarantee — a permission-gated business action — is provided by *integrator* code
(a decorator like Tenxyte's `@require_agent_clearance`) applied to endpoints the integrator
writes, not by a fixed protocol endpoint. There is therefore no generic way to black-box-test
Double Validation or the HITL contract without a live endpoint gated that way. If your deployment
has one, point `--airs-conformance-probe-path` / `--airs-hitl-probe-path` at it (see
`tenxyte_ci/demo_views.py` for a two-line reference example); tests needing them skip cleanly
otherwise.

## Reverse-direction Double Validation

One `core` test ([AIRS-CORE-6](b): the Delegating User loses the permission after issuance)
needs a way to revoke a permission from that user mid-test. This specification does not mandate
how (it's outside AIRS's own wire protocol), so it's an optional pytest fixture contract:
implement `revoke_delegating_user_permission(user_jwt, permission_code)` (and, to avoid leaving
your test user's permissions permanently mutated, its counterpart
`grant_delegating_user_permission`) in your own conftest.py or a plugin loaded via `-p`. See
`tenxyte_ci/revoke_permission_hook.py` for Tenxyte's own implementation, loaded in CI via:

```bash
pytest . -p spec.airs.conformance.tenxyte_ci.revoke_permission_hook ...
```

## Negative control

`negative_mock/` ships a deliberately non-conformant server (violates three clauses: no
`airs_version` in discovery, accepts any Agent Token regardless of status, and never returns 202
for a HITL-gated action). `negative_mock/test_negative_mock_fails.py` starts it and asserts a
suite run against it **fails** — proving this suite actually discriminates. It's tagged
`negative_control` and excluded from the options above (`-m "not negative_control"`) since it
needs no target credentials; run it on its own:

```bash
pytest negative_mock/
```

## Running against Tenxyte locally

`tenxyte_ci/` is the demo project CI (and this walkthrough) use to stand up a real, ephemeral
Tenxyte instance with every Conformance Level enabled:

```bash
python -m spec.airs.conformance.tenxyte_ci.seed_and_serve --port 8811
# prints a JSON line with base_url / user_jwt / probe paths once ready, then serves forever
```

In another terminal, feed those values to `pytest . -m "not negative_control" ...` as above (see
`.github/workflows/ci.yml`'s `airs-conformance` job for the exact invocation CI uses).
