"""
Authentication Service for Tenxyte Core.

Framework-agnostic credential verification (identifier + password), including a
timing-attack mitigation for account enumeration via login response latency.
"""

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import bcrypt

from tenxyte.core.settings import Settings
from tenxyte.ports.repositories import User

logger = logging.getLogger(__name__)

# Fixed plaintext hashed into the dummy comparison. Never compared against a real
# password — only its bcrypt cost (shared with real hashes via Settings.bcrypt_rounds)
# matters for the timing mitigation to hold.
_DUMMY_PASSWORD = b"tenxyte-dummy-timing-mitigation"


@dataclass
class AuthResult:
    """Result of a credential verification attempt."""

    success: bool
    user: User | None = None
    error: str = ""
    failure_reason: str = ""


@runtime_checkable
class PasswordUserLookup(Protocol):
    """
    Protocol for identifier + password credential storage lookups.

    `identifier` is deliberately opaque to Core (not typed `str`): an adapter
    resolves it however it needs to — an email string, a `(country_code,
    phone_number)` tuple, a username, ... — the Core service only calls the
    four operations below and never inspects `identifier` itself.
    """

    def get_by_identifier(self, identifier: object) -> User | None:
        """Resolve a user by whatever identifier the adapter supports."""
        ...  # pragma: no cover

    def is_account_locked(self, user_id: str) -> bool:
        """Check whether the account is locked out (e.g. too many failed attempts)."""
        ...  # pragma: no cover

    def check_password(self, user_id: str, password: str) -> bool:
        """Verify the password against the stored hash."""
        ...  # pragma: no cover

    def record_failed_login(self, user_id: str) -> None:
        """Record a failed login attempt (e.g. for lockout escalation)."""
        ...  # pragma: no cover


class AuthenticationService:
    """
    Framework-agnostic password-based authentication.

    Decides whether an identifier+password pair is valid — independent of how
    tokens are issued, how the login is audited, or which framework/database is
    used. Adapters (Django, FastAPI) supply a `PasswordUserLookup` and handle
    everything downstream of the returned `AuthResult` (JWT issuance, audit
    logging, response shaping, ...).

    Timing-attack mitigation: when `identifier` does not resolve to any
    account, a dummy bcrypt comparison of matching cost is still performed, so
    the response time does not reveal whether the account exists.

    Example:
        from tenxyte.core import Settings, AuthenticationService

        auth_service = AuthenticationService(settings=settings, user_lookup=my_lookup)
        result = auth_service.authenticate("user@example.com", "password")
        if result.success:
            ...
    """

    def __init__(self, settings: Settings, user_lookup: PasswordUserLookup):
        self.settings = settings
        self.user_lookup = user_lookup
        self.bcrypt_rounds = getattr(settings, "bcrypt_rounds", 12)
        self._dummy_hash: bytes | None = None

    def _get_dummy_hash(self) -> bytes:
        """
        Lazily compute a bcrypt hash with the same cost as real password hashes.

        Cached on the instance: the property that must stay constant-time
        across requests is the *comparison* (bcrypt.checkpw), not the hash
        generation — regenerating a fresh salt per request would just move
        the timing signal elsewhere, not remove it.
        """
        if self._dummy_hash is None:
            self._dummy_hash = bcrypt.hashpw(_DUMMY_PASSWORD, bcrypt.gensalt(rounds=self.bcrypt_rounds))
        return self._dummy_hash

    def _run_dummy_check(self, password: str) -> None:
        """Perform a bcrypt comparison of realistic cost; result is discarded."""
        try:
            bcrypt.checkpw(password.encode("utf-8"), self._get_dummy_hash())
        except Exception:  # noqa: BLE001, S110
            # cost. Logging here would run on every login attempt for a nonexistent account
            # (an expected, frequent case, not an error) and would itself be a side channel.
            pass

    def authenticate(self, identifier: object, password: str) -> AuthResult:
        """
        Verify credentials for `identifier` (email, phone, or adapter-defined key).

        Returns an AuthResult; never raises for invalid credentials.
        """
        user = self.user_lookup.get_by_identifier(identifier)

        if not user:
            # Timing-attack mitigation: run a same-cost bcrypt check even
            # though there is no account, so "no such account" and "wrong
            # password" take a comparable amount of time.
            self._run_dummy_check(password)
            return AuthResult(success=False, error="Invalid credentials", failure_reason="user_not_found")

        if not user.is_active:
            return AuthResult(success=False, error="Account is inactive", failure_reason="account_inactive")

        if user.metadata and user.metadata.get("is_banned"):
            return AuthResult(success=False, error="Account has been banned", failure_reason="account_banned")

        if self.user_lookup.is_account_locked(user.id):
            return AuthResult(
                success=False,
                error="Account has been locked due to too many failed login attempts",
                failure_reason="account_locked",
            )

        if not self.user_lookup.check_password(user.id, password):
            self.user_lookup.record_failed_login(user.id)
            return AuthResult(success=False, error="Invalid credentials", failure_reason="invalid_password")

        return AuthResult(success=True, user=user)
