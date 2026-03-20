"""
Async coverage tests for:
  - core/totp_service.py (lines 133, 136, 386-417, 454-470, 513-539, 581-611, 654-684, 722-745)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from tenxyte.core.totp_service import (
    TOTPService,
    TOTPUserData,
    TOTPStorage,
    InMemoryCodeReplayProtection,
)
from tenxyte.core.settings import Settings


# ─── Helpers ─────────────────────────────────────────────────────────────────

class DummyProvider:
    def get(self, name, default=None):
        return default


@pytest.fixture
def settings():
    return Settings(provider=DummyProvider())


@pytest.fixture
def service(settings):
    return TOTPService(settings=settings)


class SyncStorage:
    def __init__(self):
        self.data = {}

    def save_totp_secret(self, user_id, enc_secret):
        if user_id not in self.data:
            self.data[user_id] = TOTPUserData(id=user_id, email="u@e.com")
        self.data[user_id].totp_secret = enc_secret
        return True

    def save_backup_codes(self, user_id, codes):
        if user_id not in self.data:
            self.data[user_id] = TOTPUserData(id=user_id, email="u@e.com")
        self.data[user_id].backup_codes = codes
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


class AsyncStorage(SyncStorage):
    async def save_totp_secret_async(self, user_id, enc_secret):
        return self.save_totp_secret(user_id, enc_secret)

    async def save_backup_codes_async(self, user_id, codes):
        return self.save_backup_codes(user_id, codes)

    async def enable_2fa_async(self, user_id):
        return self.enable_2fa(user_id)

    async def disable_2fa_async(self, user_id):
        return self.disable_2fa(user_id)

    async def load_user_data_async(self, user_id):
        return self.load_user_data(user_id)


# ─── InMemoryCodeReplayProtection async stubs (lines 133, 136) ───────────────

class TestCodeReplayProtectionAsync:
    @pytest.mark.anyio
    async def test_is_code_used_async(self):
        """Line 133."""
        prot = InMemoryCodeReplayProtection()
        assert await prot.is_code_used_async("u1", "123456") is False
        prot.mark_code_used("u1", "123456", 60)
        assert await prot.is_code_used_async("u1", "123456") is True

    @pytest.mark.anyio
    async def test_mark_code_used_async(self):
        """Line 136."""
        prot = InMemoryCodeReplayProtection()
        result = await prot.mark_code_used_async("u1", "999999", 60)
        assert result is True
        assert await prot.is_code_used_async("u1", "999999") is True


# ─── TOTPService.verify_code_async (lines 386-417) ───────────────────────────

class TestVerifyCodeAsync:
    @pytest.mark.anyio
    async def test_verify_code_async_valid(self, service):
        """Lines 402-413: valid code."""
        secret = service.generate_secret()
        import pyotp
        code = pyotp.TOTP(secret).now()
        result = await service.verify_code_async(secret, code, user_id="u1")
        assert result is True

    @pytest.mark.anyio
    async def test_verify_code_async_empty(self, service):
        """Lines 388-389: empty code -> False."""
        result = await service.verify_code_async("secret", "", user_id="u1")
        assert result is False

    @pytest.mark.anyio
    async def test_verify_code_async_invalid(self, service):
        """Lines 402-413: wrong code -> False."""
        secret = service.generate_secret()
        result = await service.verify_code_async(secret, "000000", user_id="u1")
        assert result is False

    @pytest.mark.anyio
    async def test_verify_code_async_replay_prevention(self, service):
        """Lines 391-400: replay prevention via async replay protection."""
        secret = service.generate_secret()
        import pyotp
        code = pyotp.TOTP(secret).now()
        # First use succeeds
        ok1 = await service.verify_code_async(secret, code, user_id="replay-test")
        # Repeat should fail (replay)
        ok2 = await service.verify_code_async(secret, code, user_id="replay-test")
        assert ok1 is True
        assert ok2 is False

    @pytest.mark.anyio
    async def test_verify_code_async_no_user_id(self, service):
        """Lines 386-413: no user_id skips replay check."""
        secret = service.generate_secret()
        import pyotp
        code = pyotp.TOTP(secret).now()
        result = await service.verify_code_async(secret, code)
        assert result is True

    @pytest.mark.anyio
    async def test_verify_code_async_exception_path(self, service):
        """Lines 415-417."""
        from unittest.mock import patch
        with patch.object(service, "get_totp", side_effect=Exception("Explosion")):
            result = await service.verify_code_async("secret", "123456")
        assert result is False

    @pytest.mark.anyio
    async def test_verify_code_async_replay_fallback(self, service):
        """Lines 396, 411: fallback to sync replay protection."""
        class RealSyncReplay:
            def __init__(self): self.codes = set()
            def is_code_used(self, u, c): return c in self.codes
            def mark_code_used(self, u, c, t): self.codes.add(c)
        
        service.replay_protection = RealSyncReplay()
        secret = service.generate_secret()
        import pyotp
        code = pyotp.TOTP(secret).now()
        
        ok1 = await service.verify_code_async(secret, code, user_id="sync-u")
        assert ok1 is True
        ok2 = await service.verify_code_async(secret, code, user_id="sync-u")
        assert ok2 is False

# ─── TOTPService.setup_2fa_async (lines 454-470) ─────────────────────────────

class TestSetup2FAAsync:
    @pytest.mark.anyio
    async def test_setup_2fa_async_with_async_storage(self, service):
        """Lines 457-468: async storage methods called."""
        storage = AsyncStorage()
        result = await service.setup_2fa_async("u1", "u@e.com", storage)
        assert result.secret is not None
        assert result.qr_code is not None
        assert len(result.backup_codes) > 0

    @pytest.mark.anyio
    async def test_setup_2fa_async_with_sync_storage(self, service):
        """Lines 459-460: sync storage via to_thread."""
        storage = SyncStorage()
        result = await service.setup_2fa_async("u2", "u@e.com", storage)
        assert result.secret is not None


# ─── TOTPService.confirm_2fa_setup_async (lines 513-539) ─────────────────────

class TestConfirm2FAAsync:
    @pytest.mark.anyio
    async def test_confirm_2fa_setup_async_success(self, service):
        """Lines 513-539: confirm with valid code."""
        storage = AsyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        import pyotp
        secret = service._decrypt_secret(storage.data["u1"].totp_secret)
        code = pyotp.TOTP(secret).now()
        ok, err = await service.confirm_2fa_setup_async("u1", code, storage)
        assert ok is True

    @pytest.mark.anyio
    async def test_confirm_2fa_setup_async_no_data(self, service):
        """Lines 518-519: no setup initiated."""
        storage = AsyncStorage()
        ok, err = await service.confirm_2fa_setup_async("unknown", "123456", storage)
        assert ok is False
        assert "setup" in err

    @pytest.mark.anyio
    async def test_confirm_2fa_setup_async_already_enabled(self, service):
        """Lines 521-522: already enabled."""
        storage = SyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        ok, err = await service.confirm_2fa_setup_async("u1", "000000", storage)
        assert ok is False
        assert "already" in err

    @pytest.mark.anyio
    async def test_confirm_2fa_setup_async_invalid_code(self, service):
        """Lines 529-530: invalid code."""
        storage = AsyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        ok, err = await service.confirm_2fa_setup_async("u1", "000000", storage)
        assert ok is False

    @pytest.mark.anyio
    async def test_confirm_2fa_setup_async_decryption_fail(self, service):
        """Line 526: decryption failure."""
        storage = AsyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        from unittest.mock import patch
        with patch.object(service, "_decrypt_secret", return_value=None):
            ok, err = await service.confirm_2fa_setup_async("u1", "123456", storage)
        assert ok is False
        assert "decrypt" in err

    @pytest.mark.anyio
    async def test_confirm_2fa_setup_async_sync_enable_fallback(self, service):
        """Line 535: fallback to sync enable_2fa."""
        storage = SyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        import pyotp
        secret = service._decrypt_secret(storage.data["u1"].totp_secret)
        code = pyotp.TOTP(secret).now()
        ok, err = await service.confirm_2fa_setup_async("u1", code, storage)
        assert ok is True
        assert storage.data["u1"].is_2fa_enabled is True

# ─── TOTPService.verify_2fa_async (lines 581-611) ────────────────────────────

class TestVerify2FAAsync:
    @pytest.mark.anyio
    async def test_verify_2fa_async_success(self, service):
        """Lines 581-599: valid TOTP code."""
        storage = AsyncStorage()
        setup = await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        import pyotp
        secret = service._decrypt_secret(storage.data["u1"].totp_secret)
        code = pyotp.TOTP(secret).now()
        ok, err = await service.verify_2fa_async("u1", code, storage)
        assert ok is True

    @pytest.mark.anyio
    async def test_verify_2fa_async_not_enabled(self, service):
        """Lines 589-590: 2FA not enabled -> True."""
        storage = AsyncStorage()
        storage.data["u1"] = TOTPUserData(id="u1", email="u@e.com")
        ok, err = await service.verify_2fa_async("u1", "anything", storage)
        assert ok is True

    @pytest.mark.anyio
    async def test_verify_2fa_async_no_user(self, service):
        """Lines 586-587: user not found."""
        storage = AsyncStorage()
        ok, err = await service.verify_2fa_async("ghost", "code", storage)
        assert ok is False
        assert "not found" in err

    @pytest.mark.anyio
    async def test_verify_2fa_async_empty_code(self, service):
        """Lines 592-593: no code provided."""
        storage = AsyncStorage()
        storage.data["u1"] = TOTPUserData(id="u1", email="u@e.com", is_2fa_enabled=True)
        ok, err = await service.verify_2fa_async("u1", "", storage)
        assert ok is False

    @pytest.mark.anyio
    async def test_verify_2fa_async_sync_storage(self, service):
        """Lines 583-584: sync storage via to_thread."""
        storage = SyncStorage()
        result = await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        import pyotp
        secret = service._decrypt_secret(storage.data["u1"].totp_secret)
        code = pyotp.TOTP(secret).now()
        ok, err = await service.verify_2fa_async("u1", code, storage)
        assert ok is True

    @pytest.mark.anyio
    async def test_verify_2fa_async_backup_code(self, service):
        """Lines 601-609: valid backup code used."""
        storage = AsyncStorage()
        setup = await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        # Use plain backup code from setup result
        backup_code = setup.backup_codes[0]
        ok, err = await service.verify_2fa_async("u1", backup_code, storage)
        assert ok is True

    @pytest.mark.anyio
    async def test_verify_2fa_async_backup_code_fallback(self, service):
        """Line 607: fallback to sync save_backup_codes."""
        storage = SyncStorage()
        setup = await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        backup_code = setup.backup_codes[0]
        ok, err = await service.verify_2fa_async("u1", backup_code, storage)
        assert ok is True

    @pytest.mark.anyio
    async def test_verify_2fa_async_invalid_backup_code(self, service):
        """Line 611: invalid backup code."""
        storage = AsyncStorage()
        setup = await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        ok, err = await service.verify_2fa_async("u1", "000000", storage)
        assert ok is False
        assert "Invalid" in err
    @pytest.mark.anyio
    async def test_disable_2fa_async(self, service):
        """Lines 626-650: disable_2fa_async coverage."""
        from unittest.mock import patch
        storage = AsyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        
        # Valid code - use the actual secret from storage
        import pyotp
        secret = service._decrypt_secret(storage.data["u1"].totp_secret)
        code = pyotp.TOTP(secret).now()
        ok, err = await service.disable_2fa_async("u1", code, storage)
        assert ok is True
        assert storage.data["u1"].is_2fa_enabled is False

    @pytest.mark.anyio
    async def test_totp_storage_stubs(self):
        """Lines 57, 61, 65, 69, 73: protocol stubs - call on class to hit ... statements."""
        from tenxyte.core.totp_service import TOTPStorage
        # Protocol stubs - calling on class directly hits the "..." statements
        try: TOTPStorage.save_totp_secret(None, "u", "s")
        except (NotImplementedError, AttributeError): pass
        try: TOTPStorage.save_backup_codes(None, "u", [])
        except (NotImplementedError, AttributeError): pass
        try: TOTPStorage.enable_2fa(None, "u")
        except (NotImplementedError, AttributeError): pass
        try: TOTPStorage.disable_2fa(None, "u")
        except (NotImplementedError, AttributeError): pass
        try: TOTPStorage.load_user_data(None, "u")
        except (NotImplementedError, AttributeError): pass
    def test_verify_2fa_sync_full(self, service):
        """Lines 554-577: sync verify_2fa coverage."""
        storage = SyncStorage()
        setup = service.setup_2fa("u-sync", "u@e.com", storage)
        storage.data["u-sync"].is_2fa_enabled = True
        
        # Test valid TOTP
        import pyotp
        secret = service._decrypt_secret(storage.data["u-sync"].totp_secret)
        code = pyotp.TOTP(secret).now()
        ok, err = service.verify_2fa("u-sync", code, storage)
        assert ok is True
        
        # Test valid backup code
        backup = setup.backup_codes[0]
        ok, err = service.verify_2fa("u-sync", backup, storage)
        assert ok is True
        
        # Test invalid
        ok, err = service.verify_2fa("u-sync", "000000", storage)
        assert ok is False


# ─── TOTPService.disable_2fa_async (lines 654-684) ───────────────────────────

class TestDisable2FAAsync:
    @pytest.mark.anyio
    async def test_disable_2fa_async_success(self, service):
        """Lines 654-684: disable with valid TOTP code."""
        storage = AsyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        import pyotp
        secret = service._decrypt_secret(storage.data["u1"].totp_secret)
        code = pyotp.TOTP(secret).now()
        ok, err = await service.disable_2fa_async("u1", code, storage)
        assert ok is True

    @pytest.mark.anyio
    async def test_disable_2fa_async_not_enabled(self, service):
        """Lines 662-663: not enabled."""
        storage = AsyncStorage()
        storage.data["u1"] = TOTPUserData(id="u1", email="u@e.com")
        ok, err = await service.disable_2fa_async("u1", "code", storage)
        assert ok is False

    @pytest.mark.anyio
    async def test_disable_2fa_async_user_not_found(self, service):
        """Lines 659-660."""
        storage = AsyncStorage()
        ok, err = await service.disable_2fa_async("ghost", "code", storage)
        assert ok is False

    @pytest.mark.anyio
    async def test_disable_2fa_async_invalid_code(self, service):
        """Lines 674-675: invalid code."""
        storage = SyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        ok, err = await service.disable_2fa_async("u1", "000000", storage)
        assert ok is False


# ─── TOTPService.regenerate_backup_codes_async (lines 722-745) ───────────────

class TestRegenerateBackupCodesAsync:
    @pytest.mark.anyio
    async def test_regenerate_backup_codes_async_success(self, service):
        """Lines 722-745."""
        storage = AsyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        import pyotp
        secret = service._decrypt_secret(storage.data["u1"].totp_secret)
        code = pyotp.TOTP(secret).now()
        ok, new_codes, err = await service.regenerate_backup_codes_async("u1", code, storage)
        assert ok is True
        assert len(new_codes) > 0

    @pytest.mark.anyio
    async def test_regenerate_backup_codes_async_user_not_found(self, service):
        """Lines 727-728."""
        storage = AsyncStorage()
        ok, codes, err = await service.regenerate_backup_codes_async("ghost", "code", storage)
        assert ok is False

    @pytest.mark.anyio
    async def test_regenerate_backup_codes_async_not_enabled(self, service):
        """Lines 730-731."""
        storage = AsyncStorage()
        storage.data["u1"] = TOTPUserData(id="u1", email="u@e.com")
        ok, codes, err = await service.regenerate_backup_codes_async("u1", "code", storage)
        assert ok is False

    @pytest.mark.anyio
    async def test_regenerate_backup_codes_async_invalid_code(self, service):
        """Lines 734: bad code."""
        storage = SyncStorage()
        await service.setup_2fa_async("u1", "u@e.com", storage)
        storage.data["u1"].is_2fa_enabled = True
        ok, codes, err = await service.regenerate_backup_codes_async("u1", "000000", storage)
        assert ok is False
