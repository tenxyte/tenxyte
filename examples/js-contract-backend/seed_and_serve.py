"""
Contract_Fixtures — dockerized demo backend for the tenxyte-js monorepo's E2E tests (spec
specs/02-console-runtime, tâche 5.1): stands up a real, ephemeral FastAPI_Adapter instance, seeds
a deterministic set of fixtures covering every one of the console's 38 pages, serves real HTTP,
and prints a JSON line of connection info to stdout once ready — the same contract
`spec/airs/conformance/tenxyte_ci/seed_and_serve.py` already established for the AIRS Conformance
Suite / CrewAI example's own demo backend, adapted here from WSGI+Django to ASGI+FastAPI.

Usage:
    python seed_and_serve.py [--host 0.0.0.0] [--port 8000]

Prints exactly one JSON line to stdout once ready (see `_run()` for the exact shape — every
fixture's credentials/ids the JS E2E harness needs, not reproduced in this docstring since it
would drift the moment a fixture is added). Then serves forever until killed (SIGINT/SIGTERM/
Ctrl+C).

**Application-level auth is disabled** (`TENXYTE_APPLICATION_AUTH_ENABLED=False`) — the same
convention every test fixture in this repo's own FastAPI test suite already uses (no
`X-Access-Key`/`X-Access-Secret` needed on requests), so Playwright tests can call the API
directly without first provisioning an Application.

**`TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED` is turned on** (unlike the previous
version of this script, which left it off): verified by reading `routers/auth.py` directly, not
assumed from an old README — `resolve_forced_password_change_scope` is fully implemented on this
adapter now (spec `force_password_change_on_first_login` shipped since this fixture backend was
last touched), so the `must_change_password` fixture below is real and testable, not a broken
promise.

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

**Two seeding strategies, deliberately kept apart** (see `_seed_via_sql()` vs `_seed_via_api()`):
most fixtures are created by calling the real running API (organizations, roles, permissions,
applications, agent tokens, the GDPR deletion request) — this is both simpler and a stronger
guarantee than hand-crafting rows, since it exercises the exact write path a real client would use
and can never silently drift from the contract it's supposed to represent. Only fixtures with no
API-reachable creation path yet (2FA enrollment, audit logs, login attempts, a blacklisted token,
a refresh token, an AIRS pending HITL action — none of these have a FastAPI route that creates
them, verified by grepping each router, not assumed) are inserted directly via SQLAlchemy.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

# INFO, pas WARNING (le défaut Python sans config) : `otp.py`/`login_otp.py`/`password.py` logguent
# le code OTP en clair via `logger.info("... code=%s ...")` — c'est la SEULE façon d'observer ces
# codes depuis l'extérieur (ils sont hachés en base, jamais renvoyés par l'API elle-même). Le
# harnais E2E JS (specs/02-console-runtime, tâche 6.2) capture tout ce stdout dans un fichier et
# l'y cherche — voir tests/e2e/mailbox.ts (repo tenxyte-js). Testé directement : uvicorn (configuré
# séparément en `log_level="warning"`, plus bas) ne réinitialise pas cette config globale.
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")

VERIFIED_USER_EMAIL = "e2e@example.com"
VERIFIED_USER_PASSWORD = "Correct-Horse-Battery-1!"

ADMIN_USER_EMAIL = "e2e-admin@example.com"
ADMIN_USER_PASSWORD = "Correct-Horse-Battery-2!"

MEMBER_USER_EMAIL = "e2e-member@example.com"
MEMBER_USER_PASSWORD = "Correct-Horse-Battery-3!"

MEMBER2_USER_EMAIL = "e2e-member2@example.com"
MEMBER2_USER_PASSWORD = "Correct-Horse-Battery-3b!"

TWOFA_USER_EMAIL = "e2e-2fa@example.com"
TWOFA_USER_PASSWORD = "Correct-Horse-Battery-4!"

MUST_CHANGE_USER_EMAIL = "e2e-mustchange@example.com"
MUST_CHANGE_USER_PASSWORD = "Correct-Horse-Battery-5!"

PHONE_USER_COUNTRY_CODE = "+33"
PHONE_USER_NUMBER = "600000001"
PHONE_USER_PASSWORD = "Correct-Horse-Battery-6!"

# password.setInitial (specs/02-console-runtime tâche 6.2) : le seul parcours réel vers un token
# restreint `password_change_only` SANS mot de passe utilisable passe par une connexion SMS OTP
# (login_otp.py applique `resolve_forced_password_change_scope` tout comme `/login/email/`, sans
# jamais vérifier de mot de passe) — `must_change_user` (email, avec hash) ne peut pas servir ici
# puisque `/password/set-initial/` exige `password_hash IS NULL`. `email` reste requis (colonne
# non-nullable) même si personne ne s'en sert pour se connecter.
MUST_CHANGE_PHONE_USER_EMAIL = "e2e-mustchange-phone@example.com"
MUST_CHANGE_PHONE_USER_COUNTRY_CODE = "+33"
MUST_CHANGE_PHONE_USER_NUMBER = "600000002"

# social.exchange / social.callback (specs/02-console-runtime tâche 6.2) : aucun vrai compte
# GitHub n'est utilisable en CI, donc `social_auth_service._test_transport` (le même point
# d'injection que `tests/integration/fastapi/unit/test_social_router.py`, un vrai
# `httpx.ASGITransport` vers une vraie appli ASGI, jamais un mock de fonction) est câblé sur
# `_fake_oauth_server.FakeGitHubOAuthServer` ci-dessous — ces valeurs sont les réponses scriptées
# que ce faux serveur renvoie, connues à l'avance pour que Playwright puisse les vérifier.
SOCIAL_GITHUB_ACCESS_TOKEN = "e2e-fake-github-access-token"
SOCIAL_GITHUB_CODE = "e2e-fake-github-code"
SOCIAL_GITHUB_USER_ID = 999001
SOCIAL_GITHUB_EMAIL = "e2e-social-github@example.com"

ORG_SLUG = "acme-e2e"
CHILD_ORG_SLUG = "acme-e2e-eu"
ROLE_CODE = "e2e-viewer"
PERMISSION_CODE = "e2e.fixture.read"
APPLICATION_NAME = "E2E Fixture App"
AGENT_ID = "e2e-agent"


async def _seed_via_sql(session_factory) -> dict:
    """Fixtures with no API-reachable creation path (verified by grepping each router — see
    module docstring). Idempotent — `docker compose up` on an already-seeded volume (if one was
    kept around) must not error, matching the Django precedent's `get_or_create` convention."""
    import bcrypt
    import pyotp
    from sqlalchemy import select

    from tenxyte.adapters.fastapi.models_sa import (
        AgentPendingActionDB,
        AgentTokenDB,
        AuditLogDB,
        BlacklistedTokenDB,
        LoginAttemptDB,
        OrganizationRoleDB,
        RefreshTokenDB,
        UserDB,
        WebAuthnCredentialDB,
    )
    from tenxyte.ports.repositories import MFAType

    totp_secret = pyotp.random_base32()
    admin_totp_secret = pyotp.random_base32()
    result: dict = {}

    async with session_factory() as session:
        def _hash(pw: str) -> str:
            return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        async def _get_or_create_user(email: str, **fields) -> UserDB:
            existing = (await session.execute(select(UserDB).where(UserDB.email == email))).scalar_one_or_none()
            if existing is not None:
                return existing
            user = UserDB(id=str(uuid.uuid4()), email=email, **fields)
            session.add(user)
            await session.flush()  # id needed by callers before commit
            return user

        verified_user = await _get_or_create_user(
            VERIFIED_USER_EMAIL,
            password_hash=_hash(VERIFIED_USER_PASSWORD),
            is_active=True,
            email_verified=True,
        )

        admin_user = await _get_or_create_user(
            ADMIN_USER_EMAIL,
            password_hash=_hash(ADMIN_USER_PASSWORD),
            first_name="Ada",
            last_name="Admin",
            is_active=True,
            is_staff=True,
            is_superuser=True,  # rbac_service.has_permission_async's superuser bypass — grants
            # every require_permission(...) route without needing to build a role/permission
            # graph just to make the fixture backend's own admin account usable.
            email_verified=True,
            # Found by actually calling /login/email/ as this admin and getting back
            # INSUFFICIENT_SCOPE, not by reading the code first: routers/auth.py's "2fa_setup_only
            # bootstrap" issues any is_staff/is_superuser account a 15-minute restricted token
            # instead of a full-scope one until 2FA is configured. Seeding it enabled up front
            # means _seed_via_api()'s admin login gets a real, full-scope token on the first try.
            mfa_type=MFAType.TOTP,
            mfa_secret=admin_totp_secret,
        )

        member_user = await _get_or_create_user(
            MEMBER_USER_EMAIL,
            password_hash=_hash(MEMBER_USER_PASSWORD),
            first_name="Marceline",
            last_name="Member",
            is_active=True,
            email_verified=True,
        )

        # A second ordinary member — tasks.md (specs/02-console-runtime, tâche 5.1) asks for
        # "3 membres" across the seeded organization(s): admin (owner) + member + this one, so
        # /orgs/:slug/members has a role-change/removal target that isn't also the sole owner.
        member2_user = await _get_or_create_user(
            MEMBER2_USER_EMAIL,
            password_hash=_hash(MEMBER2_USER_PASSWORD),
            first_name="Marcel",
            last_name="Membre",
            is_active=True,
            email_verified=True,
        )

        # mfa_type/mfa_secret: no FastAPI route enrolls 2FA yet (routers/auth.py's own docstring
        # confirms Group C hasn't shipped 2FA setup as of this port) — only a row seeded directly
        # can reach this state, same as the routers/auth.py docstring documents for tests.
        # TENXYTE_TOTP_ENCRYPTION_KEY is unset for this fixture backend (see _run()), so
        # mfa_secret is genuinely plaintext base32 here, not a placeholder — `pyotp.TOTP(secret)
        # .now()` in a Playwright test produces a real, currently-valid code against it.
        twofa_user = await _get_or_create_user(
            TWOFA_USER_EMAIL,
            password_hash=_hash(TWOFA_USER_PASSWORD),
            is_active=True,
            email_verified=True,
            mfa_type=MFAType.TOTP,
            mfa_secret=totp_secret,
        )

        # must_change_password: real and API-reachable now (register/ accepts the flag directly —
        # see module docstring), seeded via SQL anyway alongside the others here for symmetry and
        # because _seed_via_api() runs after login, and this user must NOT be able to log in
        # normally during seeding (that's the whole point of the fixture).
        must_change_user = await _get_or_create_user(
            MUST_CHANGE_USER_EMAIL,
            password_hash=_hash(MUST_CHANGE_USER_PASSWORD),
            is_active=True,
            email_verified=True,
            must_change_password=True,
        )

        # register/ stays email-only (routers/auth.py's own docstring: "nothing here creates a
        # phone-registered account") — a phone-login fixture can only be seeded directly. `email`
        # stays required (UserDB.email is non-nullable) even though nothing logs in with it here.
        phone_user = await _get_or_create_user(
            "e2e-phone@example.com",
            password_hash=_hash(PHONE_USER_PASSWORD),
            is_active=True,
            phone_verified=True,
            phone_country_code=PHONE_USER_COUNTRY_CODE,
            phone_number=PHONE_USER_NUMBER,
        )

        # password.setInitial : password_hash=None (pas _hash(...)) est le point entier de cette
        # fixture — voir le commentaire sur MUST_CHANGE_PHONE_USER_EMAIL plus haut.
        must_change_phone_user = await _get_or_create_user(
            MUST_CHANGE_PHONE_USER_EMAIL,
            password_hash=None,
            is_active=True,
            phone_verified=True,
            phone_country_code=MUST_CHANGE_PHONE_USER_COUNTRY_CODE,
            phone_number=MUST_CHANGE_PHONE_USER_NUMBER,
            must_change_password=True,
        )

        await session.flush()

        # AuditLogDB / LoginAttemptDB: no Reference_Stack auth flow writes to these tables yet
        # (models_sa.py's own docstrings confirm this explicitly) — admin/audit-logs/ and
        # admin/login-attempts/ would otherwise always render an empty list, which is a real,
        # reachable state but not a useful one to be the ONLY state an E2E/a11y run ever sees.
        existing_audit = (await session.execute(select(AuditLogDB).limit(1))).scalar_one_or_none()
        if existing_audit is None:
            session.add(
                AuditLogDB(
                    id=str(uuid.uuid4()),
                    user_id=verified_user.id,
                    action="login",
                    ip_address="127.0.0.1",
                    user_agent="seed_and_serve.py",
                    details={"seed": True},
                )
            )
            session.add(
                LoginAttemptDB(
                    id=str(uuid.uuid4()),
                    identifier=VERIFIED_USER_EMAIL,
                    ip_address="127.0.0.1",
                    success=True,
                )
            )
            session.add(
                LoginAttemptDB(
                    id=str(uuid.uuid4()),
                    identifier="unknown@example.com",
                    ip_address="127.0.0.1",
                    success=False,
                    failure_reason="Invalid credentials",
                )
            )

        # BlacklistedTokenDB / RefreshTokenDB: these DO have real write paths (logout, 2FA
        # confirm), but seeding one directly means admin/tokens/ has something to list even
        # before any E2E scenario has logged anyone out yet.
        existing_blacklisted = (await session.execute(select(BlacklistedTokenDB).limit(1))).scalar_one_or_none()
        if existing_blacklisted is None:
            session.add(
                BlacklistedTokenDB(
                    id=str(uuid.uuid4()),
                    token_jti=str(uuid.uuid4()),
                    user_id=verified_user.id,
                    expires_at=datetime.utcnow() + timedelta(days=1),
                    reason="seed",
                )
            )
        existing_refresh = (await session.execute(select(RefreshTokenDB).limit(1))).scalar_one_or_none()
        if existing_refresh is None:
            session.add(
                RefreshTokenDB(
                    id=str(uuid.uuid4()),
                    user_id=verified_user.id,
                    token_hash=uuid.uuid4().hex,
                    expires_at=datetime.utcnow() + timedelta(days=30),
                    device_info="seed_and_serve.py",
                )
            )

        # WebAuthnCredentialDB: a syntactically-valid but never-actually-registered credential, so
        # account/passkeys renders a real list item. The *ceremony* (register/authenticate) still
        # needs a real or CDP-virtual authenticator — this only covers the "list what's already
        # registered" read path, documented honestly rather than silently left empty.
        existing_credential = (
            await session.execute(select(WebAuthnCredentialDB).where(WebAuthnCredentialDB.user_id == verified_user.id))
        ).scalar_one_or_none()
        if existing_credential is None:
            session.add(
                WebAuthnCredentialDB(
                    id=str(uuid.uuid4()),
                    user_id=verified_user.id,
                    credential_id=uuid.uuid4().hex,
                    public_key="seed-placeholder-not-a-real-key",
                    device_name="Seeded security key",
                )
            )

        # OrganizationRoleDB: no route creates one (verified by grepping routers/orgs.py — only
        # GET /org-roles/ exists; "owner" is the sole role org_service.create_organization_async
        # auto-creates, found the hard way when POST /organizations/members/add/ 400'd with "Role
        # member not found"). Global catalog, not org-scoped (org_service.py's own docstring on
        # listOrgRoles confirms this — the same two rows work for every organization).
        existing_org_role = (await session.execute(select(OrganizationRoleDB).where(OrganizationRoleDB.code == "member"))).scalar_one_or_none()
        if existing_org_role is None:
            session.add(OrganizationRoleDB(id=str(uuid.uuid4()), code="member", name="Member", description="Standard member", permissions=["org.view"]))
            session.add(OrganizationRoleDB(id=str(uuid.uuid4()), code="admin", name="Admin", description="Organization admin", permissions=["org.*"]))

        await session.commit()

        result["verified_user_id"] = verified_user.id
        result["admin_user_id"] = admin_user.id
        result["admin_totp_secret"] = admin_totp_secret
        result["member_user_id"] = member_user.id
        result["member2_user_id"] = member2_user.id
        result["twofa_user_id"] = twofa_user.id
        result["twofa_secret"] = totp_secret
        result["must_change_user_id"] = must_change_user.id
        result["phone_user_id"] = phone_user.id
        result["must_change_phone_user_id"] = must_change_phone_user.id

    return result


async def _seed_pending_actions(session_factory, agent_token_id: str) -> dict:
    """Deux Pending_Actions HITL (`AgentPendingActionDB`) directement en base — aucune route ne
    les crée (`create_pending_action_async` n'est appelé que par `airs_clearance.py`'s
    `require_agent_clearance(human_in_the_loop_required=True)`, une dépendance destinée aux
    endpoints MÉTIER d'un intégrateur, jamais utilisée par `routers/airs.py` lui-même — voir son
    propre docstring). Deux lignes, pas une seule : `pendingAction.confirm` et `.deny` sont deux
    actions distinctes du Coverage_Manifest, chacune consommant irréversiblement la sienne
    (`confirmed_at`/`denied_at` posé une fois pour toutes) — les partager ferait échouer la
    seconde selon l'ordre d'exécution des tests."""
    import secrets

    from tenxyte.adapters.fastapi.models_sa import AgentPendingActionDB

    result: dict = {}
    async with session_factory() as session:
        for key in ("pending_action_confirm_token", "pending_action_deny_token"):
            token = secrets.token_urlsafe(32)
            session.add(
                AgentPendingActionDB(
                    id=str(uuid.uuid4()),
                    agent_token_id=agent_token_id,
                    permission_requested=PERMISSION_CODE,
                    endpoint="/api/v1/auth/e2e-fixture/demo-action/",
                    payload={"seeded": True},
                    confirmation_token=token,
                    expires_at=datetime.utcnow() + timedelta(hours=1),
                )
            )
            result[key] = token
        await session.commit()
    return result


async def _login(client, base_url: str, email: str, password: str, *, totp_code: str | None = None) -> str:
    payload = {"email": email, "password": password}
    if totp_code:
        payload["totp_code"] = totp_code
    response = await client.post(f"{base_url}/login/email/", json=payload)
    response.raise_for_status()
    return response.json()["access_token"]


async def _seed_via_api(base_url: str, admin_totp_secret: str) -> dict:
    """Fixtures created by actually calling the running API as an admin would — see module
    docstring for why this is preferred over hand-crafting rows wherever a route exists."""
    import httpx
    import pyotp

    result: dict = {}

    async with httpx.AsyncClient(timeout=10) as client:
        admin_totp_code = pyotp.TOTP(admin_totp_secret).now()
        admin_token = await _login(client, base_url, ADMIN_USER_EMAIL, ADMIN_USER_PASSWORD, totp_code=admin_totp_code)
        headers = {"Authorization": f"Bearer {admin_token}"}

        member_token = await _login(client, base_url, MEMBER_USER_EMAIL, MEMBER_USER_PASSWORD)
        member_me = (await client.get(f"{base_url}/me/", headers={"Authorization": f"Bearer {member_token}"})).json()
        member_id = member_me["id"]

        member2_token = await _login(client, base_url, MEMBER2_USER_EMAIL, MEMBER2_USER_PASSWORD)
        member2_id = (await client.get(f"{base_url}/me/", headers={"Authorization": f"Bearer {member2_token}"})).json()["id"]

        # Organization — creating it makes the admin its "owner" automatically (org_service.py's
        # create_organization_async auto-creates/reuses the "owner" OrganizationRoleDB row the
        # first time any organization is created). Idempotent: a 409/slug-taken response on a
        # re-seeded volume just means the fixture already exists, not a real failure.
        org_response = await client.post(
            f"{base_url}/organizations/",
            headers=headers,
            json={"name": "Acme E2E", "slug": ORG_SLUG, "description": "Fixture organization for E2E/a11y runs"},
        )
        if org_response.status_code == 201:
            org = org_response.json()
        else:
            org = (await client.get(f"{base_url}/organizations/detail/", headers={**headers, "X-Org-Slug": ORG_SLUG})).json()
        result["organization_slug"] = org["slug"]

        # A second, child organization — tasks.md asks for "2 organisations", and a real parent/
        # child pair is what makes /orgs/:slug/tree render an actual tree instead of a single node.
        child_org_response = await client.post(
            f"{base_url}/organizations/",
            headers=headers,
            json={"name": "Acme E2E — EU", "slug": CHILD_ORG_SLUG, "description": "Child fixture organization", "parent_id": org["id"]},
        )
        if child_org_response.status_code not in (201, 409):
            child_org_response.raise_for_status()
        result["child_organization_slug"] = CHILD_ORG_SLUG

        # Add both member users to the parent org — "member" is NOT auto-created the way "owner"
        # is (found the hard way: POST .../members/add/ 400'd with "Role member not found" before
        # the member/admin OrganizationRoleDB rows were seeded directly in _seed_via_sql()).
        for user_id in (member_id, member2_id):
            add_member_response = await client.post(
                f"{base_url}/organizations/members/add/",
                headers={**headers, "X-Org-Slug": ORG_SLUG},
                json={"user_id": user_id, "role_code": "member"},
            )
            if add_member_response.status_code not in (201, 409):
                add_member_response.raise_for_status()

        # RBAC role + permission — global, not org-scoped, distinct from the org role above.
        # Idempotent the same way: a 409 on re-seed means it already exists.
        perm_response = await client.post(
            f"{base_url}/permissions/",
            headers=headers,
            json={"code": PERMISSION_CODE, "name": "E2E fixture permission", "description": "Seeded for RBAC pages"},
        )
        if perm_response.status_code not in (201, 409):
            perm_response.raise_for_status()

        role_response = await client.post(
            f"{base_url}/roles/",
            headers=headers,
            json={
                "code": ROLE_CODE,
                "name": "E2E Viewer",
                "description": "Seeded for RBAC pages",
                "permission_codes": [PERMISSION_CODE],
            },
        )
        if role_response.status_code not in (201, 409):
            role_response.raise_for_status()

        # Assign the seeded role to the member user, so /rbac/users/:id has something real to show.
        assign_role_response = await client.post(
            f"{base_url}/users/{member_id}/roles/",
            headers=headers,
            json={"role_code": ROLE_CODE},
        )
        if assign_role_response.status_code not in (201, 200, 409):
            assign_role_response.raise_for_status()

        # Application.
        app_response = await client.post(
            f"{base_url}/applications/",
            headers=headers,
            json={"name": APPLICATION_NAME, "description": "Seeded for /applications pages"},
        )
        if app_response.status_code == 201:
            # Nested under "application" — POST /applications/ returns {message, application,
            # credentials, warning}, unlike GET's flat serialize_application() shape (verified by
            # reading routers/applications.py, not assumed from the JS SDK's response type).
            result["application_id"] = app_response.json()["application"]["id"]
        else:
            apps_list = (await client.get(f"{base_url}/applications/", headers=headers)).json()
            existing_app = next((a for a in apps_list["results"] if a["name"] == APPLICATION_NAME), None)
            result["application_id"] = existing_app["id"] if existing_app else None

        # AI agent token — member_token's own bearer identity triggers agent creation, not admin;
        # matches the console's actual usage (a signed-in user provisions their own agent tokens).
        # Only a superuser can create an Agent Token with delegated permissions — airs_service.py
        # literally checks `triggered_by.is_superuser`, not RBAC (found by getting
        # PERMISSION_DENIED as member_user despite member_user holding PERMISSION_CODE via RBAC;
        # the module docstring's "until Group D ships" framing is stale, but the is_superuser gate
        # itself is real and current). Created as admin, same as a real deployment would — an
        # admin provisioning an agent token for automation is the realistic case anyway.
        agent_response = await client.post(
            f"{base_url}/ai/tokens/",
            headers=headers,
            json={"agent_id": AGENT_ID, "permissions": [PERMISSION_CODE], "expires_in": 86400},
        )
        agent_response.raise_for_status()
        result["agent_token_id"] = agent_response.json()["id"]

        # GDPR account deletion request — member requests deletion of their own account.
        deletion_response = await client.post(
            f"{base_url}/request-account-deletion/",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"password": MEMBER_USER_PASSWORD, "reason": "E2E fixture"},
        )
        if deletion_response.status_code not in (200, 201):
            # Already requested on a re-seeded volume — not a real failure, same convention as
            # the other idempotent calls above.
            pass

    return result


async def _run(host: str, port: int) -> None:
    import uvicorn

    from tenxyte.adapters.fastapi.app import create_tenxyte_app
    from tenxyte.core.env_provider import EnvSettingsProvider
    from tenxyte.core.settings import Settings

    class _DemoBackendProvider(EnvSettingsProvider):
        """Reads real env vars first (so `docker-compose.yml`/an operator can override anything,
        e.g. `TENXYTE_JWT_SECRET_KEY` for a non-default deployment), with demo-appropriate
        defaults for the settings a byte-identical, zero-config `docker compose up` needs."""

        _DEFAULTS = {
            "TENXYTE_APPLICATION_AUTH_ENABLED": False,
            "TENXYTE_JWT_SECRET_KEY": "js-contract-backend-demo-secret-key-not-for-production-use-only",
            # This adapter mounts its router at bare `settings.api_prefix` (`/api/v1` by default —
            # `app.py`'s `create_tenxyte_router` has no `/auth` sub-prefix of its own). The
            # `tenxyte-js` SDK hardcodes `/api/v1/auth/...` on every module (auth.ts, rbac.ts,
            # b2b.ts, security.ts, admin.ts, ai.ts, applications.ts, dashboard.ts — all of them,
            # consistently), matching Django's own real urls.py (`path("login/email/", ...)`,
            # relative to wherever the *consuming project* mounts `include(tenxyte.urls)` — every
            # real Django deployment this package's own docs assume mounts it under `.../auth/`).
            # Without this, EVERY SDK call 404s against this backend — found by actually running
            # the Playwright E2E harness (tâche 6.1) and watching the browser's login POST come
            # back 404, not by reading either side's code first.
            "TENXYTE_API_PREFIX": "/api/v1/auth",
            # Real and API-reachable now — see module docstring. Off would silently make the
            # must_change_password fixture a lie (a seeded flag the API never actually enforces).
            "TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED": True,
            # Off by default on this adapter (app.py: `if settings.organizations_enabled:
            # router.include_router(orgs_router)`, mirroring Django's own conditional
            # `urlpatterns` block) — every /organizations/*, /org-roles/ route 404s otherwise,
            # found by actually calling the endpoint, not by reading the flag list first.
            "TENXYTE_ORGANIZATIONS_ENABLED": True,
            # Off by default — /login/otp/* (passwordless SMS login, console's /auth/sign-in/otp)
            # needs it on to do anything but reject every request.
            "TENXYTE_OTP_LOGIN_ENABLED": True,
            # Off by default — /webauthn/* routes are unconditionally registered (unlike
            # organizations) but gated at the service-call level; passkeys pages need this on to
            # exercise anything beyond a disabled-feature error.
            "TENXYTE_WEBAUTHN_ENABLED": True,
            # `py_webauthn` compares `clientDataJSON.origin` for strict equality — the
            # `rp_id`-derived default ("http://localhost", no port) never matches a real browser
            # hitting the Vite dev server above, so every register/complete and
            # authenticate/complete would fail with an origin mismatch without this override.
            "TENXYTE_WEBAUTHN_RP_ORIGIN": "http://localhost:5180",
        }

        def get(self, name, default=None):
            if name in self._DEFAULTS:
                return super().get(name, self._DEFAULTS[name])
            return super().get(name, default)

    db_path = Path.cwd() / "js-contract-backend.db"
    db_path.unlink(missing_ok=True)

    settings = Settings(provider=_DemoBackendProvider())
    app = create_tenxyte_app(settings=settings, database_url=f"sqlite+aiosqlite:///{db_path}")

    # social.exchange / social.callback : route every outbound GitHub OAuth2 call this process
    # makes to a real local ASGI app instead of the actual internet — see the constant block near
    # SOCIAL_GITHUB_* above. A global process-wide override is safe here because this script runs
    # exactly one Contract_Backend for the whole Playwright campaign (global-setup.ts), never
    # concurrent instances sharing a process.
    import httpx
    from tenxyte.adapters.fastapi import social_auth_service

    from _fake_oauth_server import FakeGitHubOAuthServer

    fake_github = FakeGitHubOAuthServer()
    fake_github.token_response = {"access_token": SOCIAL_GITHUB_ACCESS_TOKEN}
    fake_github.userinfo_response = {
        "id": SOCIAL_GITHUB_USER_ID,
        "email": SOCIAL_GITHUB_EMAIL,
        "name": "Ada E2E",
    }
    social_auth_service._test_transport = httpx.ASGITransport(app=fake_github.app)

    # create_tenxyte_app() adds no CORS middleware at all (verified by reading app.py — only
    # ApplicationAuthMiddleware is registered) — harmless for this repo's own same-origin FastAPI
    # test suite, but a real browser calling this backend from a different origin (tenxyte-js's
    # Vite dev server, a different port) gets a silent "Failed to fetch": the request reaches this
    # server fine, but the browser refuses to hand the response back to the caller's JS without an
    # Access-Control-Allow-Origin header. Found by actually running the Playwright E2E harness
    # (specs/02-console-runtime, tâche 6.1) against this backend, not by reading the code first.
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5180"],  # apps/console's Vite dev server port
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())

    while not server.started:
        await asyncio.sleep(0.05)

    sql_fixtures = await _seed_via_sql(app.state.tenxyte_session_factory)

    # The URL this process uses to call itself (for seeding below) is always loopback, regardless
    # of which host interface it bound to for external connections — same convention as the
    # Django precedent this script is adapted from.
    base_url = f"http://127.0.0.1:{port}{settings.api_prefix}"
    api_fixtures = await _seed_via_api(base_url, sql_fixtures["admin_totp_secret"])
    pending_action_fixtures = await _seed_pending_actions(app.state.tenxyte_session_factory, api_fixtures["agent_token_id"])

    info = {
        "base_url": base_url,
        "verified_user": {"email": VERIFIED_USER_EMAIL, "password": VERIFIED_USER_PASSWORD, "id": sql_fixtures["verified_user_id"]},
        "admin_user": {
            "email": ADMIN_USER_EMAIL,
            "password": ADMIN_USER_PASSWORD,
            "id": sql_fixtures["admin_user_id"],
            "totp_secret": sql_fixtures["admin_totp_secret"],
        },
        "member_user": {"email": MEMBER_USER_EMAIL, "password": MEMBER_USER_PASSWORD, "id": sql_fixtures["member_user_id"]},
        "member2_user": {"email": MEMBER2_USER_EMAIL, "password": MEMBER2_USER_PASSWORD, "id": sql_fixtures["member2_user_id"]},
        "twofa_user": {
            "email": TWOFA_USER_EMAIL,
            "password": TWOFA_USER_PASSWORD,
            "id": sql_fixtures["twofa_user_id"],
            "totp_secret": sql_fixtures["twofa_secret"],
        },
        "must_change_user": {"email": MUST_CHANGE_USER_EMAIL, "password": MUST_CHANGE_USER_PASSWORD, "id": sql_fixtures["must_change_user_id"]},
        "phone_user": {
            "phone_country_code": PHONE_USER_COUNTRY_CODE,
            "phone_number": PHONE_USER_NUMBER,
            "password": PHONE_USER_PASSWORD,
            "id": sql_fixtures["phone_user_id"],
        },
        "must_change_phone_user": {
            "phone_country_code": MUST_CHANGE_PHONE_USER_COUNTRY_CODE,
            "phone_number": MUST_CHANGE_PHONE_USER_NUMBER,
            "id": sql_fixtures["must_change_phone_user_id"],
        },
        "social_github": {
            "access_token": SOCIAL_GITHUB_ACCESS_TOKEN,
            "code": SOCIAL_GITHUB_CODE,
            "email": SOCIAL_GITHUB_EMAIL,
        },
        "organization_slug": api_fixtures["organization_slug"],
        "child_organization_slug": api_fixtures["child_organization_slug"],
        "role_code": ROLE_CODE,
        "permission_code": PERMISSION_CODE,
        "application_id": api_fixtures["application_id"],
        "agent_token_id": api_fixtures["agent_token_id"],
        "pending_action_confirm_token": pending_action_fixtures["pending_action_confirm_token"],
        "pending_action_deny_token": pending_action_fixtures["pending_action_deny_token"],
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
