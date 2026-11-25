# js-contract-backend

Contract_Fixtures dockerized demo backend for the `tenxyte-js` monorepo's E2E tests
(specs/02-console-runtime, tâche 5.1). A real FastAPI_Adapter instance, real HTTP, real bcrypt
password hashes — no mocks — seeded with a **deterministic** set of fixtures covering every
section of the console (auth, account, organizations, RBAC, applications, AIRS, admin, GDPR) so
E2E tests can rely on known credentials and pre-existing state instead of provisioning everything
through the UI on every run.

This is a test fixture backend, not a production deployment example — see
[`examples/deployment/`](../deployment/) for a hardened, Postgres/Redis-backed Dockerfile.

> Renamed 2026-09 (specs/02-console-runtime décision D6, `tenxyte-js`): the JS-side console this
> backend serves is `@tenxyte/registry` + `@tenxyte/react`/`@tenxyte/vue` bindings, not the
> `@tenxyte/ui-headless`/`@tenxyte/ui` packages this README used to reference — those were never
> published. The seed was also extended well past its original single-fixture scope; see below.

## Run it

```bash
docker compose -f examples/js-contract-backend/docker-compose.yml up --build
```

The server listens on `http://localhost:8000`, API prefix `/api/v1` (so, e.g.,
`http://localhost:8000/api/v1/login/email/`). On startup it prints one JSON line to stdout with
the connection info a CI orchestration script can parse — see [`seed_and_serve.py`](seed_and_serve.py)'s
own docstring and the `info = {...}` dict at the end of `_run()` for the exact, current shape
rather than a copy here that can drift; every fixture below has an entry in it (id, and a
`totp_secret` for the two 2FA-enabled accounts).

Three feature flags are turned on that are **off by default** on this adapter — found by actually
calling the corresponding endpoints and hitting a 404/403, not by reading the settings list first:

- `TENXYTE_ORGANIZATIONS_ENABLED` — off by default 404s every `/organizations/*`, `/org-roles/`
  route (`app.py` only registers `orgs_router` when this is set, mirroring Django's own
  conditionally-registered `urlpatterns` block).
- `TENXYTE_OTP_LOGIN_ENABLED` — off by default rejects every `/login/otp/*` call (the console's
  `/auth/sign-in/otp` page).
- `TENXYTE_WEBAUTHN_ENABLED` — off by default gates every `/webauthn/*` call with a
  `WEBAUTHN_DISABLED` error at the service-call level (the router itself is always registered).

`TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED` is also turned on — unlike the previous
version of this backend, this is now real and API-observable (`routers/auth.py`'s
`resolve_forced_password_change_scope` is fully implemented), so the `must_change_password`
fixture below is testable, not a broken promise.

## What's seeded

Two seeding strategies, kept deliberately apart in `seed_and_serve.py` — see its own docstring for
the full reasoning:

- **Most fixtures are created by calling the real running API** as an admin/member user would
  (organizations, RBAC role + permission, application, AI agent token, the GDPR deletion request)
  — this can't silently drift from the contract it's supposed to represent, because it *is* a real
  client exercising that contract.
- **A handful have no API-reachable creation path yet** (verified by grepping every router, not
  assumed) and are inserted directly via SQLAlchemy: 2FA enrollment (no FastAPI route enrolls TOTP
  yet), audit logs, login attempts, a blacklisted token, a refresh token, and a syntactically-valid
  but never-actually-registered WebAuthn credential (so `account/passkeys` has something to list —
  the register/authenticate *ceremony* itself still needs a real or CDP-virtual authenticator,
  which this backend doesn't provide).

| Fixture | Email | Password | Notes |
|---|---|---|---|
| Verified user | `e2e@example.com` | `Correct-Horse-Battery-1!` | Active, email-verified, no 2FA — the golden path for `SignIn`. Also owns the seeded audit log, login attempts, blacklisted token, refresh token, and WebAuthn credential rows. |
| Admin | `e2e-admin@example.com` | `Correct-Horse-Battery-2!` | `is_staff`/`is_superuser` — bypasses every `require_permission(...)` RBAC check (`rbac_service.has_permission_async`'s superuser short-circuit), so this one account can exercise every admin page without a role/permission graph being built for it specifically. **Has 2FA enabled from creation** (see below) — an `is_staff`/`is_superuser` account with no 2FA configured gets a 15-minute `2fa_setup_only` *restricted* token instead of a full-scope one on login (`routers/auth.py`'s admin bootstrap path), found by actually logging in as this fixture and getting `INSUFFICIENT_SCOPE` back, not by reading the code first. |
| Member | `e2e-member@example.com` | `Correct-Horse-Battery-3!` | Standard user — the target of the RBAC/organization fixtures below (holds the seeded role, is a member of the seeded organization, owns the seeded AI agent token and GDPR deletion request). |
| 2FA-enabled user | `e2e-2fa@example.com` | `Correct-Horse-Battery-4!` | `mfa_type=TOTP`. `TENXYTE_TOTP_ENCRYPTION_KEY` is unset for this fixture backend, so the printed `totp_secret` is genuine plaintext base32 — `pyotp.TOTP(secret).now()` in a test produces a real, currently-valid code against it. |
| `must_change_password` user | `e2e-mustchange@example.com` | `Correct-Horse-Battery-5!` | Logging in returns a `password_change_only`-scoped token and `must_change_password: true` — real now (see the feature flag note above), not the broken-promise fixture this README used to describe. |
| Organization | slug `acme-e2e` | — | Created by the admin (who becomes its `owner` automatically — `org_service.py` auto-creates/reuses the `owner` `OrganizationRoleDB` row the first time any organization is created). The member user is added to it with role `member`. |
| Organization roles | codes `owner`, `member`, `admin` | — | `owner` is auto-created by the org-creation call above; `member`/`admin` are seeded directly — **no route creates an `OrganizationRoleDB` row** (`GET /org-roles/` is the only registered endpoint; `POST /organizations/members/add/` 400s with `"Role member not found"` otherwise, found by calling it, not assumed). |
| RBAC role + permission | role `e2e-viewer`, permission `e2e.fixture.read` | — | Created via `POST /permissions/` then `POST /roles/`, then assigned to the member user via `POST /users/{id}/roles/` — so `/rbac/roles`, `/rbac/permissions`, and `/rbac/users/:id` all have real, non-empty data to render. |
| Application | name `E2E Fixture App` | — | Created via `POST /applications/`. |
| AI agent token | agent_id `e2e-agent` | — | Created via `POST /ai/tokens/` **as the admin**, not the member: `airs_service.py` only lets an `is_superuser` account delegate permissions to an Agent Token (`if not triggered_by.is_superuser: raise ...`) — this is enforced regardless of what the creating user's own RBAC roles grant them, found by getting `PERMISSION_DENIED` as the member despite the member actually holding the delegated permission via RBAC. Matches a real deployment anyway: an admin provisioning agent tokens for automation is the realistic case. |
| GDPR deletion request | for the member user | — | Requested via `POST /request-account-deletion/` as the member, so `/admin/gdpr` has a real pending row. |

**Known contract-shape finding, not yet acted on** (found verifying the seed against this backend,
out of scope for `seed_and_serve.py` itself to fix): `GET /roles/` and `GET /permissions/` return
a **paginated envelope** (`{count, page, page_size, ..., results: [...]}`) on this FastAPI port,
but the JS SDK's `RbacModule.listRoles()`/`listPermissions()` type them as a bare `Role[]`/
`Permission[]` array (`packages/core/src/modules/rbac.ts`, `tenxyte-js` repo) — matching
`GET /org-roles/`, `GET /ai/tokens/`, and `GET /webauthn/credentials/`'s `.credentials`, which
*are* bare arrays/objects on this same adapter. Whether the JS SDK's type is wrong or this
adapter's pagination here is the drift from the real (Django) Wire_Contract needs resolving before
`tenxyte-js`'s `/rbac/roles`/`/rbac/permissions` pages are wired against this backend for real
(specs/02-console-runtime, tâche 5.4) — both pages currently assume a bare array.

Application-level auth (`X-Access-Key`/`X-Access-Secret`) is **disabled**
(`TENXYTE_APPLICATION_AUTH_ENABLED=false`) — the same convention this repo's own FastAPI test
suite uses throughout, so requests need no extra headers.

The database is a fresh SQLite file, deleted and recreated on every container start — every
`docker compose up` gives E2E tests the exact same starting state, and every seeding call in
`_seed_via_api()`/`_seed_via_sql()` is idempotent (a 409/already-exists response is treated as
success, not a failure) so a re-seed on an already-seeded volume never errors either.

## Extending the seed

Still missing, documented honestly rather than silently left out:

- **A real WebAuthn registration/authentication ceremony** — the seeded credential row lets
  `account/passkeys` render a non-empty list, but registering or authenticating with it for real
  needs a browser-level (or Playwright CDP virtual) authenticator this backend doesn't simulate.
- **A HITL (Human-In-The-Loop) pending action exercised through a real request** —
  `AgentPendingActionDB` rows are currently only reachable by direct SQL insertion; no endpoint in
  this repo's current route surface triggers `airs_clearance.py`'s `human_in_the_loop_required`
  path to create one for real.
- **Social login** (`social.exchange`/`social.callback`) — needs a real or stubbed OAuth provider
  round-trip, out of scope for a deterministic, offline fixture backend.

Add fixtures to `_seed_via_sql()`/`_seed_via_api()` in [`seed_and_serve.py`](seed_and_serve.py) as
each corresponding `tenxyte-js` page/flow's E2E test is being written, rather than guessing their
shape ahead of time — every fixture currently in the seed was added and verified this way (see the
inline comments on each for what broke on the first attempt and why).

## Relationship to `openapi/`

This backend's actual behavior is the Wire_Contract's ground truth for the FastAPI adapter
specifically; [`openapi/tenxyte-fastapi.json`](../../openapi/tenxyte-fastapi.json) (see
[`scripts/export_openapi.py`](../../scripts/export_openapi.py)) is its versioned, static
description. The `tenxyte-js` SDK aligns against [`openapi/tenxyte-django.json`](../../openapi/tenxyte-django.json)
instead (the Django adapter's export) — the two adapters are meant to implement the same
Wire_Contract, but the pagination finding above shows they can still drift from each other in
practice. If a JS test here observes something `tenxyte-fastapi.json` doesn't reflect, the export
is what's out of date — file that against `openapi_drift_exceptions.toml`, don't route around it.
If it observes something that disagrees with `tenxyte-django.json` instead, that's an
adapter-parity gap, not an export staleness issue — file it separately.
