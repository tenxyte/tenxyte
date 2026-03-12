"""
Tests for core magic_link_service - targeting 100% coverage of
src/tenxyte/core/magic_link_service.py
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from tenxyte.core.magic_link_service import (
    MagicLinkToken,
    MagicLinkResult,
    MagicLinkService,
    MagicLinkRepository,
    UserLookup,
)
from tenxyte.core.settings import Settings
from typing import Optional, Dict


# Protocole implementations for coverage
class DummyMagicLinkRepo(MagicLinkRepository):
    def create(self, hash, uid, email, app_id=None, ip=None, ua=None, exp=15) -> MagicLinkToken: return None
    def get_by_token(self, token: str) -> Optional[MagicLinkToken]: return None
    def invalidate_user_tokens(self, uid: str, app_id=None) -> int: return 0
    def consume(self, token_id: str) -> bool: return True

class DummyUserLookup(UserLookup):
    def get_by_email(self, email: str) -> Optional[Dict]: return None
    def is_active(self, uid: str) -> bool: return True
    def is_locked(self, uid: str) -> bool: return False

def test_protocols():
    repo = DummyMagicLinkRepo()
    assert repo.create("", "", "") is None
    assert repo.get_by_token("") is None
    assert repo.invalidate_user_tokens("") == 0
    assert repo.consume("")

    ul = DummyUserLookup()
    assert ul.get_by_email("") is None
    assert ul.is_active("")
    assert not ul.is_locked("")


def _make_settings(**overrides):
    s = MagicMock(spec=Settings)
    s.magic_link_enabled = overrides.get("enabled", True)
    s.magic_link_expiry_minutes = overrides.get("expiry", 15)
    s.app_name = overrides.get("app_name", "Test")
    return s


def _make_token(**overrides):
    defaults = dict(
        id="t1", token="", user_id="u1", email="u@x.com",
        application_id=None, ip_address="1.2.3.4",
        user_agent="UA", created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        used_at=None, is_used=False,
    )
    defaults.update(overrides)
    return MagicLinkToken(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# MagicLinkToken  (lines 22-42)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMagicLinkToken:

    def test_is_valid_true(self):
        """Line 41: not used, not expired."""
        t = _make_token()
        assert t.is_valid() is True

    def test_is_valid_used(self):
        """Line 38-39: used → invalid."""
        t = _make_token(is_used=True)
        assert t.is_valid() is False

    def test_is_valid_expired(self):
        """Lines 40-41: expired → invalid."""
        t = _make_token(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        assert t.is_valid() is False

    def test_optional_fields(self):
        """Lines 69, 73, 81, 85, 94, 98, 102: default None/False."""
        t = MagicLinkToken(id="1", token="t", user_id="u", email="e@x.com")
        assert t.application_id is None
        assert t.ip_address is None
        assert t.user_agent is None
        assert t.created_at is None
        assert t.expires_at is None
        assert t.used_at is None
        assert t.is_used is False


# ═══════════════════════════════════════════════════════════════════════════════
# MagicLinkService  (lines 105-356)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMagicLinkService:

    @pytest.fixture
    def deps(self):
        repo = MagicMock()
        user_lookup = MagicMock()
        email_svc = MagicMock()
        return repo, user_lookup, email_svc

    @pytest.fixture
    def svc(self, deps):
        repo, user_lookup, email_svc = deps
        return MagicLinkService(
            settings=_make_settings(),
            repo=repo, user_lookup=user_lookup, email_service=email_svc
        )

    # -- request_magic_link --

    def test_request_disabled(self, deps):
        """Line 192."""
        repo, ul, email = deps
        svc = MagicLinkService(settings=_make_settings(enabled=False), repo=repo, user_lookup=ul, email_service=email)
        ok, err = svc.request_magic_link("e@x.com")
        assert ok is False
        assert "not enabled" in err

    def test_request_user_not_found(self, svc, deps):
        """Lines 199-200: unknown email → True (security)."""
        deps[1].get_by_email.return_value = None
        ok, err = svc.request_magic_link("unknown@x.com")
        assert ok is True

    def test_request_user_dict(self, svc, deps):
        """Lines 203-206: user is dict."""
        deps[1].get_by_email.return_value = {"id": "u1", "email": "u@x.com", "first_name": "A"}
        deps[1].is_active.return_value = True
        deps[0].create.return_value = _make_token()
        ok, err = svc.request_magic_link("u@x.com", validation_url="https://app.com/magic")
        assert ok is True

    def test_request_user_object(self, svc, deps):
        """Lines 209-211: user is object."""
        user = MagicMock()
        user.id = "u1"
        user.email = "u@x.com"
        user.first_name = "Bob"
        deps[1].get_by_email.return_value = user
        deps[1].is_active.return_value = True
        deps[0].create.return_value = _make_token()
        ok, err = svc.request_magic_link("u@x.com")
        assert ok is True

    def test_request_inactive_user(self, svc, deps):
        """Lines 215-216: inactive user → True."""
        deps[1].get_by_email.return_value = {"id": "u1", "email": "u@x.com"}
        deps[1].is_active.return_value = False
        ok, _ = svc.request_magic_link("u@x.com")
        assert ok is True

    def test_request_email_failure(self, svc, deps):
        """Lines 245-247: email sending fails."""
        deps[1].get_by_email.return_value = {"id": "u1", "email": "u@x.com"}
        deps[1].is_active.return_value = True
        deps[0].create.return_value = _make_token()
        deps[2].send_magic_link.side_effect = Exception("SMTP error")
        ok, err = svc.request_magic_link("u@x.com")
        assert ok is False
        assert "Failed" in err

    # -- verify_magic_link --

    def test_verify_disabled(self, deps):
        """Line 274."""
        repo, ul, email = deps
        svc = MagicLinkService(settings=_make_settings(enabled=False), repo=repo, user_lookup=ul, email_service=email)
        result = svc.verify_magic_link("token")
        assert not result.success

    def test_verify_not_found(self, svc, deps):
        """Lines 294-295."""
        deps[0].get_by_token.return_value = None
        result = svc.verify_magic_link("bad")
        assert not result.success
        assert "Invalid" in result.error

    def test_verify_expired(self, svc, deps):
        """Lines 306-310: token not valid."""
        t = _make_token(is_used=True)
        deps[0].get_by_token.return_value = t
        result = svc.verify_magic_link("tok")
        assert not result.success

    def test_verify_wrong_app(self, svc, deps):
        """Lines 306-310: application mismatch."""
        t = _make_token(application_id="app1")
        deps[0].get_by_token.return_value = t
        result = svc.verify_magic_link("tok", application_id="app2")
        assert not result.success
        assert "application" in result.error

    def test_verify_ip_mismatch(self, svc, deps):
        """Lines 317: same-device check fails."""
        t = _make_token(ip_address="10.0.0.1")
        deps[0].get_by_token.return_value = t
        result = svc.verify_magic_link("tok", ip_address="192.168.0.1")
        assert not result.success
        assert "same device" in result.error

    def test_verify_user_inactive(self, svc, deps):
        """Line 317: user not active."""
        t = _make_token()
        deps[0].get_by_token.return_value = t
        deps[1].is_active.return_value = False
        result = svc.verify_magic_link("tok", require_same_device=False)
        assert not result.success
        assert "disabled" in result.error

    def test_verify_user_locked(self, svc, deps):
        """Line 320: user locked."""
        t = _make_token()
        deps[0].get_by_token.return_value = t
        deps[1].is_active.return_value = True
        deps[1].is_locked.return_value = True
        result = svc.verify_magic_link("tok", require_same_device=False)
        assert not result.success
        assert "locked" in result.error

    def test_verify_success(self, svc, deps):
        """Lines 342-356: full success path."""
        t = _make_token()
        deps[0].get_by_token.return_value = t
        deps[1].is_active.return_value = True
        deps[1].is_locked.return_value = False
        result = svc.verify_magic_link("tok", require_same_device=False)
        assert result.success
        assert result.user_id == "u1"
        deps[0].consume.assert_called_once()

    # -- _ip_matches --

    def test_ip_matches_none(self, svc):
        """Line 342: no IPs → True."""
        assert svc._ip_matches(None, "1.2.3.4") is True
        assert svc._ip_matches("1.2.3.4", None) is True

    def test_ip_matches_exact(self, svc):
        """Line 342-343."""
        assert svc._ip_matches("1.2.3.4", "1.2.3.4") is True

    def test_ip_matches_subnet(self, svc):
        """Lines 346-352: /24 subnet match."""
        assert svc._ip_matches("1.2.3.4", "1.2.3.99") is True
        assert svc._ip_matches("1.2.3.4", "1.2.4.4") is False

    def test_ip_matches_invalid(self, svc):
        """Lines 353-356: invalid IP format (e.g. ValueError)."""
        assert svc._ip_matches("not-an-ip", "also-not") is False
        assert svc._ip_matches("1.2.3.4", "not-an-ip") is False
