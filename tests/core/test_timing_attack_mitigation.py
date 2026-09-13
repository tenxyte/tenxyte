"""
Tests for AuthenticationService's timing-attack mitigation (tenxyte.core.auth_service).

Mechanism, not wall-clock timing, is asserted: measuring real elapsed time is
inherently flaky on shared CI runners. Instead these tests verify that a
same-cost bcrypt comparison actually runs when the account does not exist,
which is the property that makes the response time comparable either way.
"""

from unittest.mock import MagicMock, patch

import pytest

from tenxyte.core.auth_service import AuthenticationService, AuthResult, PasswordUserLookup
from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User


def _make_settings(bcrypt_rounds=4):
    # bcrypt_rounds=4 (the algorithm's minimum) keeps these tests fast; the
    # property under test (same cost for both branches) holds at any rounds value.
    s = MagicMock(spec=Settings)
    s.bcrypt_rounds = bcrypt_rounds
    return s


def _make_user(**overrides):
    defaults = dict(id="u1", email="user@example.com", is_active=True, metadata={})
    defaults.update(overrides)
    return User(**defaults)


class FakeUserLookup:
    """In-memory PasswordUserLookup for testing AuthenticationService in isolation."""

    def __init__(self, users_by_identifier=None, locked_ids=None, passwords=None):
        self.users_by_identifier = users_by_identifier or {}
        self.locked_ids = locked_ids or set()
        self.passwords = passwords or {}
        self.failed_login_calls = []

    def get_by_identifier(self, identifier):
        return self.users_by_identifier.get(identifier)

    def is_account_locked(self, user_id):
        return user_id in self.locked_ids

    def check_password(self, user_id, password):
        return self.passwords.get(user_id) == password

    def record_failed_login(self, user_id):
        self.failed_login_calls.append(user_id)


def test_protocol_is_satisfied_structurally():
    lookup = FakeUserLookup()
    assert isinstance(lookup, PasswordUserLookup)


# ===========================================================================
# Timing-attack mitigation mechanism
# ===========================================================================


class TestDummyHashTimingMitigation:
    def test_dummy_bcrypt_check_runs_when_user_not_found(self):
        lookup = FakeUserLookup()
        service = AuthenticationService(settings=_make_settings(), user_lookup=lookup)

        with patch("tenxyte.core.auth_service.bcrypt.checkpw") as mock_checkpw:
            result = service.authenticate("nobody@example.com", "whatever")

        assert result == AuthResult(success=False, error="Invalid credentials", failure_reason="user_not_found")
        mock_checkpw.assert_called_once()

    def test_no_dummy_check_when_user_exists(self):
        user = _make_user()
        lookup = FakeUserLookup(users_by_identifier={"user@example.com": user}, passwords={"u1": "correct-password"})
        service = AuthenticationService(settings=_make_settings(), user_lookup=lookup)

        with patch("tenxyte.core.auth_service.bcrypt.checkpw") as mock_checkpw:
            service.authenticate("user@example.com", "correct-password")

        mock_checkpw.assert_not_called()

    def test_dummy_hash_uses_configured_bcrypt_cost(self):
        service = AuthenticationService(settings=_make_settings(bcrypt_rounds=6), user_lookup=FakeUserLookup())

        dummy_hash = service._get_dummy_hash()

        # bcrypt hash format: $2b$<cost>$<22-char-salt><31-char-hash>
        cost = int(dummy_hash.decode().split("$")[2])
        assert cost == 6

    def test_dummy_hash_is_cached_not_regenerated(self):
        service = AuthenticationService(settings=_make_settings(), user_lookup=FakeUserLookup())

        first = service._get_dummy_hash()
        second = service._get_dummy_hash()

        assert first is second

    def test_dummy_hash_falls_back_to_default_cost_without_setting(self):
        settings = MagicMock(spec=[])  # no bcrypt_rounds attribute at all
        service = AuthenticationService(settings=settings, user_lookup=FakeUserLookup())

        cost = int(service._get_dummy_hash().decode().split("$")[2])

        assert cost == 12


# ===========================================================================
# Full authenticate() decision tree
# ===========================================================================


class TestAuthenticationServiceDecisionTree:
    def test_user_not_found(self):
        service = AuthenticationService(settings=_make_settings(), user_lookup=FakeUserLookup())

        result = service.authenticate("nobody@example.com", "pw")

        assert not result.success
        assert result.failure_reason == "user_not_found"
        assert result.user is None

    def test_inactive_account(self):
        user = _make_user(is_active=False)
        lookup = FakeUserLookup(users_by_identifier={"user@example.com": user})
        service = AuthenticationService(settings=_make_settings(), user_lookup=lookup)

        result = service.authenticate("user@example.com", "pw")

        assert not result.success
        assert result.failure_reason == "account_inactive"

    def test_banned_account(self):
        user = _make_user(metadata={"is_banned": True})
        lookup = FakeUserLookup(users_by_identifier={"user@example.com": user})
        service = AuthenticationService(settings=_make_settings(), user_lookup=lookup)

        result = service.authenticate("user@example.com", "pw")

        assert not result.success
        assert result.failure_reason == "account_banned"

    def test_locked_account(self):
        user = _make_user()
        lookup = FakeUserLookup(users_by_identifier={"user@example.com": user}, locked_ids={"u1"})
        service = AuthenticationService(settings=_make_settings(), user_lookup=lookup)

        result = service.authenticate("user@example.com", "pw")

        assert not result.success
        assert result.failure_reason == "account_locked"

    def test_wrong_password_records_failed_login(self):
        user = _make_user()
        lookup = FakeUserLookup(users_by_identifier={"user@example.com": user}, passwords={"u1": "correct"})
        service = AuthenticationService(settings=_make_settings(), user_lookup=lookup)

        result = service.authenticate("user@example.com", "wrong")

        assert not result.success
        assert result.failure_reason == "invalid_password"
        assert lookup.failed_login_calls == ["u1"]

    def test_success(self):
        user = _make_user()
        lookup = FakeUserLookup(users_by_identifier={"user@example.com": user}, passwords={"u1": "correct"})
        service = AuthenticationService(settings=_make_settings(), user_lookup=lookup)

        result = service.authenticate("user@example.com", "correct")

        assert result.success
        assert result.user is user
        assert lookup.failed_login_calls == []
