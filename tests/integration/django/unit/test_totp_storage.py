"""
Tests for DjangoTOTPStorage - targeting 100% coverage of
src/tenxyte/adapters/django/totp_storage.py
"""
import pytest
from unittest.mock import MagicMock, patch

from tenxyte.adapters.django.totp_storage import DjangoTOTPStorage, TOTPUserData


# ═══════════════════════════════════════════════════════════════════════════════
# TOTPUserData  (lines 13-21)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTOTPUserData:

    def test_has_backup_codes_true(self):
        d = TOTPUserData(totp_secret="s", is_2fa_enabled=True, backup_codes=["c1"])
        assert d.has_backup_codes() is True

    def test_has_backup_codes_false(self):
        d = TOTPUserData(totp_secret="s", is_2fa_enabled=True, backup_codes=[])
        assert d.has_backup_codes() is False


# ═══════════════════════════════════════════════════════════════════════════════
# DjangoTOTPStorage
# ═══════════════════════════════════════════════════════════════════════════════

class TestDjangoTOTPStorage:

    @pytest.fixture
    def storage(self):
        return DjangoTOTPStorage(encryption_key="test-key")

    def _mock_user(self, **overrides):
        defaults = dict(
            id=1, totp_secret="encrypted_secret",
            is_2fa_enabled=True, backup_codes=["h1", "h2"],
        )
        defaults.update(overrides)
        m = MagicMock()
        for k, v in defaults.items():
            setattr(m, k, v)
        return m

    # ── get_secret ───────────────────────────────────────────────────────────

    def test_get_secret_found(self, storage):
        """Lines 58-63."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = self._mock_user()
            assert storage.get_secret("1") == "encrypted_secret"

    def test_get_secret_not_found(self, storage):
        """Lines 64-65."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.get_secret("x") is None

    # ── store_secret ─────────────────────────────────────────────────────────

    def test_store_secret_success(self, storage):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = self._mock_user()
            assert storage.store_secret("1", "new_secret") is True

    def test_store_secret_not_found(self, storage):
        """Lines 86-87."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.store_secret("x", "s") is False

    # ── delete_secret ────────────────────────────────────────────────────────

    def test_delete_secret_success(self, storage):
        """Lines 99-107."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            mock_u = self._mock_user()
            MockUM.objects.get.return_value = mock_u
            assert storage.delete_secret("1") is True
            assert mock_u.totp_secret is None
            assert mock_u.is_2fa_enabled is False

    def test_delete_secret_not_found(self, storage):
        """Lines 108-109."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.delete_secret("x") is False

    # ── is_code_used ─────────────────────────────────────────────────────────

    def test_is_code_used_true(self, storage):
        """Lines 124-127."""
        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.return_value = True
            assert storage.is_code_used("1", "123456") is True

    def test_is_code_used_false(self, storage):
        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.return_value = None
            assert storage.is_code_used("1", "123456") is False

    # ── mark_code_used ───────────────────────────────────────────────────────

    def test_mark_code_used(self, storage):
        """Lines 141-145."""
        with patch("django.core.cache.cache") as mock_cache:
            assert storage.mark_code_used("1", "123456", 60) is True
            mock_cache.set.assert_called_once()

    # ── get_backup_codes ─────────────────────────────────────────────────────

    def test_get_backup_codes_found(self, storage):
        """Lines 157-163."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = self._mock_user()
            assert storage.get_backup_codes("1") == ["h1", "h2"]

    def test_get_backup_codes_none(self, storage):
        """Line 163: codes is None → returns []."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = self._mock_user(backup_codes=None)
            assert storage.get_backup_codes("1") == []

    def test_get_backup_codes_not_found(self, storage):
        """Lines 164-165."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.get_backup_codes("x") == []

    # ── store_backup_codes ───────────────────────────────────────────────────

    def test_store_backup_codes_success(self, storage):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = self._mock_user()
            assert storage.store_backup_codes("1", ["c1", "c2"]) is True

    def test_store_backup_codes_not_found(self, storage):
        """Lines 186-187."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.store_backup_codes("x", []) is False

    # ── use_backup_code ──────────────────────────────────────────────────────

    def test_use_backup_code_found(self, storage):
        """Lines 200-211: code found and removed."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            mock_u = self._mock_user(backup_codes=["h1", "h2"])
            MockUM.objects.get.return_value = mock_u
            assert storage.use_backup_code("1", "h1") is True
            assert "h1" not in mock_u.backup_codes

    def test_use_backup_code_not_in_list(self, storage):
        """Line 212: code not in list → False."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = self._mock_user(backup_codes=["h1"])
            assert storage.use_backup_code("1", "bad") is False

    def test_use_backup_code_not_found(self, storage):
        """Lines 213-214."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.use_backup_code("x", "h1") is False

    # ── save_totp_secret (alias) ─────────────────────────────────────────────

    def test_save_totp_secret(self, storage):
        with patch.object(storage, "store_secret", return_value=True):
            assert storage.save_totp_secret("1", "sec") is True

    # ── load_user_data ───────────────────────────────────────────────────────

    def test_load_user_data_found(self, storage):
        """Lines 239-240."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = self._mock_user()
            result = storage.load_user_data("1")
        assert isinstance(result, TOTPUserData)
        assert result.totp_secret == "encrypted_secret"
        assert result.is_2fa_enabled is True
        assert result.backup_codes == ["h1", "h2"]

    def test_load_user_data_not_found(self, storage):
        """Lines 239-240."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.load_user_data("x") is None

    # ── save_backup_codes (alias) ────────────────────────────────────────────

    def test_save_backup_codes(self, storage):
        with patch.object(storage, "store_backup_codes", return_value=True):
            assert storage.save_backup_codes("1", ["c1"]) is True

    # ── enable_2fa ───────────────────────────────────────────────────────────

    def test_enable_2fa_success(self, storage):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            MockUM.objects.get.return_value = self._mock_user()
            assert storage.enable_2fa("1") is True

    def test_enable_2fa_not_found(self, storage):
        """Lines 256-257."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.enable_2fa("x") is False

    # ── disable_2fa ──────────────────────────────────────────────────────────

    def test_disable_2fa_success(self, storage):
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            gum.return_value = MockUM
            mock_u = self._mock_user()
            MockUM.objects.get.return_value = mock_u
            assert storage.disable_2fa("1") is True

    def test_disable_2fa_not_found(self, storage):
        """Lines 271-272."""
        with patch("tenxyte.models.get_user_model") as gum:
            MockUM = MagicMock()
            MockUM.DoesNotExist = Exception
            gum.return_value = MockUM
            MockUM.objects.get.side_effect = Exception()
            assert storage.disable_2fa("x") is False
