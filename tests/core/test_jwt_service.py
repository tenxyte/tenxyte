import pytest
from datetime import datetime
from typing import Any

from tenxyte.core.jwt_service import JWTService
from tenxyte.core.settings import Settings

class MockSettingsProvider:
    def __init__(self, **kwargs):
        self.data = {f"TENXYTE_{k.upper()}": v for k, v in kwargs.items()}
    def get(self, name, default=None):
        return self.data.get(name, default)

class MockTokenBlacklist:
    def __init__(self):
        self.blacklist = set()
        
    def is_blacklisted(self, jti: str) -> bool:
        return jti in self.blacklist
        
    def blacklist_token(self, jti: str, expires_at: datetime, user_id: str = None, reason: str = "") -> bool:
        self.blacklist.add(jti)
        return True
        
    def is_user_revoked(self, user_id: str, token_iat: datetime = None) -> bool:
        return False
        
    def get(self, key: str):
        return None
        
    def set(self, key: str, value: Any, timeout: int = None):
        return True
        
    def delete(self, key: str):
        return True
        
    def exists(self, key: str):
        return False
        
    def add_to_blacklist(self, token_jti: str, expires_in: int):
        self.blacklist.add(token_jti)
        return True
        
@pytest.fixture
def settings():
    return Settings(provider=MockSettingsProvider(
        jwt_secret_key="super-secret-key",
        jwt_algorithm="HS256",
        jwt_access_token_lifetime=900,
        jwt_refresh_token_lifetime=86400,
        jwt_issuer="test-issuer",
        jwt_audience="test-audience"
    ))

@pytest.fixture
def jwt_service(settings):
    blacklist = MockTokenBlacklist()
    return JWTService(settings, blacklist_service=blacklist)

def test_create_access_token(jwt_service):
    token, jti, expires = jwt_service.generate_access_token(
        user_id="user123",
        application_id="app456"
    )
    assert isinstance(token, str)
    assert len(token) > 0

def test_validate_token(jwt_service):
    # Create
    token, jti, _ = jwt_service.generate_access_token(user_id="user123", application_id="app456")
    
    # Validate
    decoded = jwt_service.decode_token(token)
    assert decoded.is_valid is True
    assert decoded.user_id == "user123"
    assert decoded.type == "access"
    assert decoded.app_id == "app456"

def test_validate_invalid_token(jwt_service):
    decoded = jwt_service.decode_token("invalid.token.here")
    assert decoded is None or decoded.is_valid is False

def test_blacklist_token(jwt_service):
    token, jti, _ = jwt_service.generate_access_token(user_id="user123", application_id="app456")
    decoded = jwt_service.decode_token(token)
    assert decoded.is_valid is True
    
    jwt_service.blacklist_token(token, user_id="user123")
    
    # Validate should now say blacklisted
    decoded_after = jwt_service.decode_token(token)
    assert decoded_after.is_valid is False
    assert decoded_after.is_blacklisted is True


def test_custom_lifetime_overrides_default(jwt_service):
    """custom_lifetime should override the configured access token lifetime."""
    from datetime import timedelta, timezone

    custom = timedelta(minutes=15)
    token, jti, expires = jwt_service.generate_access_token(
        user_id="admin1",
        application_id="app456",
        custom_lifetime=custom,
    )

    now = datetime.now(timezone.utc)
    delta = (expires - now).total_seconds()
    # Bootstrap token must be ~15 minutes (<= 900 seconds), well under the
    # default 900s configured here only by coincidence; assert it tracks custom.
    assert 0 < delta <= 900
    # Within a small tolerance of 15 minutes
    assert abs(delta - 900) < 10


def test_custom_lifetime_shorter_than_default(settings):
    """A short custom_lifetime must produce a shorter-lived token than default."""
    from datetime import timedelta, timezone

    # Configure a long default lifetime so the override is clearly distinguishable
    long_settings = Settings(provider=MockSettingsProvider(
        jwt_secret_key="super-secret-key",
        jwt_algorithm="HS256",
        jwt_access_token_lifetime=3600,
        jwt_refresh_token_lifetime=86400,
        jwt_issuer="test-issuer",
        jwt_audience="test-audience",
    ))
    service = JWTService(long_settings, blacklist_service=MockTokenBlacklist())

    _, _, default_expires = service.generate_access_token(user_id="u", application_id="a")
    _, _, custom_expires = service.generate_access_token(
        user_id="u", application_id="a", custom_lifetime=timedelta(minutes=15)
    )

    assert custom_expires < default_expires
    now = datetime.now(timezone.utc)
    assert (custom_expires - now).total_seconds() <= 900


def test_default_lifetime_unchanged_when_no_custom_lifetime(jwt_service):
    """Preservation: omitting custom_lifetime keeps the configured lifetime."""
    from datetime import timezone

    token, jti, expires = jwt_service.generate_access_token(
        user_id="user123", application_id="app456"
    )
    now = datetime.now(timezone.utc)
    delta = (expires - now).total_seconds()
    # Default configured lifetime is 900 seconds in the fixture
    assert abs(delta - 900) < 10


def test_scope_claim_flows_through_extra_claims(jwt_service):
    """The 'scope' claim in extra_claims must be embedded in the token payload."""
    token, jti, _ = jwt_service.generate_access_token(
        user_id="admin1",
        application_id="app456",
        extra_claims={"scope": "2fa_setup_only"},
    )

    decoded = jwt_service.decode_token(token)
    assert decoded.is_valid is True
    assert decoded.claims.get("scope") == "2fa_setup_only"


def test_bootstrap_token_scope_and_lifetime_together(jwt_service):
    """Bootstrap case: scope claim + 15-minute lifetime in a single call."""
    from datetime import timedelta, timezone

    token, jti, expires = jwt_service.generate_access_token(
        user_id="admin1",
        application_id="app456",
        extra_claims={"scope": "2fa_setup_only"},
        custom_lifetime=timedelta(minutes=15),
    )

    decoded = jwt_service.decode_token(token)
    assert decoded.claims.get("scope") == "2fa_setup_only"
    now = datetime.now(timezone.utc)
    assert (expires - now).total_seconds() <= 900


def test_scope_claim_omitted_when_not_provided(jwt_service):
    """Preservation: no scope claim appears when extra_claims is not supplied."""
    token, jti, _ = jwt_service.generate_access_token(
        user_id="user123", application_id="app456"
    )
    decoded = jwt_service.decode_token(token)
    assert "scope" not in decoded.claims
