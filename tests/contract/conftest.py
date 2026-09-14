"""
Contract_Suite fixture (spec z_aud_3, task 3.2, Property 2): a single HTTP-shaped client
interface run against both adapters, so the same contract test proves the same thing on each.

`django` invokes the DRF view class directly via `APIRequestFactory` (the same technique
`test_endpoint_response_shape_snapshots.py` already uses) bridged through `asgiref.sync_to_async`
— Django's ORM refuses synchronous DB access from a running event loop otherwise. `fastapi` drives
a real `create_tenxyte_app()` over `httpx.AsyncClient(ASGITransport(...))`, no mocks.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from asgiref.sync import sync_to_async
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings

# path (as used by the Contract_Suite, e.g. "/register/") -> Django view class
_DJANGO_VIEW_MAP: dict[str, Any] = {}


def _register_django_view(path: str, view_cls: Any) -> None:
    _DJANGO_VIEW_MAP[path] = view_cls


def _django_response_body(response) -> dict:
    """Most views return a DRF `Response` (`.data`), but `@require_jwt`'s own auth-failure short-
    circuits return a raw Django `JsonResponse` instead (`.content` bytes, no `.data`) — normalize
    both to a plain dict."""
    if hasattr(response, "data"):
        return response.data or {}
    import json

    return json.loads(response.content) if response.content else {}


@dataclass
class ContractResponse:
    status_code: int
    body: dict


class DjangoContractClient:
    def __init__(self, application):
        self.application = application

    async def post(self, path: str, json: dict, *, headers: dict[str, str] | None = None) -> ContractResponse:
        from unittest.mock import patch

        from rest_framework.test import APIRequestFactory

        view_cls = _DJANGO_VIEW_MAP[path]

        def _call() -> ContractResponse:
            factory = APIRequestFactory()
            extra = {}
            if headers and "Authorization" in headers:
                extra["HTTP_AUTHORIZATION"] = headers["Authorization"]
            request = factory.post(path, data=json, format="json", **extra)
            request.application = self.application
            with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
                response = view_cls.as_view()(request)
            return ContractResponse(status_code=response.status_code, body=_django_response_body(response))

        return await sync_to_async(_call, thread_sensitive=True)()

    async def get(
        self, path: str, params: dict | None = None, *, headers: dict[str, str] | None = None
    ) -> ContractResponse:
        from unittest.mock import patch

        from rest_framework.test import APIRequestFactory

        view_cls = _DJANGO_VIEW_MAP[path]

        def _call() -> ContractResponse:
            factory = APIRequestFactory()
            extra = {}
            if headers and "Authorization" in headers:
                extra["HTTP_AUTHORIZATION"] = headers["Authorization"]
            request = factory.get(path, data=params or {}, **extra)
            request.application = self.application
            with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
                response = view_cls.as_view()(request)
            return ContractResponse(status_code=response.status_code, body=_django_response_body(response))

        return await sync_to_async(_call, thread_sensitive=True)()


def _body_or_empty(response) -> dict:
    """A password/reset/request-style unknown-account response has a genuinely empty body (no
    JSON at all — see PasswordResetRequestView's `Response(status=200)`), which `.json()` would
    raise on; normalize to `{}` so both clients' `ContractResponse.body` is always a dict."""
    if not response.content:
        return {}
    return response.json()


class FastAPIContractClient:
    def __init__(self, client: AsyncClient, api_prefix: str):
        self.client = client
        self.api_prefix = api_prefix

    async def post(self, path: str, json: dict, *, headers: dict[str, str] | None = None) -> ContractResponse:
        response = await self.client.post(f"{self.api_prefix}{path}", json=json, headers=headers or {})
        return ContractResponse(status_code=response.status_code, body=_body_or_empty(response))

    async def get(
        self, path: str, params: dict | None = None, *, headers: dict[str, str] | None = None
    ) -> ContractResponse:
        response = await self.client.get(f"{self.api_prefix}{path}", params=params or {}, headers=headers or {})
        return ContractResponse(status_code=response.status_code, body=_body_or_empty(response))


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _NoApplicationAuthProvider(EnvSettingsProvider):
    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        if name == "TENXYTE_JWT_SECRET_KEY":
            return "test-secret-key-for-contract-suite"
        return super().get(name, default)


@pytest.fixture(params=["django", "fastapi"])
async def api(request):
    if request.param == "django":
        from tenxyte.models import Application

        application, _ = await sync_to_async(Application.create_application, thread_sensitive=True)(
            name=f"contract-suite-{uuid.uuid4().hex}"
        )
        yield DjangoContractClient(application)
        return

    settings = Settings(provider=_NoApplicationAuthProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield FastAPIContractClient(client, settings.api_prefix)


@pytest.fixture(autouse=True)
def _register_group_a_views():
    """Registers Django's Group A view classes under the same relative paths the FastAPI side
    mounts them at, so `api.post("/register/", ...)` means the same thing on both backends."""
    from tenxyte.views.auth_views import LoginEmailView, LoginPhoneView, RegisterView

    _register_django_view("/register/", RegisterView)
    _register_django_view("/login/email/", LoginEmailView)
    # No contract test exercises this yet — FastAPI's /register/ is still email-only, so a
    # shape-parity test would need a backend-specific seeding hook the `api` fixture doesn't
    # expose yet. Registered for when that lands; both adapters' own suites already cover
    # login/phone directly in the meantime.
    _register_django_view("/login/phone/", LoginPhoneView)


@pytest.fixture(autouse=True)
def _register_group_b_views():
    """Registers Django's Group B view classes (spec z_aud_3, task 7.3)."""
    from tenxyte.views.password_views import PasswordRequirementsView, PasswordResetRequestView

    _register_django_view("/password/requirements/", PasswordRequirementsView)
    _register_django_view("/password/reset/request/", PasswordResetRequestView)


@pytest.fixture(autouse=True)
def _register_group_c_views():
    """Registers Django's Group C view classes (spec z_aud_3, task 7.3)."""
    from tenxyte.views.magic_link_views import MagicLinkRequestView
    from tenxyte.views.otp_views import RequestOTPView
    from tenxyte.views.twofa_views import TwoFactorStatusView

    _register_django_view("/magic-link/request/", MagicLinkRequestView)
    _register_django_view("/otp/request/", RequestOTPView)
    _register_django_view("/2fa/status/", TwoFactorStatusView)


@pytest.fixture(autouse=True)
def _register_group_f_views():
    """Registers Django's Group F (AIRS) view classes (spec z_aud_3, task 9.3)."""
    from tenxyte.views.agent_views import AgentTokenListCreateView, AIRSDiscoveryView

    _register_django_view("/ai/tokens/", AgentTokenListCreateView)
    _register_django_view("/ai/.well-known/airs/", AIRSDiscoveryView)


async def register_and_login(api) -> tuple[str, str]:
    """Shared helper (spec z_aud_3, task 7.3): register a fresh account and log in, returning
    `(access_token, email)` — identical on both backends since Group A's `/register/`/
    `/login/email/` contract is already proven by `test_group_a_shapes.py`. Used by Group B/C
    contract tests that need an authenticated request."""
    email = f"contract-{uuid.uuid4().hex}@example.com"
    password = "Correct-Horse-Battery-Staple-1"
    register_response = await api.post("/register/", json={"email": email, "password": password})
    assert register_response.status_code == 201
    login_response = await api.post("/login/email/", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return login_response.body["access_token"], email
