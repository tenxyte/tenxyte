# Threat Model

**Status:** living document, prepared as input to an external security audit engagement.
**Scope:** the Tenxyte library as deployed by an integrator (self-hosted, source-available).

This is a lightweight [STRIDE](https://en.wikipedia.org/wiki/STRIDE_model)-informed threat model,
organized per security domain rather than per data-flow diagram, since Tenxyte is a library
embedded into a host application rather than a standalone service.

## Protected Assets

| Asset | Where it lives | Why it matters |
|---|---|---|
| User passwords | `bcrypt` hash in `User.password` | Compromise → credential stuffing against other services |
| JWT signing key | `TENXYTE_JWT_SECRET_KEY` (host settings) | Compromise → forge arbitrary access tokens for any user |
| Refresh tokens | Hashed (SHA-256) in `RefreshToken` table | Compromise of the hash alone is not exploitable; compromise of the raw token (in transit/client storage) allows session takeover until expiry/rotation |
| TOTP secrets | Encrypted at rest (`User.totp_secret`) | Compromise → bypass of 2FA for the affected account |
| WebAuthn public keys & sign counters | `WebAuthnCredential` | Integrity matters more than confidentiality (public keys); sign-counter tampering could mask credential cloning |
| Magic link tokens | Single-use, hashed, short TTL | Compromise (before use/expiry) → account takeover without password |
| Agent tokens (AIRS) | Hashed (`AgentToken.token_hash`), scoped permissions | Compromise → actions within the token's granted scope, bounded by circuit breaker/budget |
| Audit log entries | `AuditLog` table | Integrity matters for forensic trust; an attacker who can forge/delete entries can hide their tracks |
| OAuth client secrets (social login, incl. Apple's `.p8` key) | Host settings (`GOOGLE_CLIENT_SECRET`, `APPLE_PRIVATE_KEY`, etc.) | Compromise → impersonate the application to the OAuth provider |
| Application `X-Access-Key` / `X-Access-Secret` | `Application` model, secret hashed | Compromise → bypass application-level auth gate |
| Session/device metadata | `RefreshToken.device_info`, `ip_address` | Privacy-sensitive; used for lockout/anomaly decisions |

## Threat Actors

| Actor | Capability | Motivation |
|---|---|---|
| **Anonymous internet attacker** | Unauthenticated HTTP requests to public endpoints | Account takeover, credential harvesting, DoS |
| **Registered non-privileged user** | Valid JWT for their own account | Privilege escalation, access to other tenants'/users' data, RBAC bypass |
| **Malicious or compromised admin/staff account** | RBAC-granted elevated permissions | Data exfiltration, abuse of admin-only endpoints, audit log tampering |
| **AI agent (via AgentToken)** | Scoped permissions borrowed from a delegating user, no direct credentials | Runaway/erroneous actions beyond intended scope; prompt-injection-driven over-reach |
| **Insider with database access** | Direct DB read/write, bypassing the API | Bulk credential/token exfiltration; this is why hashing-at-rest (passwords, refresh tokens, agent tokens) and encryption-at-rest (TOTP secrets) matter even against this actor |
| **Man-in-the-middle (if TLS is misconfigured downstream)** | Network interception between client and host application | Token/credential interception — out of Tenxyte's direct control (see Deployment Assumptions) |
| **Malicious OAuth provider response / compromised provider account** | Controls the identity claims returned by Google/GitHub/Microsoft/Facebook/Apple | Account fusion abuse, unverified-email takeover (mitigated by F-03, see below) |

## Attack Surfaces per Domain

### JWT Lifecycle

- **Threats:** signature forgery (weak/leaked `TENXYTE_JWT_SECRET_KEY`), algorithm confusion,
  replay of a blacklisted/revoked access token, refresh-token replay after rotation, token
  lifetime too long for the deployment's risk profile.
- **Existing mitigations:** signature verification via `PyJWT` with a fixed algorithm (no `alg`
  negotiation from the token), access-token blacklisting on logout via cache-backed
  `TokenBlacklistService`, refresh tokens stored hashed (never the raw value), configurable
  rotation (`TENXYTE_JWT_ROTATE_REFRESH_TOKENS`), `TENXYTE_SHORTCUT_SECURE_MODE` presets tuning
  lifetimes down for higher-risk profiles.
- **Auditor focus:** confirm no algorithm-confusion path exists between symmetric/asymmetric
  configuration; confirm blacklist check happens on every protected request, not just at login;
  confirm rotation invalidates the prior refresh token atomically (no window where both are valid).

### OTP Flows (email / SMS)

- **Threats:** brute-force of the OTP code, code reuse (replay), enumeration of valid
  phone/email via response-timing or error-message differences, OTP interception via a
  compromised SMS/email channel.
- **Existing mitigations:** `CodeReplayProtection` (Core), rate limiting on OTP request/verify
  endpoints, generic error messages to resist enumeration.
- **Auditor focus:** confirm OTP verify endpoints are rate-limited independently of the login
  rate limiter (an attacker with a valid session for step 1 could otherwise brute-force step 2
  unthrottled); confirm code length/entropy is adequate against online brute-force within the
  rate-limit window.

### WebAuthn (Passkeys / FIDO2)

- **Threats:** challenge replay, missing origin/RP ID validation, sign-counter regression not
  detected (cloned authenticator), registration/authentication ceremony confusion.
- **Existing mitigations:** challenge stored server-side with TTL (`WebAuthnChallenge`,
  `WEBAUTHN_CHALLENGE_EXPIRY_SECONDS`), delegation to the `webauthn` library for ceremony/
  signature validation.
- **Auditor focus:** confirm challenges are single-use and bound to the specific
  registration/authentication attempt; confirm sign-counter regression is checked and rejected;
  confirm `WEBAUTHN_RP_ID` is validated against the request origin, not merely configured.

### AIRS Agent Tokens

- **Threats:** scope escalation beyond `granted_permissions`, circuit breaker bypass (rapid
  parallel requests racing the counter), budget-limit bypass (negative or manipulated
  `cost_usd` reporting), dead man's switch bypass (heartbeat spoofing), HITL confirmation token
  reuse or prediction.
- **Existing mitigations:** double RBAC validation (agent scope AND delegating user's own
  permissions, both required), `AgentPendingAction` confirmation tokens for HITL flows, budget
  and circuit-breaker fields on `AgentToken`.
- **Auditor focus:** this is the highest-priority domain for the external audit (see
  `audit-scope.md`). Specifically: is circuit-breaker counting atomic under concurrent requests;
  can `cost_usd` be reported as negative or otherwise used to reset accumulated spend; is a HITL
  confirmation token single-use and expiring; does token suspension take effect on the *next*
  request or only after an async check (i.e. is there a window of continued access after
  suspension conditions are met).

### Password Reset

- **Threats:** token guessing, token reuse, user enumeration via response differences between
  existing/non-existing accounts, reset-token leakage via Referer header or logs.
- **Existing mitigations:** single-use tokens with TTL, generic response regardless of account
  existence, breach-check integration (HaveIBeenPwned k-anonymity) on the new password.
- **Auditor focus:** confirm the reset endpoint's response and timing are indistinguishable for
  existing vs. non-existing accounts; confirm the reset token is invalidated after first use even
  if the request to set the new password subsequently fails validation.

### Organizations Isolation (Multi-Tenant)

- **Threats:** cross-organization data leakage (missing tenant filter on a query), role
  inheritance miscalculation granting unintended permissions down the hierarchy, invitation-token
  reuse or cross-organization redemption, `X-Org-Slug` spoofing to act in an organization the
  user is not a member of.
- **Existing mitigations:** `require_org_context` / `require_org_membership` /
  `require_org_permission` decorators, org-scoped role inheritance
  (`TENXYTE_ORG_ROLE_INHERITANCE`), tenant context resolved server-side from an authenticated
  membership lookup rather than trusting the header alone.
- **Auditor focus:** confirm every org-scoped queryset filters by the resolved membership, not by
  the raw `X-Org-Slug` header value; confirm invitation tokens are bound to a specific
  organization and email, and cannot be redeemed by a different account.

### Social Login / Account Fusion (F-03)

- **Threats:** account takeover via an unverified email at a social provider matching an
  existing local account (the provider vouches for an email it never actually verified);
  provider `email_verified` type confusion (string `"true"`/`"false"` vs. boolean) silently
  treated as verified.
- **Existing mitigations:** F-03 — fusion into an existing email account is refused whenever
  `email_verified` is not strictly `True` after normalization.
- **Auditor focus:** confirm the normalization of `email_verified` across all providers
  (including Apple's string-typed claim) is correct and fails closed (unknown/malformed value
  treated as unverified, not verified).

## Deployment Assumptions

The threat model above assumes the following are the integrator's responsibility, **not**
Tenxyte's:

- TLS is terminated in front of the application (reverse proxy/load balancer); Tenxyte does not
  implement its own transport encryption.
- The database is a trusted component reachable only by the application (not directly exposed to
  the internet); Tenxyte's hashing/encryption-at-rest choices are defense-in-depth against an
  insider or a partial DB compromise, not a substitute for DB access control.
- `TENXYTE_JWT_SECRET_KEY` and OAuth client secrets are provisioned via a secrets manager or
  environment variables with appropriate access control, not committed to source control.
- The host application's own code (custom views, custom models extending the abstract base
  classes) does not itself introduce authorization bypasses around Tenxyte's decorators.
- Outbound network access to third-party identity providers (Google, GitHub, Microsoft, Facebook,
  Apple JWKS endpoints, HaveIBeenPwned) is available and not subject to DNS spoofing (standard TLS
  certificate validation is relied upon).

## See Also

- [`audit-scope.md`](audit-scope.md) — the perimeter proposed for the external audit.
- [`pre-audit-checklist.md`](pre-audit-checklist.md) — our OWASP ASVS L2 self-assessment.
- [`SECURITY.md`](../../SECURITY.md) — vulnerability disclosure policy.
