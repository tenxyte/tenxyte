"""
Tests for rate_limit() (spec z_aud_3, Requirement 3.4) — parity with the scope/rate families in
`tenxyte.throttles`'s `IPBasedThrottle` subclasses, proven against the real `InMemoryCacheService`
with simulated time (monkeypatching `time.time` in `tenxyte.core.cache_service`, the only place
that module reads the wall clock) rather than sleeping in real time.
"""

import uuid

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from tenxyte.adapters.fastapi import throttling
from tenxyte.adapters.fastapi.app import create_tenxyte_app
from tenxyte.core import cache_service as cache_service_module
from tenxyte.core.env_provider import EnvSettingsProvider
from tenxyte.core.settings import Settings


def _fresh_sqlite_url() -> str:
    return f"sqlite+aiosqlite:///file:{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"


class _NoApplicationAuthProvider(EnvSettingsProvider):
    """These tests exercise `rate_limit` in isolation — ApplicationAuthMiddleware, which runs
    first in the stack, is disabled here since it has its own dedicated test suite in
    test_application_auth.py."""

    def get(self, name, default=None):
        if name == "TENXYTE_APPLICATION_AUTH_ENABLED":
            return False
        return super().get(name, default)


def _build_app(*scopes: str):
    settings = Settings(provider=_NoApplicationAuthProvider())
    app = create_tenxyte_app(settings=settings, database_url=_fresh_sqlite_url())

    @app.get("/limited")
    async def limited(_: None = Depends(throttling.rate_limit(*scopes))):
        return {"ok": True}

    return app


async def _make_client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def fake_clock(monkeypatch):
    """A controllable clock swapped into tenxyte.core.cache_service's time.time()."""
    state = {"now": 1_000_000.0}

    def _time():
        return state["now"]

    monkeypatch.setattr(cache_service_module.time, "time", _time)

    def _advance(seconds: float) -> None:
        state["now"] += seconds

    return _advance


def test_rate_limit_rejects_unknown_scope():
    with pytest.raises(ValueError, match="Unknown rate limit scope"):
        throttling.rate_limit("not_a_real_scope")


@pytest.mark.anyio
async def test_requests_within_limit_are_allowed(fake_clock):
    app = _build_app("otp_verify")  # 5/min
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        for _ in range(5):
            response = await client.get("/limited")
            assert response.status_code == 200


@pytest.mark.anyio
async def test_request_over_limit_is_rejected_with_canonical_429(fake_clock):
    app = _build_app("otp_verify")  # 5/min
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        for _ in range(5):
            assert (await client.get("/limited")).status_code == 200

        response = await client.get("/limited")

    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "RATE_LIMIT_EXCEEDED"
    assert body["details"]["scope"] == "otp_verify"


@pytest.mark.anyio
async def test_limit_resets_after_the_window_elapses(fake_clock):
    app = _build_app("otp_verify")  # 5/min
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        for _ in range(5):
            assert (await client.get("/limited")).status_code == 200
        assert (await client.get("/limited")).status_code == 429

        fake_clock(61)  # past the 1-minute window

        assert (await client.get("/limited")).status_code == 200


@pytest.mark.anyio
async def test_different_client_ips_have_independent_budgets(fake_clock):
    app = _build_app("otp_verify")  # 5/min
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, client=("10.0.0.1", 12345))
        async with AsyncClient(transport=transport, base_url="http://test") as client_a:
            for _ in range(5):
                assert (await client_a.get("/limited")).status_code == 200
            assert (await client_a.get("/limited")).status_code == 429

        transport_b = ASGITransport(app=app, client=("10.0.0.2", 12345))
        async with AsyncClient(transport=transport_b, base_url="http://test") as client_b:
            assert (await client_b.get("/limited")).status_code == 200


@pytest.mark.anyio
async def test_stacked_scopes_reject_on_the_tighter_one(fake_clock):
    # login: 5/min, login_hourly: 20/hour — the per-minute scope trips first.
    app = _build_app("login", "login_hourly")
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        for _ in range(5):
            assert (await client.get("/limited")).status_code == 200

        response = await client.get("/limited")

    assert response.status_code == 429
    assert response.json()["details"]["scope"] == "login"


@pytest.mark.anyio
async def test_stacked_scopes_reject_on_the_hourly_budget_even_within_the_minute_budget(fake_clock):
    # login: 5/min, login_hourly: 20/hour. Exhaust the hourly budget across several
    # minute-windows (advancing the clock past each minute window resets "login" but not
    # "login_hourly"), then confirm the hourly scope alone blocks further requests.
    app = _build_app("login", "login_hourly")
    async with app.router.lifespan_context(app), await _make_client(app) as client:
        for _minute in range(4):
            for _ in range(5):
                assert (await client.get("/limited")).status_code == 200
            fake_clock(61)

        # 20 requests consumed against login_hourly's budget of 20 — the 21st is rejected.
        response = await client.get("/limited")

    assert response.status_code == 429
    assert response.json()["details"]["scope"] == "login_hourly"
