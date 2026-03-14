import pytest
from tenxyte.core.totp_service import TOTPService
from tenxyte.core.settings import Settings
from tenxyte.core.schemas import UserResponse, MFAType
import pyotp

class MockSettingsProvider:
    def __init__(self, **kwargs):
        self.data = {f"TENXYTE_{k.upper()}": v for k, v in kwargs.items()}
    def get(self, name, default=None):
        return self.data.get(name, default)

@pytest.fixture
def settings():
    return Settings(provider=MockSettingsProvider(
        secret_key="super-secret",
        totp_issuer="Tenxyte Test",
        totp_digits=6,
        totp_interval=30
    ))

@pytest.fixture
def totp_service(settings):
    return TOTPService(settings)

@pytest.fixture
def test_user():
    return UserResponse(
        id="user123",
        email="test@example.com",
    )

def test_generate_secret(totp_service):
    secret = totp_service.generate_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 16

def test_get_provisioning_uri(totp_service, test_user):
    secret = totp_service.generate_secret()
    uri = totp_service.get_provisioning_uri(secret, email="test@example.com")
    
    assert "otpauth://totp/" in uri
    assert "test%40example.com" in uri

def test_verify_totp(totp_service):
    secret = totp_service.generate_secret()
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    
    assert totp_service.verify_code(secret, valid_code) is True
    assert totp_service.verify_code(secret, "000000") is False

def test_generate_backup_codes(totp_service):
    plain_codes, hashed_codes = totp_service.generate_backup_codes(count=5)
    
    assert len(plain_codes) == 5
    assert len(hashed_codes) == 5
    for code in plain_codes:
        assert isinstance(code, str)

