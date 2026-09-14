"""
Stands up the ephemeral FastAPI Tenxyte instance the AIRS Conformance Suite runs against in CI
(spec z_aud_2 task 4.4, spec z_aud_3 task 9.2) — the FastAPI mirror of
`tenxyte_ci/seed_and_serve.py`. Creates a fresh sqlite file, seeds one superuser + one application,
mints a JWT for that user directly (see below for why, instead of logging in over HTTP like the
Django script does), starts a real uvicorn server with the demo probe endpoints
(`tenxyte_ci_fastapi/demo_views.py`) mounted alongside the normal app, and prints a JSON line of
connection info to stdout once the server is actually accepting connections.

**Seeds a superuser, not a permission-holding regular user.** Django's script grants
`conformance.test` (and friends) directly to a normal user via RBAC. The Reference_Stack has no
RBAC tables yet (Group D) — `airs_service.create_async` only allows a `user.is_superuser` caller
to grant ANY permission to an Agent Token (see that module's docstring) — so the seeded user here
must be a superuser for `issue_token()` to succeed at all. This doesn't weaken what the
Conformance Suite actually proves: Double Validation itself (does the *token* carry the requested
permission) is exercised identically regardless of why the human was allowed to grant it in the
first place.

**JWT minted directly, not via `/login/email/`.** A superuser with no 2FA configured gets the
`2fa_setup_only` bootstrap token on a real login (see `routers/auth.py`'s `_login()`) — not a
full-scope token, which is what the suite's `human_client` fixture needs. Since this script
constructs the app in-process anyway, minting directly with the same `JWTService`
config the running app will itself validate against is both simpler and correct.

**No `--airs-other-permission` seeding needed** (unlike Django): the Reference_Stack has no
permission catalog to pre-create rows in — any string is accepted as a permission at issuance
time, gated only by the superuser check above.

**No `revoke_delegating_user_permission` hook is provided** (see `revoke_permission_hook.py`'s
Django-only counterpart) — `test_user_lost_permission_rejected` in the suite skips cleanly for
this target, exactly as designed (see `conftest.py`'s docstring for that fixture's contract).

Usage:
    python -m spec.airs.conformance.tenxyte_ci_fastapi.seed_and_serve [--port 8812]

Prints exactly one JSON line to stdout once ready, e.g.:
    {"base_url": "http://127.0.0.1:8812", "user_jwt": "eyJ...",
     "airs_test_permission": "conformance.test",
     "airs_discovery_path": "/api/v1/ai/.well-known/airs/",
     "conformance_probe_path": "http://127.0.0.1:8812/api/v1/ai/_conformance_probe/",
     "hitl_probe_path": "http://127.0.0.1:8812/api/v1/ai/_hitl_probe/"}
`base_url` is deliberately a bare origin (no path) — see the comment where it's built, just
before the JSON is printed, for why a path-carrying base_url breaks httpx's URL joining here.
Then serves until killed (SIGINT/SIGTERM/Ctrl+C).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import threading
import time
import uuid

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
SRC_ROOT = os.path.join(REPO_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

USER_EMAIL = "airs-conformance-fastapi@example.com"
USER_PASSWORD = "Conformance-Suite-P4ssw0rd!"
TEST_PERMISSION = "conformance.test"


def _build_settings():
    from tenxyte.core.env_provider import EnvSettingsProvider
    from tenxyte.core.settings import Settings

    class _Provider(EnvSettingsProvider):
        def get(self, name, default=None):
            overrides = {
                "TENXYTE_APPLICATION_AUTH_ENABLED": False,
                "TENXYTE_JWT_SECRET_KEY": "conformance-ephemeral-jwt-secret-not-for-production",
                "TENXYTE_AIRS_ENABLED": True,
                "TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED": True,
                "TENXYTE_AIRS_BUDGET_TRACKING_ENABLED": True,
            }
            if name in overrides:
                return overrides[name]
            return super().get(name, default)

    return Settings(provider=_Provider())


async def _seed(database_url: str) -> str:
    """Creates the schema and one superuser + application. Returns the user's id."""
    import bcrypt

    from tenxyte.adapters.fastapi import db as db_module
    from tenxyte.adapters.fastapi.models_sa import ApplicationDB
    from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
    from tenxyte.ports.repositories import User

    engine = db_module.create_engine(database_url)
    await db_module.create_all_tables(engine)
    session_factory = db_module.create_session_factory(engine)

    password_hash = bcrypt.hashpw(USER_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    async with session_factory() as session:
        session.add(
            ApplicationDB(name="AIRS Conformance Demo (FastAPI)", access_key=str(uuid.uuid4()), access_secret="unused")
        )
        repo = SQLAlchemyAsyncUserRepository(session)
        user = await repo.create(
            User(id=str(uuid.uuid4()), email=USER_EMAIL, password_hash=password_hash, is_active=True, is_superuser=True)
        )
        await session.commit()

    await engine.dispose()
    return user.id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8812)
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address. Use 0.0.0.0 to accept connections from other containers."
    )
    parser.add_argument("--db-path", default=None)
    args = parser.parse_args()

    db_path = args.db_path or os.path.join(os.path.dirname(__file__), "_ephemeral.sqlite3")
    if os.path.exists(db_path):
        os.remove(db_path)
    database_url = f"sqlite+aiosqlite:///{db_path}"

    settings = _build_settings()
    user_id = asyncio.run(_seed(database_url))

    from tenxyte.adapters.fastapi.app import create_tenxyte_app
    from tenxyte.core.jwt_service import InMemoryTokenBlacklistService, JWTService

    app = create_tenxyte_app(settings=settings, database_url=database_url, auto_create_schema=False)

    from spec.airs.conformance.tenxyte_ci_fastapi.demo_views import router as demo_router

    app.include_router(demo_router, prefix=settings.api_prefix)

    # The running app's own JWTService is only constructed inside its lifespan, which hasn't
    # started yet — mint with a throwaway instance using the identical settings (same secret,
    # algorithm, lifetime) it will itself validate against once serving starts.
    jwt_service = JWTService(settings=settings, blacklist_service=InMemoryTokenBlacklistService())
    access_token = jwt_service.generate_new_token_pair(user_id=user_id, application_id="default").access_token

    import uvicorn

    config = uvicorn.Config(app, host=args.host, port=args.port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 30
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        print(json.dumps({"error": "FastAPI conformance server failed to start within 30s"}), file=sys.stderr)
        sys.exit(1)

    # Bare origin, no path — matching the Django CI invocation's own `--airs-base-url` convention
    # (e.g. "http://127.0.0.1:8811", not "http://127.0.0.1:8811/api/v1/auth"). httpx.Client's
    # base_url + an absolute-path request URL *appends* rather than replaces when base_url already
    # carries a path, so a prefixed base_url here would double up with `settings.api_prefix`
    # baked into every discovered endpoint path (`_endpoint_map()` in routers/airs.py).
    origin = f"http://127.0.0.1:{args.port}"
    info = {
        "base_url": origin,
        "user_jwt": access_token,
        "airs_test_permission": TEST_PERMISSION,
        "airs_discovery_path": f"{settings.api_prefix}/ai/.well-known/airs/",
        "conformance_probe_path": f"{origin}{settings.api_prefix}/ai/_conformance_probe/",
        "hitl_probe_path": f"{origin}{settings.api_prefix}/ai/_hitl_probe/",
    }
    print(json.dumps(info), flush=True)

    try:
        thread.join()
    except KeyboardInterrupt:
        server.should_exit = True
        thread.join()


if __name__ == "__main__":
    main()
