"""
Async coverage tests for:
  - core/magic_link_service.py (lines 291-373, 451-504)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any, Dict, Optional

from tenxyte.core.magic_link_service import (
    MagicLinkService,
    MagicLinkToken,
    MagicLinkResult,
    MagicLinkRepository,
)
from tenxyte.core.email_service import ConsoleEmailService


# ─── Helpers ─────────────────────────────────────────────────────────────────

class DummySettings:
    magic_link_enabled = True
    magic_link_expiry_minutes = 15
    magic_link_require_same_device = False


class DummyUser(dict):
    pass


class DummyUserLookup:
    def __init__(self, user_data=None, active=True, locked=False):
        self._user = user_data or {"id": "u1", "email": "u@example.com"}
        self._active = active
        self._locked = locked

    def get_by_email(self, email):
        return self._user

    def is_active(self, user_id):
        return self._active

    def is_locked(self, user_id):
        return self._locked


class AsyncUserLookup(DummyUserLookup):
    async def get_by_email_async(self, email):
        return self._user

    async def is_active_async(self, user_id):
        return self._active

    async def is_locked_async(self, user_id):
        return self._locked


class DummyRepo:
    def __init__(self, token=None):
        self._token = token

    def create(self, token_hash, user_id, email, application_id=None,
               ip_address=None, user_agent=None, expiry_minutes=15):
        return MagicLinkToken(id="tid", token=token_hash, user_id=user_id, email=email)

    def get_by_token(self, token):
        return self._token

    def invalidate_user_tokens(self, user_id, application_id=None):
        return 0

    def consume(self, token_id):
        return True


class AsyncRepo(DummyRepo):
    async def create_async(self, token_hash, user_id, email, application_id=None,
                           ip_address=None, user_agent=None, expiry_minutes=15):
        return self.create(token_hash, user_id, email)

    async def get_by_token_async(self, token):
        return self._token

    async def invalidate_user_tokens_async(self, user_id, application_id=None):
        return 0

    async def consume_async(self, token_id):
        return True


@pytest.fixture
def settings():
    return DummySettings()


@pytest.fixture
def email_svc():
    return ConsoleEmailService()


def _make_service(settings, email_svc, repo, user_lookup):
    return MagicLinkService(
        settings=settings,
        email_service=email_svc,
        repo=repo,
        user_lookup=user_lookup,
    )


def _make_valid_token():
    from datetime import datetime, timezone, timedelta
    return MagicLinkToken(
        id="tid",
        token="rawtoken",
        user_id="u1",
        email="u@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )


# ─── request_magic_link_async (lines 291-373) ────────────────────────────────

class TestRequestMagicLinkAsync:
    @pytest.mark.anyio
    async def test_async_repo_and_lookup(self, settings, email_svc):
        """Lines 294-350: async user lookup + async repo create."""
        repo = AsyncRepo()
        lookup = AsyncUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        ok, msg = await svc.request_magic_link_async("u@example.com")
        assert ok is True

    @pytest.mark.anyio
    async def test_sync_repo_and_lookup_fallback(self, settings, email_svc):
        """Lines 296-350: sync lookup + repo via to_thread."""
        repo = DummyRepo()
        lookup = DummyUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        ok, msg = await svc.request_magic_link_async("u@example.com")
        assert ok is True

    @pytest.mark.anyio
    async def test_user_not_found(self, settings, email_svc):
        """Lines 299-301: unknown email -> return True silently."""
        class EmptyLookup:
            def get_by_email(self, email): return None
        repo = DummyRepo()
        svc = _make_service(settings, email_svc, repo, EmptyLookup())
        ok, err = await svc.request_magic_link_async("unknown@example.com")
        assert ok is True
        assert err == ""

    @pytest.mark.anyio
    async def test_inactive_user(self, settings, email_svc):
        """Lines 318-320: inactive user -> return True silently."""
        repo = AsyncRepo()
        lookup = AsyncUserLookup(active=False)
        svc = _make_service(settings, email_svc, repo, lookup)
        ok, err = await svc.request_magic_link_async("u@example.com")
        assert ok is True
        assert err == ""

    @pytest.mark.anyio
    async def test_disabled_service(self, settings, email_svc):
        """Lines 291-292: disabled -> False."""
        settings.magic_link_enabled = False
        repo = DummyRepo()
        lookup = DummyUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        ok, err = await svc.request_magic_link_async("u@example.com")
        assert ok is False

    @pytest.mark.anyio
    async def test_email_send_failure(self, settings):
        """Lines 368-370: email failure -> False."""
        class FailEmail(ConsoleEmailService):
            def send(self, *a, **kw): raise RuntimeError("SMTP down")
        repo = AsyncRepo()
        lookup = AsyncUserLookup()
        svc = _make_service(settings, FailEmail(), repo, lookup)
        ok, err = await svc.request_magic_link_async("u@example.com")
        assert ok is False
        assert "Failed to send" in err


# ─── verify_magic_link_async (lines 451-504) ─────────────────────────────────

class TestVerifyMagicLinkAsync:
    @pytest.mark.anyio
    async def test_valid_link_async_repo(self, settings, email_svc):
        """Lines 454-503: async repo + async lookup, valid token."""
        token = _make_valid_token()
        repo = AsyncRepo(token=token)
        lookup = AsyncUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("rawtoken")
        assert result.success is True

    @pytest.mark.anyio
    async def test_valid_link_sync_repo(self, settings, email_svc):
        """Lines 456-457: sync repo via to_thread."""
        token = _make_valid_token()
        repo = DummyRepo(token=token)
        lookup = DummyUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("rawtoken")
        assert result.success is True

    @pytest.mark.anyio
    async def test_invalid_token_not_found(self, settings, email_svc):
        """Lines 459-460: token not found."""
        repo = AsyncRepo(token=None)
        lookup = AsyncUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("bad_token")
        assert result.success is False

    @pytest.mark.anyio
    async def test_expired_token(self, settings, email_svc):
        """Lines 462-463: expired token."""
        from datetime import datetime, timezone, timedelta
        expired_token = MagicLinkToken(
            id="tid", token="rawtoken", user_id="u1", email="u@example.com",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        repo = AsyncRepo(token=expired_token)
        lookup = AsyncUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("rawtoken")
        assert result.success is False

    @pytest.mark.anyio
    async def test_inactive_user_verify(self, settings, email_svc):
        """Lines 481-487: inactive user -> Account is disabled."""
        token = _make_valid_token()
        repo = AsyncRepo(token=token)
        lookup = AsyncUserLookup(active=False)
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("rawtoken")
        assert result.success is False
        assert "disabled" in result.error

    @pytest.mark.anyio
    async def test_locked_user_verify(self, settings, email_svc):
        """Lines 489-495: locked user -> Account is locked."""
        token = _make_valid_token()
        repo = AsyncRepo(token=token)
        lookup = AsyncUserLookup(locked=True)
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("rawtoken")
        assert result.success is False
        assert "locked" in result.error

    @pytest.mark.anyio
    async def test_disabled_service_verify(self, settings, email_svc):
        """Lines 451-452: service disabled."""
        settings.magic_link_enabled = False
        repo = AsyncRepo()
        lookup = AsyncUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("token")
        assert result.success is False

    @pytest.mark.anyio
    async def test_application_id_mismatch(self, settings, email_svc):
        """Lines 465-467."""
        token = _make_valid_token()
        token.application_id = "app_correct"
        repo = AsyncRepo(token=token)
        lookup = AsyncUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("token", application_id="app_wrong")
        assert result.success is False
        assert "application" in result.error

    @pytest.mark.anyio
    async def test_ip_mismatch_same_device(self, settings, email_svc):
        """Lines 469-479."""
        token = _make_valid_token()
        token.ip_address = "1.2.3.4"
        repo = AsyncRepo(token=token)
        lookup = AsyncUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        # mismatch
        result = await svc.verify_magic_link_async("token", require_same_device=True, ip_address="5.6.7.8")
        assert result.success is False
        assert "same device" in result.error

    @pytest.mark.anyio
    async def test_ip_subnet_match(self, settings, email_svc):
        """Lines 518-529: subnet matching."""
        svc = _make_service(settings, email_svc, AsyncRepo(), AsyncUserLookup())
        assert svc._ip_matches("192.168.1.5", "192.168.1.10") is True # /24 match
        assert svc._ip_matches("192.168.1.5", "192.168.2.5") is False
        assert svc._ip_matches("10.0.0.1", "10.0.0.255") is True
        assert svc._ip_matches("10.0.1.1", "10.0.0.1") is False
        # To hit exception path: use different invalid strings that will fail split comparison
        assert svc._ip_matches("invalid-ip", "another-invalid") is False # exception path 529

    @pytest.mark.anyio
    async def test_consume_fallback(self, settings, email_svc):
        """Line 500: fallback to sync consume."""
        token = _make_valid_token()
        repo = DummyRepo(token=token) # sync repo
        lookup = DummyUserLookup()
        svc = _make_service(settings, email_svc, repo, lookup)
        result = await svc.verify_magic_link_async("rawtoken")
        assert result.success is True

