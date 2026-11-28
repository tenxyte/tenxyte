"""
Cross-adapter Database Parity tests: Django <-> FastAPI on the exact same database.

Proves that:
1. Django migrations and FastAPI SQLAlchemy `Base.metadata` produce the exact same set of
   25 `tenxyte_*` tables with identical column names.
2. A deployment can switch from Django to FastAPI on the exact same SQLite database file
   (with `auto_create_schema=False`) and preserve:
   - Applications (`X-Access-Key` / `X-Access-Secret`)
   - Users & passwords (canonical SHA-256 + bcrypt hash)
   - TOTP 2FA secrets (Fernet-encrypted) and `is_2fa_enabled`
   - RBAC roles & hierarchical permissions (`tenxyte_users_roles`, `tenxyte_roles_permissions`)
   - Organizations & memberships
   - Active refresh tokens (`tenxyte_refresh_tokens`)
   - Blacklisted JWTs (`tenxyte_blacklisted_tokens`)
   - AIRS Agent Tokens & granted permissions (`tenxyte_agent_tokens_granted_permissions`)
3. A user registered and logged out via FastAPI can immediately be queried, authenticated
   (`user.check_password`), refreshed (`RefreshToken.get_by_raw_token`), and checked against
   the JWT blacklist (`BlacklistedToken.is_blacklisted`) from Django on the same database.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyotp
import pytest
from asgiref.sync import sync_to_async
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.models_sa import AgentTokenDB, AuditLogDB, Base
from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings, SettingsProvider


class _DictSettingsProvider(SettingsProvider):
    def __init__(self, values: dict):
        self._values = values

    def get(self, name: str, default=None):
        if name in self._values:
            return self._values[name]
        short = name.removeprefix("TENXYTE_")
        return self._values.get(short, default)


def _sqlite_schema(db_path: Path) -> dict[str, set[str]]:
    con = sqlite3.connect(db_path)
    try:
        tables = [
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'tenxyte_%' ORDER BY name"
            ).fetchall()
        ]
        schema: dict[str, set[str]] = {}
        for table in tables:
            cols = {row[1] for row in con.execute(f'PRAGMA table_info("{table}")').fetchall()}
            schema[table] = cols
        return schema
    finally:
        con.close()


@pytest.mark.django_db
def test_schema_table_and_column_parity(tmp_path: Path):
    """Django's migrated schema and FastAPI's SQLAlchemy metadata must have identical
    `tenxyte_*` table names and identical column sets on every single table."""
    from django.db import connection

    # 1. Introspect Django's active SQLite schema
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'tenxyte_%' ORDER BY name"
        )
        django_tables = [row[0] for row in cursor.fetchall()]
        django_schema: dict[str, set[str]] = {}
        for table in django_tables:
            cursor.execute(f'PRAGMA table_info("{table}")')
            django_schema[table] = {row[1] for row in cursor.fetchall()}

    # 2. Create a fresh SQLite DB via FastAPI's SQLAlchemy Base.metadata
    sa_db = tmp_path / "sa_schema.sqlite3"
    sa_engine = create_engine(f"sqlite:///{sa_db}")
    Base.metadata.create_all(sa_engine)
    sa_engine.dispose()
    sa_schema = _sqlite_schema(sa_db)

    assert set(sa_schema.keys()) == set(django_schema.keys()), (
        f"Table mismatch:\n"
        f"  Only in Django:  {sorted(set(django_schema) - set(sa_schema))}\n"
        f"  Only in FastAPI: {sorted(set(sa_schema) - set(django_schema))}"
    )

    for table in sorted(django_schema):
        assert sa_schema[table] == django_schema[table], (
            f"Column mismatch on table '{table}':\n"
            f"  Only in Django:  {sorted(django_schema[table] - sa_schema[table])}\n"
            f"  Only in FastAPI: {sorted(sa_schema[table] - django_schema[table])}"
        )


@pytest.mark.anyio
async def test_django_fastapi_bidirectional_shared_database_switch(tmp_path: Path, django_db_blocker):
    """End-to-end bidirectional test on a single shared SQLite file:
    - Phase 1: Seed data via Django ORM (App, User + password + Fernet TOTP, RBAC, Org,
      RefreshToken, BlacklistedToken, AIRS AgentToken).
    - Phase 2: Boot FastAPI (`auto_create_schema=False`) against the exact same SQLite file
      and exercise login + 2FA, /me/ (RBAC), /refresh/, blacklist rejection, /organizations/,
      and AIRS heartbeat + trace persistence.
    - Phase 3: Register & logout a brand-new user via FastAPI, then verify password, refresh
      token, and blacklisted JWT back from Django ORM on the same file.
    """
    from django.conf import settings as dj_settings
    from django.core.management import call_command
    from django.db import connections

    shared_db = tmp_path / "shared_tenxyte.sqlite3"
    shared_secret = "shared-django-fastapi-jwt-secret-key-at-least-32-bytes"
    shared_fernet_key = Fernet.generate_key().decode("utf-8")

    # Configure a dedicated Django DB alias pointing to `shared_db`
    alias = "shared_parity_db"
    dj_settings.DATABASES[alias] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(shared_db),
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "OPTIONS": {},
        "TIME_ZONE": None,
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }

    raw_totp_secret = pyotp.random_base32()
    encrypted_totp = Fernet(shared_fernet_key.encode("utf-8")).encrypt(raw_totp_secret.encode("utf-8")).decode("utf-8")
    user_password = "SharedSwitchPassword123!"
    raw_agent_token = "Ag3ntT0k3nSharedDbParity1234567890abcdefghijklm"

    def _seed_via_django() -> dict:
        import hashlib
        import secrets

        from tenxyte.models import (
            AgentToken,
            Application,
            BlacklistedToken,
            Organization,
            OrganizationMembership,
            OrganizationRole,
            Permission,
            RefreshToken,
            Role,
            User,
        )

        with django_db_blocker.unblock():
            call_command("migrate", database=alias, verbosity=0)

            # 1. Application
            raw_app_secret = secrets.token_hex(32)
            app_obj = Application(
                name="Shared App",
                description="Created in Django",
                access_key=secrets.token_hex(32),
                access_secret=Application._hash_secret(raw_app_secret),
                allowed_origins=[],
            )
            app_obj.save(using=alias)

            # 2. User + password + Fernet-encrypted TOTP 2FA
            user = User(
                email="alice.shared@example.com",
                first_name="Alice",
                last_name="Shared",
                is_active=True,
                is_email_verified=True,
                is_superuser=True,
                is_2fa_enabled=True,
                totp_secret=encrypted_totp,
            )
            user.set_password(user_password)
            user.save(using=alias)

            # 3. RBAC Role & Permission
            perm = Permission(code="reports.read", name="Read Reports", description="")
            perm.save(using=alias)
            role = Role(code="analyst", name="Analyst", description="")
            role.save(using=alias)
            role.permissions.db_manager(alias)
            # Assign M2M using the alias
            Role.permissions.through.objects.using(alias).create(role_id=role.id, permission_id=perm.id)
            User.roles.through.objects.using(alias).create(user_id=user.id, role_id=role.id)

            # 4. Organization & Membership
            org_role = OrganizationRole(
                code="owner", name="Owner", is_system=True, permissions=["org.*"]
            )
            org_role.save(using=alias)
            org = Organization(name="Shared Corp", slug="shared-corp", created_by=user)
            org.save(using=alias)
            membership = OrganizationMembership(user=user, organization=org, role=org_role, status="active")
            membership.save(using=alias)

            # 5. RefreshToken
            raw_refresh = secrets.token_urlsafe(64)
            rt = RefreshToken(
                user=user,
                application=app_obj,
                token=RefreshToken._hash_token(raw_refresh),
                device_info="django-device",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            rt.save(using=alias)

            # 6. BlacklistedToken (pre-blacklisted JWT)
            jwt_svc = JWTService(
                settings=Settings(
                    provider=_DictSettingsProvider(
                        {
                            "JWT_SECRET_KEY": shared_secret,
                            "JWT_ALGORITHM": "HS256",
                        }
                    )
                )
            )
            revoked_access, revoked_jti, revoked_exp = jwt_svc.generate_access_token(
                user_id=str(user.id), application_id=str(app_obj.id)
            )
            bl = BlacklistedToken(
                token_jti=revoked_jti,
                user=user,
                expires_at=revoked_exp,
                reason="django_logout",
            )
            bl.save(using=alias)

            # 7. AIRS AgentToken + granted_permissions M2M
            agent_token = AgentToken(
                token=hashlib.sha256(raw_agent_token.encode("utf-8")).hexdigest(),
                agent_id="django-issued-agent",
                triggered_by=user,
                application=app_obj,
                organization=org,
                status="ACTIVE",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            agent_token.save(using=alias)
            AgentToken.granted_permissions.through.objects.using(alias).create(
                agenttoken_id=agent_token.id, permission_id=perm.id
            )

            connections[alias].close()
            return {
                "app_id": str(app_obj.id),
                "access_key": app_obj.access_key,
                "access_secret": raw_app_secret,
                "user_id": str(user.id),
                "raw_refresh": raw_refresh,
                "revoked_access": revoked_access,
                "agent_token_id": str(agent_token.id),
                "org_slug": org.slug,
            }

    try:
        seeded = await sync_to_async(_seed_via_django, thread_sensitive=True)()

        # --- Phase 2: Boot FastAPI against the EXACT SAME SQLite file (auto_create_schema=False) ---
        fa_settings = Settings(
            provider=_DictSettingsProvider(
                {
                    "JWT_SECRET_KEY": shared_secret,
                    "JWT_ALGORITHM": "HS256",
                    "TOTP_ENCRYPTION_KEY": shared_fernet_key,
                    "APPLICATION_AUTH_ENABLED": True,
                    "ORGANIZATIONS_ENABLED": True,
                    "AIRS_ENABLED": True,
                    "BREACH_CHECK_ENABLED": False,
                    "RATE_LIMITING_ENABLED": False,
                }
            )
        )
        app = create_tenxyte_app(
            settings=fa_settings,
            database_url=f"sqlite+aiosqlite:///{shared_db.as_posix()}",
            auto_create_schema=False,
        )
        app_headers = {
            "X-Access-Key": seeded["access_key"],
            "X-Access-Secret": seeded["access_secret"],
        }

        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
                # 2a. Login with Django password + live TOTP code decrypted with shared Fernet key
                totp_code = pyotp.TOTP(raw_totp_secret).now()
                login_res = await client.post(
                    "/api/v1/login/email/",
                    headers=app_headers,
                    json={
                        "email": "alice.shared@example.com",
                        "password": user_password,
                        "totp_code": totp_code,
                    },
                )
                assert login_res.status_code == 200, login_res.text
                login_body = login_res.json()
                assert login_body["user"]["id"] == seeded["user_id"]
                assert login_body["user"]["is_email_verified"] is True
                assert login_body["user"]["is_2fa_enabled"] is True

                auth_headers = {**app_headers, "Authorization": f"Bearer {login_body['access_token']}"}

                # 2b. Verify RBAC roles & permissions read from Django's M2M tables
                me_res = await client.get("/api/v1/me/", headers=auth_headers)
                assert me_res.status_code == 200, me_res.text
                me_body = me_res.json()
                assert me_body["id"] == seeded["user_id"]
                assert "analyst" in me_body["roles"]
                assert "reports.read" in me_body["permissions"]

                # 2c. Redeem the Django-created RefreshToken on FastAPI
                refresh_res = await client.post(
                    "/api/v1/refresh/",
                    headers=app_headers,
                    json={"refresh_token": seeded["raw_refresh"]},
                )
                assert refresh_res.status_code == 200, refresh_res.text
                assert "access_token" in refresh_res.json()

                # 2d. Verify Django-blacklisted JWT is rejected by FastAPI
                bl_res = await client.get(
                    "/api/v1/me/",
                    headers={**app_headers, "Authorization": f"Bearer {seeded['revoked_access']}"},
                )
                assert bl_res.status_code == 401
                assert bl_res.json()["code"] == "TOKEN_INVALID"

                # 2e. Verify Django-created Organization is visible on FastAPI
                orgs_res = await client.get("/api/v1/organizations/list/", headers=auth_headers)
                assert orgs_res.status_code == 200, orgs_res.text
                org_slugs = [o["slug"] for o in orgs_res.json()["results"]]
                assert seeded["org_slug"] in org_slugs

                # 2f. Verify Django-created AIRS AgentToken + granted_permissions M2M + AuditLog trace
                trace_id = "trace-django-to-fastapi-001"
                hb_res = await client.post(
                    f"/api/v1/ai/tokens/{seeded['agent_token_id']}/heartbeat/",
                    headers={
                        **app_headers,
                        "Authorization": f"AgentBearer {raw_agent_token}",
                        "X-Prompt-Trace-ID": trace_id,
                    },
                )
                assert hb_res.status_code == 200, hb_res.text

                token_detail = await client.get(
                    f"/api/v1/ai/tokens/{seeded['agent_token_id']}/",
                    headers=auth_headers,
                )
                assert token_detail.status_code == 200, token_detail.text
                assert token_detail.json()["agent_id"] == "django-issued-agent"

                async with app.state.tenxyte_session_factory() as session:
                    agent_row = await session.get(AgentTokenDB, seeded["agent_token_id"])
                    assert agent_row is not None
                    assert agent_row.granted_permissions == ["reports.read"]

                    audit_row = (
                        await session.execute(select(AuditLogDB).where(AuditLogDB.prompt_trace_id == trace_id))
                    ).scalar_one_or_none()
                    assert audit_row is not None
                    assert audit_row.agent_token_id == seeded["agent_token_id"]

                # --- Phase 3: Write via FastAPI (register + login + logout) ---
                bob_password = "BobFastAPIPassword123!"
                reg_res = await client.post(
                    "/api/v1/register/",
                    headers=app_headers,
                    json={
                        "email": "bob.fastapi@example.com",
                        "password": bob_password,
                        "first_name": "Bob",
                        "last_name": "FastAPI",
                        "login": True,
                    },
                )
                assert reg_res.status_code == 201, reg_res.text
                reg_body = reg_res.json()
                bob_access = reg_body["access_token"]
                bob_refresh = reg_body["refresh_token"]

                # Logout Bob via FastAPI so his access token is persisted in tenxyte_blacklisted_tokens
                logout_res = await client.post(
                    "/api/v1/logout/",
                    headers={**app_headers, "Authorization": f"Bearer {bob_access}"},
                    json={"refresh_token": bob_refresh},
                )
                assert logout_res.status_code == 200, logout_res.text

                # Issue a second refresh token for Bob (still active) to verify Django can redeem it
                bob_login = await client.post(
                    "/api/v1/login/email/",
                    headers=app_headers,
                    json={"email": "bob.fastapi@example.com", "password": bob_password},
                )
                assert bob_login.status_code == 200, bob_login.text
                bob_active_refresh = bob_login.json()["refresh_token"]

                # Decode Bob's logged-out JTI
                decoded_bob = await app.state.tenxyte_jwt_service.decode_token_async(
                    bob_access, check_blacklist=False
                )
                bob_revoked_jti = decoded_bob.jti

        # --- Verify FastAPI-created data back in Django ORM on the exact same SQLite file ---
        def _verify_from_django():
            from tenxyte.models import AuditLog, BlacklistedToken, RefreshToken, User

            with django_db_blocker.unblock():
                bob = User.objects.using(alias).get(email="bob.fastapi@example.com")
                assert bob.check_password(bob_password) is True
                assert bob.first_name == "Bob"

                # Active FastAPI refresh token is found and valid in Django
                rt = RefreshToken.objects.using(alias).get(token=RefreshToken._hash_token(bob_active_refresh))
                assert rt.user_id == bob.id
                assert rt.is_revoked is False

                # Logged-out FastAPI refresh token is marked is_revoked=True in Django
                rt_revoked = RefreshToken.objects.using(alias).get(token=RefreshToken._hash_token(bob_refresh))
                assert rt_revoked.is_revoked is True

                # Logged-out FastAPI JWT is present in Django's BlacklistedToken table
                assert BlacklistedToken.objects.using(alias).filter(token_jti=bob_revoked_jti).exists() is True

                # FastAPI AIRS trace was persisted in Django's AuditLog table
                assert AuditLog.objects.using(alias).filter(prompt_trace_id=trace_id).exists() is True

                connections[alias].close()

        await sync_to_async(_verify_from_django, thread_sensitive=True)()
    finally:
        def _cleanup():
            if alias in connections.databases:
                connections[alias].close()
                del connections.databases[alias]
            dj_settings.DATABASES.pop(alias, None)

        await sync_to_async(_cleanup, thread_sensitive=True)()
