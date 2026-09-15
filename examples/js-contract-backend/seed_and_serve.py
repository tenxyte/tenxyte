"""
Contract_Fixtures — dockerized demo backend for the JS monorepo's E2E tests (spec z_aud_3,
Requirement 6.6, task 14.2): stands up a real, ephemeral FastAPI_Adapter instance, seeds exactly
the deterministic fixtures documented in `README.md`, serves real HTTP, and prints a JSON line of
connection info to stdout once ready — the same contract
`spec/airs/conformance/tenxyte_ci/seed_and_serve.py` already established for the AIRS Conformance
Suite / CrewAI example's own demo backend, adapted here from WSGI+Django to ASGI+FastAPI.

Usage:
    python seed_and_serve.py [--host 0.0.0.0] [--port 8000]

Prints exactly one JSON line to stdout once ready:
    {"base_url": "http://127.0.0.1:8000/api/v1",
     "seeded_user": {"email": "e2e@example.com", "password": "Correct-Horse-Battery-1!"},
     "seeded_user_jwt": "eyJ..."}
Then serves forever until killed (SIGINT/SIGTERM/Ctrl+C).

**Application-level auth is disabled** (`TENXYTE_APPLICATION_AUTH_ENABLED=False`) — the same
convention every test fixture in this repo's own FastAPI test suite already uses (no
`X-Access-Key`/`X-Access-Secret` needed on requests), so Playwright tests can call the API
directly without first provisioning an Application.

**The database is a fresh SQLite file per container start** (`auto_create_schema=True`, the
App_Factory's own default), deleted and recreated on every launch — every `docker compose up`
gives JS E2E tests a byte-identical starting state, deliberately: this is a Contract_Fixtures
backend for testing the Wire_Contract, not a persistence demo. A real file rather than
`:memory:` — `db.py`'s `create_engine` uses a plain connection pool with no `StaticPool`
override, so an in-memory SQLite database would be a *different*, empty database on every new
connection the pool opens (the same reason `tests/integration/fastapi/`'s own fixtures use a
shared-cache `file:...?mode=memory&cache=shared&uri=true` URI instead of bare `:memory:`) — a
plain file sidesteps that entirely and needs no special pooling configuration for a long-running,
many-concurrent-request server process.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SEEDED_USER_EMAIL = "e2e@example.com"
SEEDED_USER_PASSWORD = "Correct-Horse-Battery-1!"


async def _seed(session_factory) -> None:
    """Idempotent — `docker compose up` on an already-seeded volume (if one was kept around)
    must not error, matching `seed_and_serve.py`'s own Django precedent (`get_or_create`).

    Deliberately seeds only this one verified user for now — a `must_change_password: True`
    fixture was tried and dropped: `UserDB.must_change_password` is a real column, but
    `routers/auth.py`'s login handlers hardcode `"must_change_password": False` in every
    response (verified by actually calling `/login/email/` against a seeded row with the flag
    set, not just reading the code) — the feature is real in Django but gated off by default
    there too, and its FastAPI port is its own not-yet-executed spec
    (`specs/force_password_change_on_first_login/`). Seeding a fixture the API can't currently
    surface would be a broken promise to whoever writes the `ForcedPasswordChange` E2E test
    against this backend; add it back once that spec ships."""
    import bcrypt
    from sqlalchemy import select

    from tenxyte.adapters.fastapi.models_sa import UserDB

    async with session_factory() as session:
        existing = (await session.execute(select(UserDB).where(UserDB.email == SEEDED_USER_EMAIL))).scalar_one_or_none()
        if existing is None:
            session.add(
                UserDB(
                    id=str(uuid.uuid4()),
                    email=SEEDED_USER_EMAIL,
                    password_hash=bcrypt.hashpw(SEEDED_USER_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                    is_active=True,
                    email_verified=True,
                )
            )

        await session.commit()


async def _login(base_url: str, email: str, password: str) -> str:
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"{base_url}/login/email/", json={"email": email, "password": password})
        response.raise_for_status()
        return response.json()["access_token"]


async def _run(host: str, port: int) -> None:
    import uvicorn

    from tenxyte.adapters.fastapi.app import create_tenxyte_app
    from tenxyte.core.env_provider import EnvSettingsProvider
    from tenxyte.core.settings import Settings

    class _DemoBackendProvider(EnvSettingsProvider):
        """Reads real env vars first (so `docker-compose.yml`/an operator can override anything,
        e.g. `TENXYTE_JWT_SECRET_KEY` for a non-default deployment), with demo-appropriate
        defaults for the two settings a byte-identical, zero-config `docker compose up` needs."""

        def get(self, name, default=None):
            if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
                return super().get(name, False)
            if name == "TENXYTE_JWT_SECRET_KEY":
                return super().get(name, "js-contract-backend-demo-secret-key-not-for-production-use-only")
            return super().get(name, default)

    db_path = Path.cwd() / "js-contract-backend.db"
    db_path.unlink(missing_ok=True)

    settings = Settings(provider=_DemoBackendProvider())
    app = create_tenxyte_app(settings=settings, database_url=f"sqlite+aiosqlite:///{db_path}")

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())

    while not server.started:
        await asyncio.sleep(0.05)

    await _seed(app.state.tenxyte_session_factory)

    # The URL this process uses to call itself (for the login below) is always loopback,
    # regardless of which host interface it bound to for external connections — same convention
    # as seed_and_serve.py's Django precedent.
    base_url = f"http://127.0.0.1:{port}{settings.api_prefix}"
    seeded_user_jwt = await _login(base_url, SEEDED_USER_EMAIL, SEEDED_USER_PASSWORD)

    info = {
        "base_url": base_url,
        "seeded_user": {"email": SEEDED_USER_EMAIL, "password": SEEDED_USER_PASSWORD},
        "seeded_user_jwt": seeded_user_jwt,
    }
    print(json.dumps(info), flush=True)

    await serve_task


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1", help="Bind address. Use 0.0.0.0 for other containers.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    try:
        asyncio.run(_run(args.host, args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
