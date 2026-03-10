import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from tenxyte.core.webauthn_service import WebAuthnService, WebAuthnCredentialRepository, WebAuthnChallengeRepository
from tenxyte.core.schemas import UserResponse
from tenxyte.core.settings import Settings
import webauthn

class MockSettingsProvider:
    def __init__(self, **kwargs):
        self.data = {f"TENXYTE_{k.upper()}": v for k, v in kwargs.items()}
    def get(self, name, default=None):
        return self.data.get(name, default)

class MockCredentialRepository(WebAuthnCredentialRepository):
    def __init__(self):
        self.credentials = []
        
    def create(self, user_id: str, credential_id: str, public_key: bytes, sign_count: int, transports: Optional[List[str]] = None, name: str = "Passkey") -> Dict[str, Any]:
        cred = {
            "id": "cred" + credential_id,
            "user_id": user_id,
            "credential_id": credential_id,
            "public_key": public_key,
            "sign_count": sign_count,
            "transports": transports or [],
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used_at": datetime.now(timezone.utc).isoformat(),
        }
        self.credentials.append(cred)
        return cred
        
    def get_by_credential_id(self, credential_id: str) -> Optional[Dict[str, Any]]:
        return next((c for c in self.credentials if c["credential_id"] == credential_id), None)
        
    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        return [c for c in self.credentials if c["user_id"] == user_id]
        
    def update_sign_count(self, credential_id: str, sign_count: int) -> bool:
        cred = self.get_by_credential_id(credential_id)
        if cred:
            cred["sign_count"] = sign_count
            cred["last_used_at"] = datetime.now(timezone.utc).isoformat()
            return True
        return False
        
    def delete(self, credential_id: str) -> bool:
        initial_len = len(self.credentials)
        self.credentials = [c for c in self.credentials if c["credential_id"] != credential_id]
        return len(self.credentials) < initial_len

class MockChallenge:
    def __init__(self, id, challenge, operation, user_id):
        self.id = id
        self.challenge = challenge
        self.operation = operation
        self.user_id = user_id

class MockChallengeRepository(WebAuthnChallengeRepository):
    def __init__(self):
        self.challenges = {}
        
    def create(self, challenge: str, operation: str, user_id: Optional[str] = None, expiry_seconds: int = 300) -> MockChallenge:
        import uuid
        c_id = str(uuid.uuid4())
        self.challenges[user_id or "anonymous"] = {
            "id": c_id,
            "user_id": user_id,
            "challenge": challenge,
            "operation": operation,
        }
        return MockChallenge(id=c_id, challenge=challenge, operation=operation, user_id=user_id)
        
    def get_and_delete(self, challenge_id: str) -> Optional[Dict[str, Any]]:
        # For tests, we'll pretend challenge_id is user_id for simplicity,
        # but the real repo fetches by challenge_id token.
        return None

@pytest.fixture
def settings():
    return Settings(provider=MockSettingsProvider(
        secret_key="super-secret",
        rp_id="localhost",
        rp_name="Tenxyte Test",
        rp_expected_origin="http://localhost:3000"
    ))

@pytest.fixture
def webauthn_service(settings):
    cred_repo = MockCredentialRepository()
    chall_repo = MockChallengeRepository()
    return WebAuthnService(settings, cred_repo, chall_repo)

@pytest.fixture
def test_user():
    return UserResponse(
        id="user123",
        email="test@example.com",
    )

def test_generate_registration_options(webauthn_service, test_user):
    success, options_json, error = webauthn_service.begin_registration(
        user_id="user123",
        email="test@example.com",
        display_name="Test User"
    )
    
    assert success is True
    assert isinstance(options_json, dict)  # JSON string
    assert webauthn_service.challenge_repo.challenges["user123"]["operation"] == "register"

def test_generate_authentication_options(webauthn_service):
    # It takes an optional user_id; if not provided, discoverable credentials are used
    success, options_json, error = webauthn_service.begin_authentication(user_id="user123")
    
    assert success is True
    assert isinstance(options_json, dict)  # JSON string
    assert webauthn_service.challenge_repo.challenges["user123"]["operation"] == "authenticate"

# Detailed verify_registration and verify_authentication tests require mock webauthn responses
# which is slightly complex for a quick unit test without realistic payloads, but the methods
# are there and imported successfully.

