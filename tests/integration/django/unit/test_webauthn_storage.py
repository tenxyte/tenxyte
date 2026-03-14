"""
Tests for DjangoWebAuthnStorage - targeting 100% coverage of
src/tenxyte/adapters/django/webauthn_storage.py
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from tenxyte.adapters.django.webauthn_storage import (
    DjangoWebAuthnCredential,
    DjangoWebAuthnStorage,
)
from tenxyte.core.webauthn_service import (
    WebAuthnCredential as CoreWebAuthnCredential,
)


# ═══════════════════════════════════════════════════════════════════════════════
# DjangoWebAuthnCredential  (wrapper class, lines 14-58)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDjangoWebAuthnCredential:

    @pytest.fixture
    def cred(self):
        mock = MagicMock()
        mock.id = 1
        mock.user_id = 2
        mock.credential_id = "cred-abc"
        mock.public_key = b"pubkey"
        mock.sign_count = 5
        mock.is_active = True
        mock.device_name = "Yubikey"
        mock.created_at = datetime.now(timezone.utc)
        mock.last_used_at = datetime.now(timezone.utc)
        mock.transports = ["usb"]
        return DjangoWebAuthnCredential(mock)

    def test_id(self, cred):
        assert cred.id == "1"

    def test_user_id(self, cred):
        assert cred.user_id == "2"

    def test_credential_id(self, cred):
        assert cred.credential_id == "cred-abc"

    def test_public_key(self, cred):
        assert cred.public_key == b"pubkey"

    def test_sign_count(self, cred):
        assert cred.sign_count == 5

    def test_is_active(self, cred):
        assert cred.is_active is True

    def test_device_name(self, cred):
        assert cred.device_name == "Yubikey"

    def test_created_at(self, cred):
        assert cred.created_at is not None

    def test_last_used_at(self, cred):
        assert cred.last_used_at is not None

    def test_transports(self, cred):
        assert cred.transports == ["usb"]

    def test_defaults_when_attrs_missing(self):
        """Properties fall back to defaults when attrs are missing."""
        mock = MagicMock(spec=[])  # no attrs
        mock.id = 99
        mock.user_id = 88
        mock.credential_id = "x"
        mock.public_key = b"k"
        wrapper = DjangoWebAuthnCredential(mock)
        assert wrapper.sign_count == 0
        assert wrapper.is_active is True
        assert wrapper.device_name == "Passkey"
        assert wrapper.created_at is None
        assert wrapper.last_used_at is None
        assert wrapper.transports == []


# ═══════════════════════════════════════════════════════════════════════════════
# DjangoWebAuthnStorage
# ═══════════════════════════════════════════════════════════════════════════════

class TestDjangoWebAuthnStorage:

    @pytest.fixture
    def storage(self):
        return DjangoWebAuthnStorage()

    def _mock_cred(self, **overrides):
        defaults = dict(
            id=10, user_id=1, credential_id="cid-1",
            public_key=b"pk", sign_count=3,
            device_name="Key1", aaguid="aa", transports=["usb"],
        )
        defaults.update(overrides)
        m = MagicMock()
        for k, v in defaults.items():
            setattr(m, k, v)
        return m

    def _mock_challenge(self, **overrides):
        defaults = dict(
            id=20, challenge="ch-data", user_id=1,
            purpose="authentication", operation="authenticate",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            is_used=False,
        )
        defaults.update(overrides)
        m = MagicMock()
        for k, v in defaults.items():
            setattr(m, k, v)
        return m

    # ── get_credential ───────────────────────────────────────────────────────

    def test_get_credential_found(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.return_value = self._mock_cred()
            result = storage.get_credential("cid-1")
        assert result is not None
        assert result["credential_id"] == "cid-1"

    def test_get_credential_not_found(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.side_effect = Exception("nope")
            assert storage.get_credential("bad") is None

    # ── get_credentials_for_user ─────────────────────────────────────────────

    def test_get_credentials_for_user_found(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.filter.return_value = [self._mock_cred()]
            result = storage.get_credentials_for_user("1")
        assert len(result) == 1

    def test_get_credentials_for_user_error(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.filter.side_effect = Exception()
            assert storage.get_credentials_for_user("1") == []

    # ── store_credential ─────────────────────────────────────────────────────

    def test_store_credential_success(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.create.return_value = self._mock_cred()
            assert storage.store_credential("1", {
                "credential_id": "c", "public_key": b"k", "sign_count": 0
            }) is True

    def test_store_credential_failure(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.create.side_effect = Exception()
            assert storage.store_credential("1", {
                "credential_id": "c", "public_key": b"k"
            }) is False

    # ── update_sign_count ────────────────────────────────────────────────────

    def test_update_sign_count_success(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.return_value = self._mock_cred()
            assert storage.update_sign_count("cid-1", 10) is True

    def test_update_sign_count_failure(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.side_effect = Exception()
            assert storage.update_sign_count("bad", 5) is False

    # ── delete_credential ────────────────────────────────────────────────────

    def test_delete_credential_success(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.return_value = self._mock_cred()
            assert storage.delete_credential("cid-1") is True

    def test_delete_credential_failure(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.side_effect = Exception()
            assert storage.delete_credential("bad") is False

    # ── get_challenge ────────────────────────────────────────────────────────

    def test_get_challenge_found(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.get.return_value = self._mock_challenge()
            result = storage.get_challenge("20")
        assert result is not None
        assert result["challenge"] == "ch-data"

    def test_get_challenge_not_found(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.get.side_effect = Exception()
            assert storage.get_challenge("bad") is None

    # ── store_challenge ──────────────────────────────────────────────────────

    def test_store_challenge_with_int_expiry(self, storage):
        """Lines 239-240: expires_at is int → converted to timedelta."""
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            mock_ch = self._mock_challenge()
            MockModel.objects.create.return_value = mock_ch
            result = storage.store_challenge({
                "challenge": "ch", "user_id": "1",
                "purpose": "registration", "expires_at": 300
            })
        assert result == "20"

    def test_store_challenge_with_datetime_expiry(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            mock_ch = self._mock_challenge()
            MockModel.objects.create.return_value = mock_ch
            result = storage.store_challenge({
                "challenge": "ch",
                "expires_at": datetime.utcnow() + timedelta(minutes=5)
            })
        assert result == "20"

    def test_store_challenge_no_expiry(self, storage):
        """Line 246: no expires_at → default 5 minutes."""
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            mock_ch = self._mock_challenge()
            MockModel.objects.create.return_value = mock_ch
            result = storage.store_challenge({"challenge": "ch"})
        assert result == "20"

    def test_store_challenge_failure(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.create.side_effect = Exception()
            assert storage.store_challenge({"challenge": "ch"}) == ""

    # ── delete_challenge ─────────────────────────────────────────────────────

    def test_delete_challenge_success(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.filter.return_value.delete.return_value = (1, {})
            assert storage.delete_challenge("20") is True

    def test_delete_challenge_failure(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.filter.side_effect = Exception()
            assert storage.delete_challenge("bad") is False

    # ── cleanup_expired_challenges ───────────────────────────────────────────

    def test_cleanup_success(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.filter.return_value.delete.return_value = (3, {})
            assert storage.cleanup_expired_challenges() == 3

    def test_cleanup_failure(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.filter.side_effect = Exception()
            assert storage.cleanup_expired_challenges() == 0

    # ══════════════════════════════════════════════════════════════════════════
    # Core compatibility methods
    # ══════════════════════════════════════════════════════════════════════════

    # ── get_by_credential_id ─────────────────────────────────────────────────

    def test_get_by_credential_id_bytes(self, storage):
        """Line 302: public_key is bytes → .decode()."""
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.return_value = self._mock_cred(public_key=b"key-bytes")
            result = storage.get_by_credential_id("cid-1")
        assert result is not None
        assert result.public_key == "key-bytes"

    def test_get_by_credential_id_str(self, storage):
        """Line 302: public_key is str → kept as-is."""
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.return_value = self._mock_cred(public_key="key-str")
            result = storage.get_by_credential_id("cid-1")
        assert result.public_key == "key-str"

    def test_get_by_credential_id_not_found(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.side_effect = Exception()
            assert storage.get_by_credential_id("bad") is None

    # ── list_by_user ─────────────────────────────────────────────────────────

    def test_list_by_user_found(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.filter.return_value = [
                self._mock_cred(public_key=b"k1"),
                self._mock_cred(id=11, public_key="k2"),
            ]
            result = storage.list_by_user("1")
        assert len(result) == 2

    def test_list_by_user_error(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.filter.side_effect = Exception()
            assert storage.list_by_user("1") == []

    # ── create (dispatch) ────────────────────────────────────────────────────

    def test_create_credential(self, storage):
        """Lines 347-348: first arg is WebAuthnCredential → _create_credential."""
        cred = CoreWebAuthnCredential(
            id="", credential_id="cid", public_key="pk",
            user_id="1", sign_count=0, device_name="Key",
            aaguid="aa", transports=["usb"],
        )
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            mock_created = self._mock_cred()
            MockModel.objects.create.return_value = mock_created
            result = storage.create(cred)
        assert result is not None

    def test_create_challenge_kwargs(self, storage):
        """Lines 351-356: kwargs path for challenge creation."""
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            mock_ch = self._mock_challenge()
            MockModel.objects.create.return_value = mock_ch
            result = storage.create(
                challenge="ch", operation="register",
                user_id="1", expiry_seconds=120
            )
        assert result is not None

    def test_create_challenge_positional(self, storage):
        """Lines 351-354: positional args for challenge creation."""
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            mock_ch = self._mock_challenge()
            MockModel.objects.create.return_value = mock_ch
            result = storage.create("ch", "authenticate", "1", 300)
        assert result is not None

    def test_create_challenge_minimal(self, storage):
        """Minimal positional args (only challenge)."""
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            mock_ch = self._mock_challenge()
            MockModel.objects.create.return_value = mock_ch
            result = storage.create("ch-only")
        assert result is not None

    # ── _create_credential ───────────────────────────────────────────────────

    def test_create_credential_with_bytes_key(self, storage):
        """Line 366: public_key is str → .encode()."""
        cred = CoreWebAuthnCredential(
            id="", credential_id="cid", public_key="pk-str",
            user_id="1", sign_count=0, device_name="K",
        )
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.create.return_value = self._mock_cred()
            result = storage._create_credential(cred)
        assert result is not None

    def test_create_credential_failure(self, storage):
        """Line 383-384: exception → RuntimeError."""
        cred = CoreWebAuthnCredential(
            id="", credential_id="cid", public_key="pk",
            user_id="1", sign_count=0, device_name="K",
        )
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.create.side_effect = Exception("DB error")
            with pytest.raises(RuntimeError, match="Failed to create credential"):
                storage._create_credential(cred)

    # ── _create_challenge ────────────────────────────────────────────────────

    def test_create_challenge_success(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            mock_ch = self._mock_challenge(user_id=None)
            MockModel.objects.create.return_value = mock_ch
            result = storage._create_challenge("ch", "auth")
        assert result is not None
        assert result.user_id is None

    def test_create_challenge_failure(self, storage):
        """Line 414-415: exception → RuntimeError."""
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.create.side_effect = Exception("DB error")
            with pytest.raises(RuntimeError, match="Failed to create challenge"):
                storage._create_challenge("ch", "auth")

    # ── delete (credential by id + user_id) ──────────────────────────────────

    def test_delete_success(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.return_value = self._mock_cred()
            assert storage.delete("10", "1") is True

    def test_delete_failure(self, storage):
        with patch("tenxyte.models.WebAuthnCredential") as MockModel:
            MockModel.objects.get.side_effect = Exception()
            assert storage.delete("bad", "1") is False

    # ── get_by_id (challenge) ────────────────────────────────────────────────

    def test_get_by_id_found(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            mock_ch = self._mock_challenge(user_id=None)
            MockModel.objects.get.return_value = mock_ch
            result = storage.get_by_id("20")
        assert result is not None
        assert result.user_id is None

    def test_get_by_id_with_user(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.get.return_value = self._mock_challenge()
            result = storage.get_by_id("20")
        assert result.user_id == "1"

    def test_get_by_id_not_found(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.get.side_effect = Exception()
            assert storage.get_by_id("bad") is None

    # ── consume ──────────────────────────────────────────────────────────────

    def test_consume_success(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.get.return_value = self._mock_challenge()
            assert storage.consume("20") is True

    def test_consume_failure(self, storage):
        with patch("tenxyte.models.WebAuthnChallenge") as MockModel:
            MockModel.objects.get.side_effect = Exception()
            assert storage.consume("bad") is False
