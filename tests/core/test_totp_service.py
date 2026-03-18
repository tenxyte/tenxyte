import os
import pytest
from unittest.mock import patch, MagicMock



from tenxyte.core.totp_service import (
    TOTPService, TOTPUserData, TOTPStorage, CodeReplayProtection,
    InMemoryCodeReplayProtection
)
from tenxyte.core.settings import Settings

class DummyProvider:
    def get(self, name, default=None):
        return default

@pytest.fixture
def settings():
    return Settings(provider=DummyProvider())

class DummyStorage:
    def __init__(self):
        self.data = {}
    
    def save_totp_secret(self, user_id, encrypted_secret):
        if user_id not in self.data:
            self.data[user_id] = TOTPUserData(id=user_id, email="x@y.com")
        self.data[user_id].totp_secret = encrypted_secret
        return True

    def save_backup_codes(self, user_id, hashed_codes):
        if user_id not in self.data:
            self.data[user_id] = TOTPUserData(id=user_id, email="x@y.com")
        self.data[user_id].backup_codes = hashed_codes
        return True
        
    def enable_2fa(self, user_id):
        if user_id in self.data:
            self.data[user_id].is_2fa_enabled = True
        return True

    def disable_2fa(self, user_id):
        if user_id in self.data:
            self.data[user_id].is_2fa_enabled = False
            self.data[user_id].totp_secret = None
        return True

    def load_user_data(self, user_id):
        return self.data.get(user_id)


def test_protocols():
    class DummyS:
        pass
    try:
        TOTPStorage.save_totp_secret(DummyS(), "u", "e")
    except Exception:
        pass
    try:
        TOTPStorage.save_backup_codes(DummyS(), "u", [])
    except Exception:
        pass
    try:
        TOTPStorage.enable_2fa(DummyS(), "u")
    except Exception:
        pass
    try:
        TOTPStorage.disable_2fa(DummyS(), "u")
    except Exception:
        pass
    try:
        TOTPStorage.load_user_data(DummyS(), "u")
    except Exception:
        pass
    try:
        CodeReplayProtection.is_code_used(DummyS(), "u", "c")
    except Exception:
        pass
    try:
        CodeReplayProtection.mark_code_used(DummyS(), "u", "c", 1)
    except Exception:
        pass


def test_totp_user_data():
    u = TOTPUserData("1", "test@example.com")
    assert not u.has_backup_codes()
    u.backup_codes = ["a"]
    assert u.has_backup_codes()


def test_in_memory_replay():
    r = InMemoryCodeReplayProtection()
    assert not r.is_code_used("u", "c")
    r.mark_code_used("u", "c", 10)
    assert r.is_code_used("u", "c")


def test_init_encryption(settings):
    # with key passed directly
    s1 = TOTPService(settings=settings, encryption_key="MTIzNDU2NzgxMjM0NTY3ODEyMzQ1Njc4MTIzNDU2Nzg=")
    assert s1.totp_key is not None

    # with settings providing the key via provider
    class KeyProvider:
        def get(self, name, default=None):
            if name == "TENXYTE_TOTP_ENCRYPTION_KEY":
                return "MTIzNDU2NzgxMjM0NTY3ODEyMzQ1Njc4MTIzNDU2Nzg="
            return default
    
    settings_with_key = Settings(provider=KeyProvider())
    s2 = TOTPService(settings=settings_with_key)
    assert s2.totp_key is not None


def test_encrypt_decrypt_no_key(settings):
    s = TOTPService(settings=settings)  # no key
    assert s._encrypt_secret("abc") == "abc"
    assert s._decrypt_secret(None) is None
    assert s._decrypt_secret("def") == "def"


def test_decrypt_exception(settings):
    s = TOTPService(settings=settings, encryption_key="MTIzNDU2NzgxMjM0NTY3ODEyMzQ1Njc4MTIzNDU2Nzg=")
    # string that cannot be decrypted
    assert s._decrypt_secret("invalid-encrypted-string") is None


def test_generate_methods(settings):
    s = TOTPService(settings=settings)
    sec = s.generate_secret()
    qr = s.generate_qr_code(sec, "test@test.com")
    assert "data:image/png;base64," in qr


def test_verify_code_edge_cases(settings):
    s = TOTPService(settings=settings)
    assert s.verify_code(None, "123") is False
    assert s.verify_code("sec", None) is False

    # exception
    assert s.verify_code("invalid_base32_secret!!!!!!!!", "123456") is False

    # code replay protection blocking
    sec = s.generate_secret()
    code = s.get_totp(sec).now()
    r = InMemoryCodeReplayProtection()
    r.mark_code_used("u", code, 100)
    s.replay_protection = r
    assert s.verify_code(sec, code, user_id="u") is False


def test_backup_code_verification(settings):
    s = TOTPService(settings=settings)
    plain, hashed = s.generate_backup_codes(3)
    
    # Empty
    is_valid, _ = s.verify_backup_code("abc", [])
    assert not is_valid

    # Format correction
    code = plain[0]
    unformatted = code.replace("-", "")
    is_valid, rem = s.verify_backup_code(unformatted, hashed)
    assert is_valid
    assert len(rem) == 2

    # Invalid code
    is_valid, rem = s.verify_backup_code("invalid", rem)
    assert not is_valid
    assert len(rem) == 2


def test_2fa_workflow(settings):
    s = TOTPService(settings=settings, encryption_key="MTIzNDU2NzgxMjM0NTY3ODEyMzQ1Njc4MTIzNDU2Nzg=")
    storage = DummyStorage()
    
    # Setup
    res = s.setup_2fa("u", "e@x.com", storage)
    
    # Confirm
    code = s.get_totp(res.secret).now()
    suk, msg = s.confirm_2fa_setup("u", code, storage)
    assert suk is True
    
    # Confirm again -> already enabled
    suk, msg = s.confirm_2fa_setup("u", code, storage)
    assert suk is False and "already enabled" in msg

    # Confirm not user -> setup not initiated
    suk, msg = s.confirm_2fa_setup("nonexistent", code, storage)
    assert suk is False and "not initiated" in msg


def test_verify_2fa(settings):
    s = TOTPService(settings=settings)
    storage = DummyStorage()
    storage.data["u"] = TOTPUserData("u", "e@t", is_2fa_enabled=False)
    
    # Not enabled -> OK
    suk, msg = s.verify_2fa("u", "123", storage)
    assert suk is True

    # User not found
    suk, msg = s.verify_2fa("none", "123", storage)
    assert suk is False and "not found" in msg

    res = s.setup_2fa("u2", "e@x.com", storage)
    code = s.get_totp(res.secret).now()
    s.confirm_2fa_setup("u2", code, storage)
    
    s.replay_protection._used_codes.clear()

    # Empty code
    suk, msg = s.verify_2fa("u2", None, storage)
    assert suk is False and "required" in msg

    # Valid TOTP
    code = s.get_totp(res.secret).now()
    suk, msg = s.verify_2fa("u2", code, storage)
    assert suk is True

    # Backup code
    bc = res.backup_codes[0]
    suk, msg = s.verify_2fa("u2", bc, storage)
    assert suk is True
    
    # Invalid code
    suk, msg = s.verify_2fa("u2", "000000", storage)
    assert suk is False and "Invalid" in msg


def test_disable_and_regenerate(settings):
    s = TOTPService(settings=settings)
    storage = DummyStorage()
    
    # User not found
    suk, msg = s.disable_2fa("none", "123", storage)
    assert not suk
    suk, _, msg = s.regenerate_backup_codes("none", "123", storage)
    assert not suk

    # Not enabled
    storage.data["u"] = TOTPUserData("u", "e@t", is_2fa_enabled=False)
    suk, msg = s.disable_2fa("u", "123", storage)
    assert not suk
    suk, _, msg = s.regenerate_backup_codes("u", "123", storage)
    assert not suk

    res = s.setup_2fa("u2", "e@x.com", storage)
    code = s.get_totp(res.secret).now()
    s.confirm_2fa_setup("u2", code, storage)

    s.replay_protection._used_codes.clear()

    # Regen failure invalid code
    suk, codes, msg = s.regenerate_backup_codes("u2", "invalid", storage)
    assert not suk

    # Regen success
    code = s.get_totp(res.secret).now()
    suk, codes, msg = s.regenerate_backup_codes("u2", code, storage)
    assert suk
    assert len(codes) > 0

    # Disable invalid code
    suk, msg = s.disable_2fa("u2", "invalid", storage)
    assert not suk

    # Disable with backup code
    bc = codes[0]
    suk, msg = s.disable_2fa("u2", bc, storage)
    assert suk


def test_confirm_decrypt_fail(settings):
    s = TOTPService(settings=settings)
    storage = DummyStorage()
    s.setup_2fa("u", "e", storage)
    storage.data["u"].totp_secret = "invalid_encrypted_data"
    s.totp_key = MagicMock()
    s.totp_key.decrypt.side_effect = Exception("fail")
    suk, msg = s.confirm_2fa_setup("u", "123", storage)
    assert not suk and "Failed" in msg


def test_confirm_invalid_code(settings):
    s = TOTPService(settings=settings)
    storage = DummyStorage()
    s.setup_2fa("u", "e", storage)
    suk, msg = s.confirm_2fa_setup("u", "invalid", storage)
    assert not suk and "Invalid" in msg

