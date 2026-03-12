import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

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
        
    def is_blacklisted(self, token_jti: str):
        return token_jti in self.blacklist

@pytest.fixture
def settings():
    return Settings(provider=MockSettingsProvider(
        jwt_secret="super-secret-key",
        jwt_algorithm="HS256",
        jwt_access_token_lifetime=3600,
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

