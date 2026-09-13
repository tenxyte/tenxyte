# Pre-Audit Self-Assessment — OWASP ASVS L2 (targeted)

**Status:** internal self-assessment, prepared ahead of the external audit defined in
`audit-scope.md`. This is not a substitute for the external audit — it exists to reduce the
auditor's discovery cost and to give a written baseline they can challenge.

**Framework:** [OWASP Application Security Verification Standard (ASVS) 4.0.3](https://owasp.org/www-project-application-security-verification-standard/),
Level 2, restricted to the sections most relevant to an authentication/access-control library:
**V2 Authentication**, **V3 Session Management**, **V6 Cryptography**.

**Legend:** ✅ Pass · ❌ Fail / gap · N/A Not applicable to a library (integrator responsibility)

---

## V2 — Authentication

| # | Requirement (paraphrased) | Status | Code reference |
|---|---|---|---|
| 2.1.1 | Passwords ≥ 12 characters permitted | ✅ | `TENXYTE_PASSWORD_MIN_LENGTH` (default supports ≥ 12) |
| 2.1.2 | Passwords ≥ 64 characters permitted (no arbitrary short max) | ✅ | length validated against `TENXYTE_PASSWORD_MAX_LENGTH`, not hardcoded low |
| 2.1.7 | Passwords checked against breach corpus | ✅ | HaveIBeenPwned k-anonymity check, `TENXYTE_BREACH_CHECK_ENABLED` |
| 2.1.9 | No composition rules that reduce entropy without benefit | ⚠️ | configurable complexity rules exist (`TENXYTE_PASSWORD_REQUIRE_*`) — auditor should confirm defaults don't force low-entropy patterns |
| 2.2.1 | Anti-automation on authentication (rate limiting) | ✅ | `LoginThrottle`, `TENXYTE_RATE_LIMITING_ENABLED`, progressive account lockout |
| 2.2.2 | Weak/leaked credential detection triggers step-up, not silent accept | ✅ | breach check blocks registration/reset when enabled |
| 2.2.3 | Anti-automation does not create a self-DoS vector via account lockout | ⚠️ | lockout is per-account by design — auditor should confirm it cannot be weaponized to lock out arbitrary victims via unauthenticated login attempts alone |
| 2.3.1 | Default/initial passwords not reusable / forced-change path | N/A | Tenxyte does not ship default user accounts; `tenxyte_quickstart` generates random application credentials, printed once |
| 2.4.x | Credential storage — passwords hashed with a memory-hard/adaptive algorithm | ✅ | `bcrypt` (adaptive, salted) |
| 2.5.x | Credential recovery does not reveal account existence | ✅ | password reset returns a generic response regardless of account existence |
| 2.6.x | Look-up secret verifiers (backup codes) single-use, sufficient entropy | ✅ | 2FA backup codes, single-use, generated with `secrets`-grade randomness |
| 2.7.x | Out-of-band verifiers (OTP email/SMS) expire, rate-limited, not predictable | ✅ | `CodeReplayProtection`, TTL-bound OTP, rate-limited endpoints |
| 2.8.x | TOTP implementation follows RFC 6238, secret ≥ 128 bits, rate-limited verify | ✅ | `pyotp`-based, secret encrypted at rest, `TOTPService` |
| 2.9.x | Cryptographic authenticators (WebAuthn) — verified against RP ID and origin | ⚠️ | delegated to the `webauthn` library — auditor should confirm `WEBAUTHN_RP_ID` is validated against the actual request origin at the call site, not merely passed through |

## V3 — Session Management

| # | Requirement (paraphrased) | Status | Code reference |
|---|---|---|---|
| 3.1.1 | Session tokens never in the URL | ✅ | JWT access/refresh always in body/header, never query string |
| 3.2.1 | Session tokens generated with a CSPRNG, sufficient entropy | ✅ | refresh tokens via Python `secrets`; JWT via HMAC/RSA signature, not guessable |
| 3.2.3 | Session tokens stored with sufficient protection (hashed if reusable) | ✅ | `RefreshToken` stores only a SHA-256 hash, never the raw token |
| 3.3.1 | Logout invalidates the session server-side, not just client-side | ✅ | `logout` blacklists the access token, revokes the refresh token |
| 3.3.2 | Absolute/idle session timeouts enforced | ✅ | `TENXYTE_JWT_ACCESS_TOKEN_LIFETIME`, refresh token expiry |
| 3.4.x | Cookie-based sessions (if used) set `Secure`, `HttpOnly`, `SameSite` | N/A | Tenxyte's default flow is header-based Bearer JWT, not cookies; integrators using a cookie-mode SDK should verify these flags at the host application level |
| 3.5.x | Stateless session tokens (JWT) validated for signature, `exp`, `iss`/`aud` where applicable, and cannot be re-used after logout | ⚠️ | signature and `exp` validated; blacklist covers logout — auditor should confirm blacklist check is applied uniformly across *all* protected endpoints, including any that bypass the standard decorator |
| 3.6.x | Re-authentication required for sensitive transactions | ✅ | `TENXYTE_REQUIRE_2FA_FOR_STAFF`-style step-up for privileged roles; password change requires current password |
| 3.7.1 | Session termination on password change / suspected compromise | ✅ | `logout/all` revokes all refresh tokens for the user; password change can trigger this |

## V6 — Cryptography

| # | Requirement (paraphrased) | Status | Code reference |
|---|---|---|---|
| 6.1.1 | No sensitive data classification gaps for regulated data | N/A | data classification is an integrator responsibility; Tenxyte encrypts the fields it controls that are inherently secret (TOTP seed) |
| 6.2.1 | All cryptographic modules fail securely | ✅ | JWKS/JWT validation is fail-closed (see Apple Sign-In design, `docs/security-audit/threat-model.md`) |
| 6.2.2 | Industry-proven/certified cryptographic implementations used, no custom crypto | ✅ | `cryptography` (PyCA), `PyJWT`, `bcrypt`, `pyotp` — no hand-rolled primitives |
| 6.2.3 | Encryption keys not hardcoded | ✅ | `TENXYTE_JWT_SECRET_KEY` and TOTP encryption key sourced from settings/environment; DEBUG-mode ephemeral key is explicitly randomized per process, not a fixed default |
| 6.2.5 | Cryptographic randomness uses a CSPRNG | ✅ | Python `secrets` module used for tokens/codes, not `random` |
| 6.3.1 | No proprietary/broken algorithms in active use | ✅ | AES (via `cryptography`) for TOTP secret encryption, HMAC/RSA/ECDSA for JWT, bcrypt for passwords |
| 6.4.1 | Key management — rotation supported for the JWT signing key | ⚠️ | rotation is possible via settings change but there is no built-in dual-key grace-period rotation mechanism — flagged as a design gap for auditor review, not a defect |

---

## Summary of Flagged Items (⚠️) for Auditor Priority

1. **2.1.9** — confirm default password composition rules do not force low-entropy patterns.
2. **2.2.3** — confirm account lockout cannot be used to lock out an arbitrary victim via
   unauthenticated attempts alone (lockout-as-DoS).
3. **2.9.x** — confirm WebAuthn RP ID / origin validation is enforced at the actual verification
   call site.
4. **3.5.x** — confirm the JWT blacklist check is applied uniformly on every protected code path.
5. **6.4.1** — JWT signing-key rotation has no built-in dual-key grace period; document as a known
   limitation or address in a future release.

## See Also

- [`threat-model.md`](threat-model.md) — assets, actors, attack surfaces.
- [`audit-scope.md`](audit-scope.md) — perimeter proposed to the external auditor.
- [`SECURITY.md`](../../SECURITY.md) — vulnerability disclosure policy.
