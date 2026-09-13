# API Stability & Versioning Policy

This document is Tenxyte's **Stability Contract**: it defines exactly what is covered by our
backward-compatibility guarantee (the **Public API Surface**), the versioning policy that governs
changes to it, and what is explicitly excluded from that guarantee.

If something is not listed here, treat it as an implementation detail that can change in a MINOR
or PATCH release without notice.

## SemVer Policy

Tenxyte follows [Semantic Versioning 2.0.0](https://semver.org/) applied to the Public API Surface
defined below:

- **MAJOR** (`X.0.0`) — may contain breaking changes to the Public API Surface. Breaking changes
  are only ever released in a MAJOR version.
- **MINOR** (`1.X.0`) — additive changes only: new endpoints, new settings, new optional
  parameters, new decorators, new exported symbols. Existing behavior is preserved.
- **PATCH** (`1.0.X`) — bug fixes and security fixes that do not change the documented contract
  (a fix that makes behavior match its documentation is a PATCH, even if it changes observable
  behavior that was previously undocumented or contradicted the docs).

## Deprecation Policy

No element of the Public API Surface is removed without going through this cycle:

1. The element is marked deprecated in its docstring/documentation and a `DeprecationWarning` is
   emitted at the relevant call site (import, function call, or settings access) starting from a
   MINOR release.
2. The deprecated element remains fully functional for **at least one full MINOR version** after
   the warning is introduced.
3. Removal happens only in the next MAJOR version, and is listed under "Removed" in the CHANGELOG
   entry for that MAJOR release.

Example: if a setting is deprecated in `1.3.0`, it remains functional through the entire `1.x`
line and can only be removed in `2.0.0`.

## Public API Surface

The Public API Surface consists of exactly the following six categories.

### 1. HTTP Endpoints

Every endpoint documented in [`endpoints.md`](endpoints.md) — its path, HTTP method, request
fields, response shape, and status codes — is covered. `endpoints.md` is the normative,
exhaustive source; this document does not duplicate it. At a category level, this includes:
registration and login (email/phone), token refresh/logout, social login (multi-provider),
passwordless OTP login, magic links, password management, 2FA (TOTP), RBAC (roles/permissions/user
assignments), organizations (B2B multi-tenant), applications management, and the AIRS agent-token
endpoints.

Undocumented endpoints, undocumented response fields, and internal/admin-only endpoints not listed
in `endpoints.md` are **not** covered.

### 2. Settings (`TENXYTE_*`)

Every setting documented in [`settings.md`](settings.md) — its name, default value, and accepted
type/values — is covered, including the `TENXYTE_SHORTCUT_SECURE_MODE` presets and every setting
they resolve to. `settings.md` is the normative, exhaustive source.

Settings not listed in `settings.md`, and the *specific numeric/behavioral defaults chosen inside*
a `TENXYTE_SHORTCUT_SECURE_MODE` preset for a setting the preset does not individually document,
are implementation details of the preset and may be tuned in a MINOR release to improve the
security posture of that preset.

### 3. Abstract Models

The following abstract base classes, exported from `tenxyte.models`, and their currently
documented fields:

- `AbstractUser`
- `AbstractRole`
- `AbstractPermission`
- `AbstractApplication`

Subclassing these and overriding `TENXYTE_USER_MODEL` / `TENXYTE_ROLE_MODEL` /
`TENXYTE_PERMISSION_MODEL` / `TENXYTE_APPLICATION_MODEL` is a covered, supported integration
pattern. Concrete (non-abstract) internal models (e.g. `RefreshToken`, `AuditLog`,
`SocialConnection`) and their internal field layout are **not** part of the Public API Surface
beyond what is reachable through documented endpoints — they may gain fields in a MINOR release.

### 4. Public Decorators

Exported from `tenxyte.decorators`:

`require_jwt`, `require_verified_email`, `require_verified_phone`, `rate_limit`, `require_role`,
`require_any_role`, `require_all_roles`, `require_permission`, `require_any_permission`,
`require_all_permissions`, `require_org_context`, `require_org_membership`, `require_org_role`,
`require_org_permission`, `require_org_owner`, `require_org_admin`, `require_agent_clearance`,
and the `get_client_ip` helper.

Their signatures, the exceptions/responses they produce on failure, and their documented behavior
are covered.

### 5. `tenxyte/__init__.py` and `tenxyte.core` Exports

**Top-level (`import tenxyte`)** — always importable, with or without Django installed:

- `tenxyte.__version__`

**Django-dependent top-level symbols** — resolved lazily; importable and usable once
`tenxyte[django]` is installed, and raise `TenxyteMissingDependencyError` (a subclass of
`ImportError`) with an explicit `pip install tenxyte[django]` message otherwise:

- `tenxyte.setup`
- `tenxyte.AbstractUser`, `tenxyte.AbstractRole`, `tenxyte.AbstractPermission`,
  `tenxyte.AbstractApplication`
- `tenxyte.get_user_model`, `tenxyte.get_role_model`, `tenxyte.get_permission_model`,
  `tenxyte.get_application_model`

**`tenxyte.core` (`tenxyte.core.__all__`)** — the framework-agnostic Core layer, always
importable regardless of which framework adapter is installed. The exact set of symbols is
whatever `tenxyte.core.__all__` lists at the current release (`Settings`, `JWTService`,
`TOTPService`, `WebAuthnService`, `MagicLinkService`, `EmailService`, `CacheService`,
`TaskService`, and their associated data classes/schemas). Additions to this list are MINOR
changes; the internal module layout of `tenxyte.core` (which `.py` file defines which symbol) is
**not** covered — import from `tenxyte.core` directly, not from a specific submodule, to stay
within the contract.

### 6. Error Response Format

Every error response returned by a documented endpoint follows this shape:

```json
{
  "error": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "details": {}
}
```

`error` and `code` are always present strings; `details` is always present and is an object
(empty `{}` when there is nothing to add, or a field-keyed map of validation errors). The exact
wording of `error` messages is **not** covered (may be reworded in a PATCH release); the presence
of the three keys, their types, and documented `code` values for a given endpoint **are** covered.

## What Is NOT Covered

The following are explicitly excluded from the stability guarantee and may change in any release,
including PATCH:

- Any module, function, class, or attribute whose name starts with an underscore (`_`), at any
  level of the package (e.g. `tenxyte._internal`, `SomeClass._helper`).
- Internal test helpers and fixtures under `tests/`.
- Undocumented behavior — i.e. anything not stated in `endpoints.md`, `settings.md`, this document,
  or a docstring of a symbol listed above. If the code does something the docs don't describe,
  the docs (and this list) are the contract, not the incidental behavior.
- The internal module layout of `tenxyte.core` (see §5 above).
- Concrete (non-abstract) model internals beyond documented endpoint-visible fields.
- Database migration file names/numbering (the resulting schema, reachable through documented
  models, is covered; the migration history mechanics are not).
- CLI output formatting of management commands (`tenxyte_quickstart`, `tenxyte_seed`,
  `tenxyte_cleanup`, `tenxyte_purge_audit_logs`) beyond their documented exit codes and effects.
- Log message text and logger names.

## Verifying This Contract

The set of symbols in category 5 above is enforced by an automated snapshot test
(`tests/core/test_public_api_snapshot.py`) that fails the build if a previously exported public
symbol from `tenxyte/__init__.py` disappears without going through the deprecation cycle.

## See Also

- [`endpoints.md`](endpoints.md) — full HTTP API reference.
- [`settings.md`](settings.md) — full settings reference.
- [`SECURITY.md`](../../SECURITY.md) — vulnerability disclosure policy and supported versions.
- [`MIGRATION_GUIDE.md`](MIGRATION_GUIDE.md) — version-to-version migration instructions,
  including the `0.9 → 1.0` packaging change.
