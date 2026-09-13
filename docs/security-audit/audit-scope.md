# External Security Audit — Proposed Scope

**Status:** proposal, prepared for a prospective external audit vendor. This document defines the
perimeter *offered* for audit; it does not itself constitute the audit.

## In Scope

### Priority 1 — Highest sensitivity

| Module | Path | Why |
|---|---|---|
| JWT service | `src/tenxyte/core/jwt_service.py` | Signature/validation logic for every authenticated request |
| TOTP service | `src/tenxyte/core/totp_service.py` | 2FA secret generation, code verification, replay protection |
| WebAuthn service | `src/tenxyte/core/webauthn_service.py` | Passkey registration/authentication ceremonies |
| Agent service (AIRS) | `src/tenxyte/services/agent_service.py` | Circuit breaker, budget enforcement, HITL — see `threat-model.md` |
| Decorators | `src/tenxyte/decorators.py` | Every authorization gate (`require_jwt`, `require_permission`, `require_org_*`, `require_agent_clearance`) |

### Priority 2 — Core flows

| Flow | Entry points | Why |
|---|---|---|
| Login (email/phone) | `views/*` login endpoints + `services/otp_service.py` | Primary authentication path, account lockout |
| Password reset | `password/reset/*` endpoints | Token handling, enumeration resistance |
| 2FA setup/confirm/disable | `2fa/*` endpoints | State transitions around the 2FA requirement |
| Social login / account fusion | `services/social_auth_service.py`, `views/social_auth_views.py` | F-03 unverified-email fusion refusal, provider trust boundary |

### Priority 3 — Supporting

- `src/tenxyte/authentication.py` — DRF authentication backend wiring.
- `src/tenxyte/adapters/django/middleware.py` — CORS, application auth, tenant context.
- `src/tenxyte/models/base.py` — password hashing, account lockout counters, field-level PII
  exposure (in particular the fields deliberately excluded from `/me/`, per the internal
  `VULN-005` review referenced in serializer comments).
- Rate limiting configuration and its interaction with the endpoints above.

## Explicitly Out of Scope

- Third-party dependency code itself (Django, DRF, `cryptography`, `PyJWT`, `webauthn`, etc.) —
  vulnerabilities there should be reported upstream; see `SECURITY.md` for how Tenxyte handles
  coordinated pinning fixes when a dependency vulnerability affects it.
- The host application's own code (custom views, custom models, custom settings) — the audit
  covers Tenxyte as a library, not a specific integrator's deployment, unless that integrator
  commissions a separate application-level audit.
- Non-security code quality (style, performance, test coverage) except where a quality issue is
  itself the root cause of a security defect.
- The FastAPI adapter (`src/tenxyte/adapters/fastapi/`) — partial/beta support at the time of this
  scope; recommended for a follow-up engagement once it reaches parity with the Django adapter.
- Infrastructure/deployment security (TLS configuration, database hardening, secrets management)
  — these are integrator responsibilities per the Deployment Assumptions in `threat-model.md`.

## Test Environment Provided to the Auditor

- A disposable clone of the repository at the tagged release under audit, with a
  `docker-compose.yml`-based local stack (Django dev server + SQLite or PostgreSQL, per the
  auditor's preference) and a seed script (`tenxyte_seed`) populating representative test data:
  several users across role levels (regular user, org admin, RBAC admin, Django superuser),
  sample organizations with a multi-level hierarchy, sample agent tokens with varied
  budget/circuit-breaker configurations, and sample audit log entries.
- Test credentials for each seeded account, provided out-of-band (not committed to the
  repository).
- Sandbox OAuth app credentials (Google, GitHub, Microsoft, Facebook, Apple) scoped to a test
  callback URL, so social login and Apple Sign-In flows can be exercised end-to-end without
  using production identity provider apps.
- Read access to `threat-model.md` and `pre-audit-checklist.md` as a starting brief.

## Expected Deliverable Format

- A findings report with, per finding: severity (CVSS 3.1 or equivalent), affected
  module/file/line, reproduction steps or proof-of-concept, and a suggested remediation.
- A findings report submitted as (or convertible to) a private GitHub security advisory draft, or
  delivered under an NDA with responsible-disclosure terms consistent with `SECURITY.md`'s
  90-day coordinated-disclosure embargo.
- A closing summary mapping findings against the ASVS L2 sections referenced in
  `pre-audit-checklist.md`, noting any item the self-assessment marked as passing that the
  auditor disagrees with.

## See Also

- [`threat-model.md`](threat-model.md) — assets, actors, attack surfaces.
- [`pre-audit-checklist.md`](pre-audit-checklist.md) — internal self-assessment ahead of the audit.
- [`SECURITY.md`](../../SECURITY.md) — vulnerability disclosure policy governing how findings from
  this audit (and any future report) are handled once the audit is commissioned.
