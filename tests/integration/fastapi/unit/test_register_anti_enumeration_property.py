"""
Feature: z_aud_3, Property 3: anti-enumeration parity for `POST /register/` — the response shape
(same keys, same types) is identical whether the submitted email already belongs to an account or
not, for generated emails/passwords. Django_Adapter parity: `RegisterView` returns the same fake
"Registration successful" body either way (spec z_aud_3, task 5.2).
"""

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.adapters.fastapi.repositories_async import SQLAlchemyAsyncUserRepository
from tenxyte.core.auth_service import hash_password
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _TestProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-anti-enum-property"
        return super().get(name, default)


def _response_shape(body: dict) -> dict:
    """Keys and value *types* only — not the values themselves, which legitimately differ
    (echoed email, random fake id, ...)."""

    def _shape(value):
        if isinstance(value, dict):
            return {k: _shape(v) for k, v in value.items()}
        return type(value).__name__

    return _shape(body)


async def _register(client, email: str, password: str) -> tuple[int, dict]:
    response = await client.post("/api/v1/register/", json={"email": email, "password": password})
    return response.status_code, response.json()


async def _run_scenario(email: str, password: str) -> tuple[tuple[int, dict], tuple[int, dict]]:
    settings_obj = Settings(provider=_TestProvider())
    app = create_tenxyte_app(settings=settings_obj, database_url=_fresh_sqlite_url())

    async with app.router.lifespan_context(app):
        session_factory = app.state.tenxyte_session_factory
        async with session_factory() as session:
            repo = SQLAlchemyAsyncUserRepository(session)
            hashed = hash_password("some-other-password-1")
            await repo.create(User(id=str(uuid.uuid4()), email=email, password_hash=hashed, is_active=True))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            existing_result = await _register(client, email, password)

        fresh_email = f"{uuid.uuid4().hex}@example.com"
        transport2 = ASGITransport(app=app)
        async with AsyncClient(transport=transport2, base_url="http://test") as client:
            new_result = await _register(client, fresh_email, password)

    return existing_result, new_result


_emails = st.emails()
_passwords = st.text(min_size=8, max_size=40).filter(
    lambda p: p.strip() == p and len(p.strip()) >= 8 and len(p.encode("utf-8")) <= 72
)


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=25)
@given(email=_emails, password=_passwords)
def test_property_register_response_shape_is_identical_for_existing_and_new_accounts(email, password):
    (existing_status, existing_body), (new_status, new_body) = asyncio.run(_run_scenario(email, password))

    assert existing_status == new_status == 201
    assert _response_shape(existing_body) == _response_shape(new_body)
    assert existing_body["message"] == new_body["message"] == "Registration successful"
    assert (
        existing_body["verification_required"]
        == new_body["verification_required"]
        == {
            "email": True,
            "phone": False,
        }
    )
