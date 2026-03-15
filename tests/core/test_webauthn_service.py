import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from tenxyte.core.webauthn_service import (
    WebAuthnService, WebAuthnCredentialRepository, WebAuthnChallengeRepository,
    WebAuthnChallenge, WebAuthnCredential
)
from tenxyte.core.settings import Settings

class DummyProvider:
    def get(self, name, default=None):
        if name == "TENXYTE_WEBAUTHN_RP_ID":
            return "localhost"
        return default

@pytest.fixture
def settings():
    return Settings(provider=DummyProvider())

def test_challenge_is_valid():
    now = datetime.now(timezone.utc)
    # Valid
    c1 = WebAuthnChallenge("1", "chal", "register", expires_at=now + timedelta(minutes=5))
    assert c1.is_valid()
    # Consumed
    c2 = WebAuthnChallenge("1", "chal", "register", consumed=True)
    assert not c2.is_valid()
    # Expired
    c3 = WebAuthnChallenge("1", "chal", "register", expires_at=now - timedelta(minutes=5))
    assert not c3.is_valid()

def test_protocols():
    class DummyCRepo:
        pass
    class DummyChRepo:
        pass
    
    try:
        WebAuthnCredentialRepository.get_by_credential_id(DummyCRepo(), "id")
    except Exception:
        pass
    try:
        WebAuthnCredentialRepository.list_by_user(DummyCRepo(), "id")
    except Exception:
        pass
    try:
        WebAuthnCredentialRepository.create(DummyCRepo(), None)
    except Exception:
        pass
    try:
        WebAuthnCredentialRepository.update_sign_count(DummyCRepo(), "id", 1)
    except Exception:
        pass
    try:
        WebAuthnCredentialRepository.delete(DummyCRepo(), "id", "uid")
    except Exception:
        pass
    try:
        WebAuthnChallengeRepository.create(DummyChRepo(), "c", "o")
    except Exception:
        pass
    try:
        WebAuthnChallengeRepository.get_by_id(DummyChRepo(), "id")
    except Exception:
        pass
    try:
        WebAuthnChallengeRepository.consume(DummyChRepo(), "id")
    except Exception:
        pass


class MockChRepo:
    def __init__(self):
        self.db = {}
    def create(self, challenge, operation, user_id=None, expiry_seconds=300):
        c = WebAuthnChallenge("cid", challenge, operation, user_id, expires_at=datetime.now(timezone.utc)+timedelta(seconds=expiry_seconds))
        self.db["cid"] = c
        return c
    def get_by_id(self, challenge_id):
        return self.db.get(challenge_id)
    def consume(self, challenge_id):
        if challenge_id in self.db:
            self.db[challenge_id].consumed = True

class MockCRepo:
    def __init__(self):
        self.db = []
    def get_by_credential_id(self, credential_id):
        for c in self.db:
            if c.credential_id == credential_id:
                return c
        return None
    def list_by_user(self, user_id):
        return [c for c in self.db if c.user_id == user_id]
    def create(self, credential):
        credential.id = "db_1"
        self.db.append(credential)
        return credential
    def update_sign_count(self, credential_id, new_count):
        for c in self.db:
            if c.id == credential_id:
                c.sign_count = new_count
        return True
    def delete(self, credential_id, user_id):
        initial = len(self.db)
        self.db = [c for c in self.db if not (c.credential_id == credential_id and c.user_id == user_id)]
        return len(self.db) < initial

@pytest.fixture
def service(settings):
    return WebAuthnService(settings, MockCRepo(), MockChRepo())


def test_get_origin(service):
    assert service._get_origin() == "http://localhost"
    service.rp_id = "example.com"
    assert service._get_origin() == "https://example.com"


def test_disabled_service(service):
    service.enabled = False
    suk, opt, err = service.begin_registration("u", "e")
    assert not suk and "enabled" in err
    
    res = service.complete_registration("u", {}, "cid")
    assert not res.success and "enabled" in res.error
    
    suk, opt, err = service.begin_authentication("u")
    assert not suk and "enabled" in err
    
    res = service.complete_authentication({}, "cid")
    assert not res.success and "enabled" in res.error

@patch("tenxyte.core.webauthn_service._get_webauthn")
def test_begin_registration(mock_get_webauthn, service):
    mock_webauthn = MagicMock()
    mock_webauthn.options_to_json.return_value = '{"opt": 1}'
    mock_get_webauthn.return_value = mock_webauthn
    
    # Success
    suk, opt, err = service.begin_registration("u", "e", "d")
    assert suk
    assert opt["options"] == '{"opt": 1}'
    
    # Exception
    mock_webauthn.generate_registration_options.side_effect = Exception("err")
    suk, opt, err = service.begin_registration("u", "e", "d")
    assert not suk and "error" in err

@patch("tenxyte.core.webauthn_service._get_webauthn")
def test_complete_registration(mock_get_webauthn, service):
    mock_webauthn = MagicMock()
    mock_get_webauthn.return_value = mock_webauthn
    
    # missing challenge
    res = service.complete_registration("u", {}, "invalid")
    assert not res.success and "Invalid" in res.error
    
    # consumed challenge
    c = service.challenge_repo.create("chal", "r", "u")
    c.consumed = True
    res = service.complete_registration("u", {}, "cid")
    assert not res.success and "expired" in res.error
    
    # mismatch user
    c.consumed = False
    c.user_id = "other"
    res = service.complete_registration("u", {}, "cid")
    assert not res.success and "match" in res.error
    
    # verification exception
    c.user_id = "u"
    mock_webauthn.verify_registration_response.side_effect = Exception("fail")
    res = service.complete_registration("u", {}, "cid")
    assert not res.success and "failed" in res.error
    
    # success
    mock_verify = MagicMock()
    mock_verify.credential_id = b"cid_bytes"
    mock_verify.credential_public_key = b"pub"
    mock_verify.sign_count = 0
    mock_verify.aaguid = "aaguid"
    mock_webauthn.verify_registration_response.side_effect = None
    mock_webauthn.verify_registration_response.return_value = mock_verify
    
    res = service.complete_registration("u", {}, "cid", "device_n")
    assert res.success
    assert res.credential.credential_id == "cid_bytes"
    assert res.credential.public_key == "pub"
    assert res.credential.user_id == "u"

@patch("tenxyte.core.webauthn_service._get_webauthn")
def test_begin_authentication(mock_get_webauthn, service):
    mock_webauthn = MagicMock()
    mock_webauthn.options_to_json.return_value = '{"opt": 2}'
    mock_get_webauthn.return_value = mock_webauthn
    
    # success with user id
    service.credential_repo.create(WebAuthnCredential(id="", credential_id="c_id", public_key="k", user_id="u"))
    suk, opt, err = service.begin_authentication("u")
    assert suk
    assert opt["options"] == '{"opt": 2}'
    
    # success without user id
    suk, opt, err = service.begin_authentication()
    assert suk
    
    # exception
    mock_webauthn.generate_authentication_options.side_effect = Exception("err")
    suk, opt, err = service.begin_authentication("u")
    assert not suk and "error" in err

@patch("tenxyte.core.webauthn_service._get_webauthn")
def test_complete_authentication(mock_get_webauthn, service):
    mock_webauthn = MagicMock()
    mock_get_webauthn.return_value = mock_webauthn
    
    # missing challenge
    res = service.complete_authentication({}, "invalid")
    assert not res.success and "Invalid" in res.error
    
    # invalid challenge
    c = service.challenge_repo.create("chal", "a")
    c.consumed = True
    res = service.complete_authentication({}, "cid")
    assert not res.success and "expired" in res.error
    
    # credential not found
    c.consumed = False
    res = service.complete_authentication({"id": "unknown"}, "cid")
    assert not res.success and "Unknown" in res.error
    
    # verification exception
    service.credential_repo.create(WebAuthnCredential(id="db_1", credential_id="known", public_key="k", user_id="u"))
    mock_webauthn.verify_authentication_response.side_effect = Exception("fail")
    res = service.complete_authentication({"id": "known"}, "cid")
    assert not res.success and "failed" in res.error
    
    # success
    mock_verify = MagicMock()
    mock_verify.new_sign_count = 5
    mock_webauthn.verify_authentication_response.side_effect = None
    mock_webauthn.verify_authentication_response.return_value = mock_verify
    res = service.complete_authentication({"id": "known"}, "cid")
    assert res.success
    assert res.user_id == "u"
    
def test_manage_credentials(service):
    service.credential_repo.create(WebAuthnCredential(id="db_1", credential_id="known", public_key="k", user_id="u"))
    creds = service.list_credentials("u")
    assert len(creds) == 1
    assert "device_name" in creds[0]
    
    suk, err = service.delete_credential("u", "known")
    assert suk
    suk, err = service.delete_credential("u", "unknown")
    assert not suk

def test_get_webauthn_import_error():
    from tenxyte.core.webauthn_service import _get_webauthn
    with patch.dict("sys.modules", {"webauthn": None}):
        with pytest.raises(ImportError):
            _get_webauthn()

