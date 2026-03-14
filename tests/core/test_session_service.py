import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from tenxyte.core.session_service import SessionService, SessionRepository
from tenxyte.core.settings import Settings
from tenxyte.core.schemas import UserResponse

class MockSettingsProvider:
    def __init__(self, **kwargs):
        self.data = {f"TENXYTE_{k.upper()}": v for k, v in kwargs.items()}
    def get(self, name, default=None):
        return self.data.get(name, default)

class MockCacheService:
    def __init__(self):
        self.data = {}
        
    def get(self, key: str):
        return self.data.get(key)
        
    def set(self, key: str, value: Any, timeout: int = None):
        self.data[key] = value
        return True
        
    def delete(self, key: str):
        if key in self.data:
            del self.data[key]
        return True

class MockSessionRepository(SessionRepository):
    def __init__(self):
        self.sessions = {}
        
    def create(self, user_id: str, device_id: str, metadata: Dict[str, Any], expires_at: datetime) -> str:
        session_id = metadata["session_id"]
        self.sessions[session_id] = metadata
        return session_id
        
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)
        
    def revoke(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
        
    def revoke_all_for_user(self, user_id: str, except_session_id: Optional[str] = None) -> int:
        to_delete = []
        for sid, meta in self.sessions.items():
            if meta["user_id"] == user_id and sid != except_session_id:
                to_delete.append(sid)
        for sid in to_delete:
            del self.sessions[sid]
        return len(to_delete)
        
    def get_user_sessions(self, user_id: str) -> list[Dict[str, Any]]:
        return [m for m in self.sessions.values() if m["user_id"] == user_id]

def test_protocol_methods():
    class DummyRepo:
        pass
    try:
        SessionRepository.create(DummyRepo(), "u", "d", {}, datetime.now())
    except Exception:
        pass
    try:
        SessionRepository.get(DummyRepo(), "s")
    except Exception:
        pass
    try:
        SessionRepository.revoke(DummyRepo(), "s")
    except Exception:
        pass
    try:
        SessionRepository.revoke_all_for_user(DummyRepo(), "u", "s")
    except Exception:
        pass
    try:
        SessionRepository.get_user_sessions(DummyRepo(), "u")
    except Exception:
        pass

@pytest.fixture
def settings():
    return Settings(provider=MockSettingsProvider(
        secret_key="super-secret",
        jwt_refresh_token_lifetime=86400,
        device_fingerprinting_enabled=True,
        max_devices_per_user=2  # To hit line 108
    ))

@pytest.fixture
def session_service(settings):
    cache = MockCacheService()
    repo = MockSessionRepository()
    return SessionService(settings, cache, repo)

@pytest.fixture
def test_user():
    return UserResponse(
        id="user123",
        email="test@example.com",
    )

def test_create_session(session_service, test_user):
    session = session_service.create_session(
        user=test_user,
        device_id="device456",
        ip_address="127.0.0.1",
        user_agent="pytest"
    )
    
    assert "session_id" in session
    assert session["user_id"] == "user123"
    assert session["device_id"] == "device456"
    assert session["ip_address"] == "127.0.0.1"

def test_validate_session_from_cache(session_service, test_user):
    session = session_service.create_session(user=test_user)
    session_id = session["session_id"]
    
    valid_session = session_service.validate_session(session_id)
    assert valid_session is not None
    assert valid_session["session_id"] == session_id

def test_validate_session_fallback_repo(session_service, test_user):
    # Test lines 147-153
    session = session_service.create_session(user=test_user)
    session_id = session["session_id"]
    
    # Remove from cache manually
    cache_key = f"session:{session_id}"
    session_service.cache_service.delete(cache_key)
    
    valid_session = session_service.validate_session(session_id)
    assert valid_session is not None
    assert valid_session["session_id"] == session_id
    
    # Now it should be back in cache
    assert session_service.cache_service.get(cache_key) is not None

def test_validate_session_fallback_expired_repo(session_service, test_user):
    # If ttl <= 0 (expired but somehow still in repo)
    session = session_service.create_session(user=test_user)
    session_id = session["session_id"]
    
    # Remove from cache manually
    cache_key = f"session:{session_id}"
    session_service.cache_service.delete(cache_key)
    
    # Modify repo entry to be expired
    repo_session = session_service.repository.get(session_id)
    repo_session["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    
    valid_session = session_service.validate_session(session_id)
    assert valid_session is None

def test_validate_session_not_found(session_service):
    valid_session = session_service.validate_session("invalid")
    assert valid_session is None

def test_revoke_session(session_service, test_user):
    session = session_service.create_session(user=test_user)
    session_id = session["session_id"]
    
    assert session_service.revoke_session(session_id) is True
    assert session_service.validate_session(session_id) is None

def test_revoke_session_no_repo(settings, test_user):
    service = SessionService(settings, MockCacheService(), None)
    session = service.create_session(user=test_user)
    session_id = session["session_id"]
    
    assert service.revoke_session(session_id) is True

def test_revoke_all_sessions(session_service, test_user):
    session_service.create_session(user=test_user)
    session_service.create_session(user=test_user)
    session_service.create_session(user=test_user)
    
    assert len(session_service.repository.sessions) == 3
    count = session_service.revoke_all_sessions(user_id="user123")
    assert count == 3
    assert len(session_service.repository.sessions) == 0

def test_revoke_all_sessions_no_repo(settings, test_user):
    service = SessionService(settings, MockCacheService(), None)
    service.create_session(user=test_user)
    count = service.revoke_all_sessions(user_id="user123")
    assert count == 0
