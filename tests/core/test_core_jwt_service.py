"""
Tests for core jwt_service - targeting 100% coverage of
src/tenxyte/core/jwt_service.py
"""
import time
import uuid
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from tenxyte.core.jwt_service import (
    InMemoryTokenBlacklistService,
    TokenBlacklistService,
    JWTService,
    TokenPair,
    DecodedToken,
)
from tenxyte.core.settings import Settings


def _make_settings(**overrides):
    s = MagicMock(spec=Settings)
    s.jwt_secret = overrides.get("jwt_secret", "test-secret-key-32chars-minimum!")
    s.jwt_public_key = overrides.get("jwt_public_key", None)
    s.jwt_algorithm = overrides.get("jwt_algorithm", "HS256")
    s.jwt_access_token_lifetime = overrides.get("jwt_access_token_lifetime", 3600)
    s.jwt_refresh_token_lifetime = overrides.get("jwt_refresh_token_lifetime", 86400)
    s.jwt_issuer = overrides.get("jwt_issuer", "")
    s.jwt_audience = overrides.get("jwt_audience", None)
    return s


class DummyBlacklistService(TokenBlacklistService):
    def is_blacklisted(self, jti: str) -> bool: return False
    def blacklist_token(self, jti: str, exp: datetime, user_id=None, reason="") -> bool: return True

def test_token_blacklist_protocol():
    """Lines 50, 60."""
    p = DummyBlacklistService()
    assert not p.is_blacklisted("jti")
    assert p.blacklist_token("jti", datetime.now())

# ═══════════════════════════════════════════════════════════════════════════════
# InMemoryTokenBlacklistService  (lines 63-133)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInMemoryTokenBlacklistService:

    @pytest.fixture
    def bl(self):
        return InMemoryTokenBlacklistService()

    def test_init(self, bl):
        """Lines 72-75."""
        assert bl._blacklisted == {}
        assert bl._reasons == {}
        assert bl._user_revocations == {}

    def test_is_blacklisted_not_found(self, bl):
        """Lines 79-80."""
        assert bl.is_blacklisted("jti-1") is False

    def test_is_blacklisted_found(self, bl):
        """Lines 83, 91."""
        bl.blacklist_token("jti-1", datetime.now(timezone.utc) + timedelta(hours=1))
        assert bl.is_blacklisted("jti-1") is True

    def test_is_blacklisted_expired(self, bl):
        """Lines 84-89: expired entry cleaned up."""
        bl.blacklist_token("jti-exp", datetime.now(timezone.utc) - timedelta(seconds=1))
        assert bl.is_blacklisted("jti-exp") is False

    def test_is_blacklisted_expired_with_reason(self, bl):
        """Lines 87-88: expired entry with reason cleaned up."""
        bl.blacklist_token("jti-exp", datetime.now(timezone.utc) - timedelta(seconds=1), reason="test")
        assert bl.is_blacklisted("jti-exp") is False
        assert "jti-exp" not in bl._reasons

    def test_is_user_revoked_no_revocation(self, bl):
        """Lines 95-96."""
        assert bl.is_user_revoked("u1", datetime.now(timezone.utc)) is False

    def test_is_user_revoked_before(self, bl):
        """Lines 98-100: token issued before revocation → revoked."""
        bl.revoke_all_user_tokens("u1")
        old_iat = datetime.now(timezone.utc) - timedelta(hours=1)
        assert bl.is_user_revoked("u1", old_iat) is True

    def test_is_user_revoked_after(self, bl):
        """Lines 98-100: token issued after revocation → not revoked."""
        bl.revoke_all_user_tokens("u1")
        future_iat = datetime.now(timezone.utc) + timedelta(hours=1)
        assert bl.is_user_revoked("u1", future_iat) is False

    def test_revoke_all_user_tokens(self, bl):
        """Lines 104-106."""
        result = bl.revoke_all_user_tokens("u1")
        assert isinstance(result, datetime)
        assert "u1" in bl._user_revocations

    def test_blacklist_token_no_reason(self, bl):
        """Lines 116-119: no reason."""
        assert bl.blacklist_token("jti", datetime.now(timezone.utc)) is True
        assert "jti" not in bl._reasons

    def test_blacklist_token_with_reason(self, bl):
        """Lines 117-118: with reason."""
        bl.blacklist_token("jti", datetime.now(timezone.utc), reason="logout")
        assert bl._reasons["jti"] == "logout"

    def test_get_reason(self, bl):
        """Line 123."""
        bl.blacklist_token("jti", datetime.now(timezone.utc), reason="test")
        assert bl.get_reason("jti") == "test"
        assert bl.get_reason("missing") is None

    def test_cleanup_expired(self, bl):
        """Lines 127-133."""
        bl.blacklist_token("live", datetime.now(timezone.utc) + timedelta(hours=1))
        bl.blacklist_token("dead", datetime.now(timezone.utc) - timedelta(seconds=1), reason="r")
        count = bl.cleanup_expired()
        assert count == 1
        assert "dead" not in bl._blacklisted
        assert "dead" not in bl._reasons
        assert "live" in bl._blacklisted


# ═══════════════════════════════════════════════════════════════════════════════
# JWTService  (lines 136-705)
# ═══════════════════════════════════════════════════════════════════════════════

class TestJWTService:

    @pytest.fixture
    def svc(self):
        return JWTService(settings=_make_settings())

    @pytest.fixture
    def svc_with_issuer(self):
        return JWTService(settings=_make_settings(jwt_issuer="tenxyte", jwt_audience="myapp"))

    # -- __init__ --

    def test_init_symmetric(self):
        """Lines 179-182 branch: HS256."""
        svc = JWTService(settings=_make_settings())
        assert not svc.is_asymmetric

    def test_init_asymmetric(self):
        """Lines 179-182: RS256 branch."""
        svc = JWTService(settings=_make_settings(
            jwt_algorithm="RS256",
            jwt_secret="privkey",
            jwt_public_key="pubkey"
        ))
        assert svc.is_asymmetric
        assert svc.private_key == "privkey"
        assert svc.public_key == "pubkey"
        assert svc.verifying_key == "pubkey"

    def test_init_asymmetric_no_public(self):
        """Line 182: no public key → uses private key."""
        svc = JWTService(settings=_make_settings(
            jwt_algorithm="RS256", jwt_secret="privkey", jwt_public_key=None
        ))
        assert svc.verifying_key == "privkey"

    # -- generate_access_token --

    def test_generate_access_token(self, svc):
        token, jti, expires = svc.generate_access_token("u1", "app1")
        assert token
        assert jti
        assert expires > datetime.now(timezone.utc)

    def test_generate_access_token_no_key(self):
        """Line 217: no signing key."""
        svc = JWTService(settings=_make_settings(jwt_secret=""))
        with pytest.raises(ValueError, match="signing key"):
            svc.generate_access_token("u1", "app1")

    def test_generate_access_token_asymmetric_no_private(self):
        """Lines 222-223: asymmetric but no private key."""
        svc = JWTService(settings=_make_settings(
            jwt_algorithm="RS256", jwt_secret="", jwt_public_key="pub"
        ))
        with pytest.raises(ValueError, match="signing key"):
            svc.generate_access_token("u1", "app1")

    def test_generate_access_token_with_issuer_audience(self, svc_with_issuer):
        token, _, _ = svc_with_issuer.generate_access_token("u1", "app1")
        decoded = pyjwt.decode(
            token, "test-secret-key-32chars-minimum!",
            algorithms=["HS256"], audience="myapp", issuer="tenxyte"
        )
        assert decoded["iss"] == "tenxyte"
        assert decoded["aud"] == "myapp"

    def test_generate_access_token_extra_claims(self, svc):
        """Lines 251-256: extra claims, protected ones filtered."""
        token, _, _ = svc.generate_access_token("u1", "app1", extra_claims={
            "custom": "val", "jti": "SHOULD_NOT_OVERRIDE"
        })
        decoded = pyjwt.decode(token, "test-secret-key-32chars-minimum!", algorithms=["HS256"])
        assert decoded["custom"] == "val"
        assert decoded["jti"] != "SHOULD_NOT_OVERRIDE"

    # -- generate_refresh_token --
    
    def test_generate_refresh_token(self, svc):
        """Line 281."""
        rt = svc.generate_refresh_token("u1", "app1")
        assert len(rt) > 10

    # -- generate_token_pair --

    def test_generate_token_pair(self, svc):
        """Lines 302-306."""
        pair = svc.generate_token_pair("u1", "app1", "refresh_str")
        assert isinstance(pair, TokenPair)
        assert pair.refresh_token == "refresh_str"

    # -- generate_new_token_pair --

    def test_generate_new_token_pair(self, svc):
        """Lines 335-342."""
        pair = svc.generate_new_token_pair("u1", "app1")
        assert isinstance(pair, TokenPair)
        assert len(pair.refresh_token) > 10

    # -- decode_token --

    def test_decode_token_valid(self, svc):
        token, jti, _ = svc.generate_access_token("u1", "app1")
        decoded = svc.decode_token(token)
        assert decoded.is_valid
        assert decoded.user_id == "u1"

    def test_decode_token_no_key(self):
        """Line 367: no verifying key."""
        svc = JWTService(settings=_make_settings(jwt_secret=""))
        svc.verifying_key = ""
        with pytest.raises(ValueError, match="verifying key"):
            svc.decode_token("some.token.here")

    def test_decode_token_missing_claims(self, svc):
        """Lines 391: missing user_id/app_id/jti."""
        payload = {"type": "access", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = pyjwt.encode(payload, "test-secret-key-32chars-minimum!", algorithm="HS256")
        decoded = svc.decode_token(token)
        assert not decoded.is_valid
        assert "Missing required claims" in decoded.error

    def test_decode_token_expired(self, svc):
        """Line 433: ExpiredSignatureError → None."""
        payload = {
            "type": "access", "jti": "x", "user_id": "u1", "app_id": "a1",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = pyjwt.encode(payload, "test-secret-key-32chars-minimum!", algorithm="HS256")
        assert svc.decode_token(token) is None

    def test_decode_token_invalid(self, svc):
        """Lines 434-445: InvalidTokenError."""
        decoded = svc.decode_token("not.a.valid.token")
        assert decoded is not None
        assert not decoded.is_valid
        assert "Invalid token" in decoded.error

    def test_decode_token_blacklisted(self, svc):
        token, jti, expires = svc.generate_access_token("u1", "app1")
        svc.blacklist_service.blacklist_token(jti, expires)
        decoded = svc.decode_token(token)
        assert decoded.is_blacklisted
        assert not decoded.is_valid

    def test_decode_token_user_revoked(self, svc):
        """Lines 415-418: user-level revocation."""
        token, _, _ = svc.generate_access_token("u1", "app1")
        # Revoke all tokens (sets revocation time to now)
        import time; time.sleep(0.01)
        svc.blacklist_service.revoke_all_user_tokens("u1")
        decoded = svc.decode_token(token)
        assert decoded.is_blacklisted

    def test_decode_token_skip_blacklist(self, svc):
        token, jti, expires = svc.generate_access_token("u1", "app1")
        svc.blacklist_service.blacklist_token(jti, expires)
        decoded = svc.decode_token(token, check_blacklist=False)
        assert not decoded.is_blacklisted

    # -- is_token_valid / get_user_id_from_token / get_application_id_from_token --

    def test_is_token_valid(self, svc):
        """Lines 449-450."""
        token, _, _ = svc.generate_access_token("u1", "app1")
        assert svc.is_token_valid(token) is True

    def test_is_token_valid_expired(self, svc):
        assert svc.is_token_valid("bad.token") is False

    def test_get_user_id_from_token(self, svc):
        """Lines 454-457."""
        token, _, _ = svc.generate_access_token("u1", "app1")
        assert svc.get_user_id_from_token(token) == "u1"

    def test_get_user_id_from_token_invalid(self, svc):
        assert svc.get_user_id_from_token("bad") is None

    def test_get_application_id_from_token(self, svc):
        """Lines 461-464."""
        token, _, _ = svc.generate_access_token("u1", "app1")
        assert svc.get_application_id_from_token(token) == "app1"

    def test_get_application_id_from_token_invalid(self, svc):
        assert svc.get_application_id_from_token("bad") is None

    # -- blacklist_token --

    def test_blacklist_token_success(self, svc):
        """Lines 487."""
        token, _, _ = svc.generate_access_token("u1", "app1")
        assert svc.blacklist_token(token, reason="logout") is True

    def test_blacklist_token_invalid(self, svc):
        """Line 487: invalid token → False."""
        assert svc.blacklist_token("bad.token") is False

    # -- blacklist_token_by_jti --

    def test_blacklist_token_by_jti(self, svc):
        """Line 505."""
        assert svc.blacklist_token_by_jti("jti-1", datetime.now(timezone.utc)) is True

    # -- refresh_tokens --

    def test_refresh_tokens_db_success(self, svc):
        """Lines 598-630."""
        mock_module = MagicMock()
        mock_rt_model = MagicMock()
        mock_rt_instance = MagicMock()
        mock_rt_instance.is_revoked = False
        mock_rt_instance.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_rt_instance.user_id = "u1"
        mock_rt_instance.application_id = "app1"
        
        mock_rt_model.get_by_raw_token.return_value = mock_rt_instance
        mock_module.RefreshToken = mock_rt_model

        with patch.dict("sys.modules", {"tenxyte.models": mock_module}):
            result = svc.refresh_tokens("real-refresh-token")
            
        assert result is not None
        assert isinstance(result, TokenPair)
        assert mock_rt_instance.is_revoked is True
        mock_rt_instance.save.assert_called_with(update_fields=['is_revoked'])
        mock_rt_model.objects.create.assert_called_once()
        
    def test_refresh_tokens_db_revoked(self, svc):
        """Line 598."""
        mock_module = MagicMock()
        mock_rt_model = MagicMock()
        mock_rt_instance = MagicMock()
        mock_rt_instance.is_revoked = True
        
        mock_rt_model.get_by_raw_token.return_value = mock_rt_instance
        mock_module.RefreshToken = mock_rt_model

        with patch.dict("sys.modules", {"tenxyte.models": mock_module}):
            result = svc.refresh_tokens("real-refresh-token")
        assert result is None

    def test_refresh_tokens_db_expired(self, svc):
        """Line 602."""
        mock_module = MagicMock()
        mock_rt_model = MagicMock()
        mock_rt_instance = MagicMock()
        mock_rt_instance.is_revoked = False
        mock_rt_instance.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        mock_rt_model.get_by_raw_token.return_value = mock_rt_instance
        mock_module.RefreshToken = mock_rt_model

        with patch.dict("sys.modules", {"tenxyte.models": mock_module}):
            result = svc.refresh_tokens("real-refresh-token")
        assert result is None

    def test_refresh_tokens_import_error_decode_failure(self, svc):
        """Lines 679-686: handle JWT exception during fallback."""
        with patch.dict("sys.modules", {"tenxyte.models": None}):
            # Cause exception during decode_token
            with patch("tenxyte.core.jwt_service.JWTService.decode_token", side_effect=Exception):
                result = svc.refresh_tokens("bad-token")
        assert result is None

    def test_refresh_tokens_jwt_exception(self, svc):
        """Lines 676-677: exception in DoesNotExist flow."""
        mock_module = MagicMock()
        mock_rt = MagicMock()
        mock_rt.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_rt.get_by_raw_token.side_effect = mock_rt.DoesNotExist()
        mock_module.RefreshToken = mock_rt

        with patch.dict("sys.modules", {"tenxyte.models": mock_module}):
            with patch("tenxyte.core.jwt_service.JWTService.decode_token", side_effect=Exception):
                result = svc.refresh_tokens("bad-token")
        assert result is None

    def test_refresh_tokens_jwt_invalid(self, svc):
        """Line 645: decode_token returns invalid token."""
        mock_module = MagicMock()
        mock_rt = MagicMock()
        mock_rt.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_rt.get_by_raw_token.side_effect = mock_rt.DoesNotExist()
        mock_module.RefreshToken = mock_rt

        invalid_token = DecodedToken(
            user_id="", app_id="", jti="", exp=datetime.now(), iat=datetime.now(),
            type="error", claims={}, is_valid=False
        )
        with patch.dict("sys.modules", {"tenxyte.models": mock_module}):
            with patch("tenxyte.core.jwt_service.JWTService.decode_token", return_value=invalid_token):
                result = svc.refresh_tokens("bad-token")
        assert result is None

    def test_refresh_tokens_jwt_refresh_type(self, svc):
        """Lines 647-677: refresh via JWT refresh token (DoesNotExist branch)."""
        # Create a token with type=refresh
        payload = {
            "type": "refresh", "jti": str(uuid.uuid4()), "user_id": "u1", "app_id": "a1",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        refresh_jwt = pyjwt.encode(payload, "test-secret-key-32chars-minimum!", algorithm="HS256")

        # Mock RefreshToken.get_by_raw_token to raise DoesNotExist
        mock_model = MagicMock()
        mock_model.DoesNotExist = Exception
        mock_model.get_by_raw_token.side_effect = Exception()

        with patch.dict("sys.modules", {"tenxyte.models": MagicMock()}):
            with patch("tenxyte.core.jwt_service.JWTService.refresh_tokens") as orig:
                # We need to actually call through; let's just test the method directly
                pass

        # Simpler approach: mock the import at the right level
        mock_module = MagicMock()
        mock_rt = MagicMock()
        mock_rt.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_rt.get_by_raw_token.side_effect = mock_rt.DoesNotExist()
        mock_module.RefreshToken = mock_rt

        with patch.dict("sys.modules", {"tenxyte.models": mock_module}):
            result = svc.refresh_tokens(refresh_jwt)
        assert result is not None
        assert isinstance(result, TokenPair)

    def test_refresh_tokens_non_refresh_type(self, svc):
        """Lines 647-648: JWT token but type != refresh → None."""
        token, _, _ = svc.generate_access_token("u1", "app1")

        mock_module = MagicMock()
        mock_rt = MagicMock()
        mock_rt.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock_rt.get_by_raw_token.side_effect = mock_rt.DoesNotExist()
        mock_module.RefreshToken = mock_rt

        with patch.dict("sys.modules", {"tenxyte.models": mock_module}):
            result = svc.refresh_tokens(token)
        assert result is None
