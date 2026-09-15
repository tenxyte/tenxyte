# FastAPI Quickstart

Get a first authenticated API call working against Tenxyte's FastAPI adapter in about five
minutes, using the built-in **App_Factory** — no manual service wiring required.

## Table of Contents

- [1. Install](#1-install)
- [2. Create the app](#2-create-the-app)
- [3. Run it](#3-run-it)
- [4. Create an application (API credentials)](#4-create-an-application-api-credentials)
- [5. Your first API call](#5-your-first-api-call)
- [Next steps](#next-steps)
- [Production considerations](#production-considerations)

---

## 1. Install

```bash
pip install "tenxyte[fastapi]"
```

This pulls in FastAPI, uvicorn, SQLAlchemy 2.0 (async), aiosqlite (the default development
database driver), Alembic, and httpx — everything the adapter needs. Django is **not** installed;
the two adapters are entirely independent (`pip freeze | grep -i django` stays empty).

Available extras:
- `[fastapi]` — everything above.
- `[webauthn]` — add on top for Passkeys/FIDO2 support (`webauthn/*` endpoints).
- `[postgres]` / `[mysql]` — if you're not using the default SQLite development driver, install
  the async driver for your database yourself (e.g. `asyncpg` for Postgres) — not a hard
  dependency of `[fastapi]`, since it varies by deployment.

## 2. Create the app

```python
# main.py
from tenxyte.adapters.fastapi.app import create_tenxyte_app

app = create_tenxyte_app()
```

That's it — `create_tenxyte_app()` returns a fully wired, runnable `FastAPI` app: every endpoint
across every ported Parity_Group (registration, login, password reset, OTP, 2FA, magic links,
passkeys, social login, RBAC, applications, organizations, GDPR, AIRS agent delegation, admin
routes), backed by a real SQLAlchemy async ORM layer (the **Reference_Stack**) whose tables are
created automatically on startup — no `NotImplementedError` anywhere, no dependency you have to
supply yourself first.

Settings are read from `TENXYTE_*` environment variables by default (via `EnvSettingsProvider`
— see [Settings Reference](settings.md) for the full `Adapter_Custom > OS env > .env > preset >
default` priority both adapters share). The one setting you must provide is the JWT signing
secret. A `.env` file in this directory is the easiest way — it's loaded automatically, no flag
needed:

```bash
# .env
TENXYTE_JWT_SECRET_KEY=change-me-to-a-real-secret-at-least-32-characters-long
```

A real OS environment variable works too (and always wins over `.env` if both are set), but only
for the shell session it was set in — reopening a terminal loses it, which is the most common
reason a "working" setup suddenly complains the secret is missing again:

```bash
export TENXYTE_JWT_SECRET_KEY="change-me-to-a-real-secret-at-least-32-characters-long"
# PowerShell: $env:TENXYTE_JWT_SECRET_KEY = "..."
```

## 3. Run it

```bash
uvicorn main:app --reload
```

Interactive API docs (Swagger UI) are at `http://localhost:8000/api/v1/docs/` — under the same
API prefix as every other endpoint, not FastAPI's own root-level `/docs` default, so it's exempt
from application-level authentication (step 4) the same way Django's own docs convention is.

## 4. Create an application (API credentials)

Application-level authentication (`X-Access-Key`/`X-Access-Secret`) is **on by default**
(`TENXYTE_APPLICATION_AUTH_ENABLED=true`), matching the Django adapter's own default — every
request to a non-exempt path needs these two headers. Create one application once, up front:

```python
# create_application.py — run this once against your running app's database
import asyncio

from tenxyte.adapters.fastapi import db
from tenxyte.adapters.fastapi.application_auth import create_application


async def main():
    engine = db.create_engine()  # same default SQLite file main.py's app just created
    session_factory = db.create_session_factory(engine)
    async with session_factory() as session:
        app, raw_secret = await create_application(session, name="My App")
        print(f"X-Access-Key: {app.access_key}")
        print(f"X-Access-Secret: {raw_secret}")  # shown once — store it now
    await engine.dispose()


asyncio.run(main())
```

```bash
python create_application.py
```

Run this *after* `uvicorn` has started at least once (so the database tables exist). For local
development only, you can skip this step entirely by setting
`TENXYTE_APPLICATION_AUTH_ENABLED=false` instead — every test fixture in this repo's own test
suite does exactly that. Keep it enabled if you want to exercise the real, default request shape.

## 5. Your first API call

```bash
export ACCESS_KEY="<X-Access-Key from step 4>"
export ACCESS_SECRET="<X-Access-Secret from step 4>"

# Register
curl -X POST http://localhost:8000/api/v1/register/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: $ACCESS_KEY" \
  -H "X-Access-Secret: $ACCESS_SECRET" \
  -d '{"email": "you@example.com", "password": "Correct-Horse-Battery-1!"}'

# Log in
curl -X POST http://localhost:8000/api/v1/login/email/ \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: $ACCESS_KEY" \
  -H "X-Access-Secret: $ACCESS_SECRET" \
  -d '{"email": "you@example.com", "password": "Correct-Horse-Battery-1!"}'
# -> {"access_token": "...", "refresh_token": "...", "user": {...}, ...}

# Call an authenticated endpoint
curl http://localhost:8000/api/v1/me/ \
  -H "X-Access-Key: $ACCESS_KEY" \
  -H "X-Access-Secret: $ACCESS_SECRET" \
  -H "Authorization: Bearer <access_token from login>"
```

Every error response — a wrong password, a missing field, an expired token — comes back in the
same canonical shape as the Django adapter:

```json
{ "error": "Invalid email or password", "code": "LOGIN_FAILED" }
```

That's the full loop: install, create the app, run it, get a real access token, call a protected
endpoint. Everything else — 2FA, magic links, passkeys, social login, organizations, RBAC, GDPR,
AIRS agent delegation — is the same `create_tenxyte_app()`, already wired; see the
[parity table](parity_table.md) for the complete endpoint list.

## Next steps

- [Async Guide](async_guide.md) — the `Async_Ports` pattern and how Core services resolve
  sync vs. async automatically.
- [Settings Reference](settings.md) — every `TENXYTE_*` environment variable.
- [Architecture](architecture.md) — Ports and Adapters, and how the Reference_Stack fits in.
- [Custom Adapters](custom_adapters.md) — swap the Reference_Stack's pieces (cache, email, task
  queue) for your own infrastructure.
- [Parity Table](parity_table.md) — every endpoint, both adapters, regenerated by CI.

## Production considerations

`create_tenxyte_app()`'s defaults are aimed at getting you running immediately, not at a
production deployment as-is:

- **Migrations, not auto-created tables**: pass `auto_create_schema=False` and apply the Alembic
  migrations under `migrations/` as part of your own deploy process instead of relying on
  ORM-metadata table creation.
- **A real cache/blacklist backend**: the default `InMemoryCacheService`/
  `InMemoryTokenBlacklistService` don't share state across multiple processes or instances. Build
  a Redis-backed adapter (see [Custom Adapters](custom_adapters.md)) for anything beyond a single
  process.
- **A real email backend**: `ConsoleEmailService` prints instead of sending — magic links, OTP
  codes, and password resets need a real provider wired in before going live.
- **An asymmetric JWT algorithm**: the default `HS256` (symmetric) shares one secret between
  every service that needs to verify a token. Switch to `RS256`/`PS256`/`EdDSA`
  (`TENXYTE_JWT_ALGORITHM`) if more than one service ever needs to verify tokens it didn't issue.
- **CORS**, if the API is called from a browser on a different origin:

  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://yourdomain.com"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

Both adapters share the same Core services underneath — the authentication logic itself is
portable between them; only the App_Factory/wiring layer differs.
