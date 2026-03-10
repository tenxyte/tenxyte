import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from tenxyte.core.magic_link_service import MagicLinkService, MagicLinkRepository, MagicLinkToken
from tenxyte.core.settings import Settings
from tenxyte.core.schemas import UserResponse

class MockSettingsProvider:
    def __init__(self, **kwargs):
        self.data = {f"TENXYTE_{k.upper()}": v for k, v in kwargs.items()}
    def get(self, name, default=None):
        return self.data.get(name, default)

class MockEmailService:
    def __init__(self):
        self.sent_emails = []
        
    def send_magic_link(self, to_email: str, token: str, magic_url: Optional[str] = None, **kwargs):
        self.sent_emails.append((to_email, magic_url))
        return True

class MockMagicLinkRepository(MagicLinkRepository):
    def __init__(self):
        self.tokens = {}
        
    def create(self, token_hash: str, user_id: str, email: str, application_id: Optional[str] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None, expiry_minutes: int = 15) -> MagicLinkToken:
        expires = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        token = MagicLinkToken(id="id_" + token_hash, token=token_hash, user_id=user_id, email=email, application_id=application_id, ip_address=ip_address, user_agent=user_agent, created_at=datetime.now(timezone.utc), expires_at=expires)
        self.tokens[token_hash] = token
        return token
        
    def get_by_token(self, token: str) -> Optional[MagicLinkToken]:
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return self.tokens.get(token_hash)
        
    def consume(self, token_id: str) -> bool:
        for t in self.tokens.values():
            if t.id == token_id:
                t.is_used = True
                return True
        return False
        
    def invalidate_user_tokens(self, user_id: str, application_id: Optional[str] = None) -> int:
        count = 0
        for t in self.tokens.values():
            if t.user_id == user_id and not t.is_used:
                t.is_used = True
                count += 1
        return count

class MockUserLookup:
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        if email == "test@example.com":
            return {"id": "user123", "email": email, "first_name": "Test"}
        return None
        
    def is_active(self, user_id: str) -> bool:
        return True
        
    def is_locked(self, user_id: str) -> bool:
        return False

@pytest.fixture
def settings():
    return Settings(provider=MockSettingsProvider(
        secret_key="super-secret",
        magic_link_lifetime=15,
        frontend_url="http://localhost:3000",
        magic_link_path="/verify-magic-link"
    ))

@pytest.fixture
def magic_link_service(settings):
    email = MockEmailService()
    repo = MockMagicLinkRepository()
    lookup = MockUserLookup()
    return MagicLinkService(settings, repo, lookup, email)

@pytest.fixture
def test_user():
    return UserResponse(
        id="user123",
        email="test@example.com",
    )

def test_generate_token(magic_link_service, test_user):
    success, err = magic_link_service.request_magic_link(email="test@example.com", validation_url="http://localhost:3000/verify-magic-link")
    
    assert success is True
    assert len(magic_link_service.email_service.sent_emails) == 1
    
    email_to, url = magic_link_service.email_service.sent_emails[0]
    assert email_to == "test@example.com"
    assert url.startswith("http://localhost:3000/verify-magic-link")
    assert "token=" in url

def test_verify_token(magic_link_service, test_user):
    magic_link_service.request_magic_link(email="test@example.com", validation_url="http://localhost:3000/verify")
    # Grab the generated raw token from the URL sent
    url = magic_link_service.email_service.sent_emails[0][1]
    raw_token = url.split("token=")[1]
    
    res = magic_link_service.verify_magic_link(raw_token, require_same_device=False)
    
    assert res.success is True
    assert res.user_id == "user123"

def test_verify_invalid_token(magic_link_service):
    res = magic_link_service.verify_magic_link("invalid_token", require_same_device=False)
    assert res.success is False

def test_verify_used_token(magic_link_service, test_user):
    magic_link_service.request_magic_link(email="test@example.com", validation_url="http://localhost:3000/verify")
    url = magic_link_service.email_service.sent_emails[0][1]
    raw_token = url.split("token=")[1]
    
    # First time verify
    res1 = magic_link_service.verify_magic_link(raw_token, require_same_device=False)
    assert res1.success is True
    
    # Second time verify should fail
    res2 = magic_link_service.verify_magic_link(raw_token, require_same_device=False)
    assert res2.success is False

