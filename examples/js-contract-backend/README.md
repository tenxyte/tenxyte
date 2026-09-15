# js-contract-backend

Contract_Fixtures dockerized demo backend for the `@tenxyte/ui-headless`/`@tenxyte/ui` monorepo's
Playwright E2E tests (spec `z_aud_3`, Requirement 6.6, task 14.2). A real FastAPI_Adapter
instance, real HTTP, real bcrypt password hashes — no mocks — seeded with a small set of
**deterministic** fixtures so E2E tests can rely on known credentials instead of provisioning
their own accounts through the UI on every run.

This is a test fixture backend, not a production deployment example — see
[`examples/deployment/`](../deployment/) for a hardened, Postgres/Redis-backed Dockerfile.

## Run it

```bash
docker compose -f examples/js-contract-backend/docker-compose.yml up --build
```

The server listens on `http://localhost:8000`, API prefix `/api/v1` (so, e.g.,
`http://localhost:8000/api/v1/login/email/`). On startup it prints one JSON line to stdout with
the connection info a CI orchestration script can parse:

```json
{
  "base_url": "http://127.0.0.1:8000/api/v1",
  "seeded_user": { "email": "e2e@example.com", "password": "Correct-Horse-Battery-1!" },
  "seeded_user_jwt": "eyJ..."
}
```

## What's seeded

| Fixture | Email | Password | Notes |
|---|---|---|---|
| Verified user | `e2e@example.com` | `Correct-Horse-Battery-1!` | Active, email-verified, no 2FA — the golden path for `SignIn`. `seeded_user_jwt` above is a real access token for this user, obtained by actually calling `POST /login/email/` at startup, for tests that want to skip the UI login step. |

Application-level auth (`X-Access-Key`/`X-Access-Secret`) is **disabled**
(`TENXYTE_APPLICATION_AUTH_ENABLED=false`) — the same convention this repo's own FastAPI test
suite uses throughout, so requests need no extra headers.

The database is a fresh SQLite file, deleted and recreated on every container start — every
`docker compose up` gives E2E tests the exact same starting state.

## Extending the seed

This intentionally seeds only one working fixture for now — the golden path for `SignIn`.
Every other component specced in `base.md` needs its own concrete fixture that either doesn't
exist yet on either side of the contract, or (like `ForcedPasswordChange`) isn't actually
reachable through the API yet even though the underlying data model supports it:

- **`ForcedPasswordChange`**: a `must_change_password: true` user was seeded and tried here, then
  removed — `UserDB.must_change_password` is a real column, but `routers/auth.py`'s login
  handlers hardcode `"must_change_password": False` in every response (verified by calling
  `/login/email/` against a seeded row with the flag set). The feature is gated off by default in
  Django too, and its FastAPI port is tracked as its own not-yet-executed spec,
  `specs/force_password_change_on_first_login/`. Re-add the fixture once that spec ships.
- **`TwoFactorSetup`**, **`PasskeyButton`**, **`OrgSwitcher`**: each needs its own concrete fixture
  (a TOTP secret, a registered credential, an organization + membership) that doesn't exist yet on
  either side of the contract.

Add fixtures to `_seed()` in [`seed_and_serve.py`](seed_and_serve.py) once the corresponding
`@tenxyte/ui-headless` component and its E2E test are being written, rather than guessing their
shape ahead of time.

## Relationship to `openapi/`

This backend's actual behavior is the Wire_Contract's ground truth; `openapi/tenxyte-fastapi.json`
(see [`scripts/export_openapi.py`](../../scripts/export_openapi.py)) is its versioned, static
description. If a JS test here observes something the OpenAPI export doesn't reflect, the export
is what's out of date — file that against `openapi_drift_exceptions.toml`, don't route around it.
