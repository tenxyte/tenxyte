import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from django.core.cache import cache

from tenxyte.adapters.django.cache_service import DjangoCacheService, get_cache_service

@pytest.fixture
def cache_service():
    """Returns a clean DjangoCacheService instance."""
    # Ensure cache is clear before each test
    svc = DjangoCacheService(cache_name='default')
    svc.clear()
    yield svc
    svc.clear()

def test_get_set_delete(cache_service):
    """Test get, set, and delete operations."""
    key = "test_key"
    val = "test_value"
    
    # Test get missing
    assert cache_service.get(key) is None
    
    # Test set
    assert cache_service.set(key, val, timeout=60) is True
    
    # Test get existing
    assert cache_service.get(key) == val
    
    # Test delete
    assert cache_service.delete(key) is True
    assert cache_service.get(key) is None

def test_exists(cache_service):
    """Test exists method."""
    key = "exists_key"
    
    assert cache_service.exists(key) is False
    
    cache_service.set(key, "data", timeout=60)
    assert cache_service.exists(key) is True
    
    # Test with None value (Django cache specific behavior)
    cache_service.set("none_key", None, timeout=60)
    assert cache_service.exists("none_key") is True

def test_increment(cache_service):
    """Test increment method."""
    key = "inc_key"
    
    # Test increment when key doesn't exist
    assert cache_service.increment(key, 5) == 5
    
    # Test increment when key exists
    assert cache_service.increment(key, 2) == 7
    
    # Test negative increment
    assert cache_service.increment(key, -3) == 4

def test_expire(cache_service):
    """Test expire method."""
    key = "expire_key"
    
    # Test expire when key doesn't exist
    assert cache_service.expire(key, 60) is False
    
    # Test expire when key exists
    cache_service.set(key, "val")
    assert cache_service.expire(key, 60) is True

def test_ttl_fallback(cache_service):
    """Test ttl method fallback behavior."""
    key = "ttl_key"
    
    # Test ttl when key doesn't exist
    assert cache_service.ttl(key) == -2
    
    # Test ttl when key exists but no native ttl support
    cache_service.set(key, "val", timeout=60)
    # The default dummy/locmem cache doesn't have native TTL
    assert cache_service.ttl(key) == -1

def test_ttl_native():
    """Test ttl method with native TTL support mocked."""
    svc = DjangoCacheService(cache_name='default')
    
    # Mock backend with native .ttl() returning a value
    mock_backend = MagicMock()
    mock_backend.ttl.return_value = 42

    with patch.object(svc, '_get_cache', return_value=mock_backend):
        # Native TTL supported
        assert svc.ttl("any") == 42
        
        # Native TTL returning None → -1 (no expiration)
        mock_backend.ttl.return_value = None
        assert svc.ttl("any") == -1

    # Simulate backend without .ttl attribute → fallback to exists()
    # Use patch.object on exists() directly to control its return value
    with patch.object(svc, 'exists', return_value=False):
        # Key missing → -2
        assert svc.ttl("missing_key") == -2
    
    with patch.object(svc, 'exists', return_value=True):
        # Key exists but no TTL info → -1
        assert svc.ttl("existing_key") == -1

def test_clear(cache_service):
    """Test clear method."""
    cache_service.set("k1", "v1")
    cache_service.set("k2", "v2")
    
    assert cache_service.clear() is True
    assert cache_service.get("k1") is None
    assert cache_service.get("k2") is None

def test_is_blacklisted(cache_service):
    """Test is_blacklisted method."""
    jti = "test_jti"
    assert cache_service.is_blacklisted(jti) is False
    
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    cache_service.blacklist_token(jti, expires_at)
    
    assert cache_service.is_blacklisted(jti) is True

def test_is_user_revoked(cache_service):
    """Test is_user_revoked method."""
    user_id = "user123"
    
    # No IAT provided
    assert cache_service.is_user_revoked(user_id) is False
    
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=1)
    future = now + timedelta(hours=1)
    
    # User not revoked
    assert cache_service.is_user_revoked(user_id, now) is False
    
    # Revoke user
    revocation_time = cache_service.revoke_all_user_tokens(user_id)
    
    # Tokens issued before revocation are revoked
    assert cache_service.is_user_revoked(user_id, past) is True
    
    # Tokens issued after revocation are ostensibly valid
    # In reality they should be, but let's test the datetime compare
    assert cache_service.is_user_revoked(user_id, future) is False

def test_is_user_revoked_with_timestamp(cache_service):
    """Test is_user_revoked when stored value is a numeric timestamp."""
    user_id = "user456"
    now = datetime.now(timezone.utc)
    token_iat = now - timedelta(hours=1)
    
    # Mock cache to return numeric timestamp directly (how standard redis backend might store it)
    cache_service._get_cache().set(f"revoked_user_{user_id}", now.timestamp())
    
    assert cache_service.is_user_revoked(user_id, token_iat) is True
    
    # Ensure tokens issued after are valid
    assert cache_service.is_user_revoked(user_id, now + timedelta(hours=1)) is False

def test_get_cache_service():
    """Test convenience get_cache_service function."""
    svc = get_cache_service()
    assert isinstance(svc, DjangoCacheService)
    assert svc._cache_name == 'default'
    
    svc_custom = get_cache_service(cache_name='custom')
    assert isinstance(svc_custom, DjangoCacheService)
    assert svc_custom._cache_name == 'custom'

def test_ttl_exception_fallback():
    """Test ttl() exception branch (line 183): when backend has .ttl but it raises."""
    svc = DjangoCacheService(cache_name='default')
    
    mock_backend = MagicMock()
    mock_backend.ttl.side_effect = Exception("Redis connection error")
    
    with patch.object(svc, '_get_cache', return_value=mock_backend):
        # Key exists → exists() should return True → ttl returns -1
        with patch.object(svc, 'exists', return_value=True):
            assert svc.ttl("some_key") == -1
        
        # Key missing → exists() returns False → ttl returns -2
        with patch.object(svc, 'exists', return_value=False):
            assert svc.ttl("missing_key") == -2

def test_is_code_used_returns_true(cache_service):
    """Test is_code_used() when code IS in cache (True path, lines 216-217)."""
    user_id = "user_totp"
    code = "123456"
    
    # Initially not used
    assert cache_service.is_code_used(user_id, code) is False
    
    # Mark it as used
    cache_service.mark_code_used(user_id, code, ttl_seconds=60)
    
    # Now it should be detected as used
    assert cache_service.is_code_used(user_id, code) is True

def test_mark_code_used(cache_service):
    """Test mark_code_used() method (lines 231-233)."""
    user_id = "user_totp2"
    code = "654321"
    
    result = cache_service.mark_code_used(user_id, code, ttl_seconds=60)
    assert result is True
    
    # Verify the key is now set
    cache_key = f"totp_used_{user_id}_{code}"
    assert cache_service.get(cache_key) is True

def test_is_user_revoked_with_datetime_object(cache_service):
    """Test is_user_revoked() when stored value is a datetime object (line 273)."""
    user_id = "user_dt"
    now = datetime.now(timezone.utc)
    past_iat = now - timedelta(hours=2)
    future_iat = now + timedelta(hours=1)
    
    # Store a datetime object directly (not a timestamp)
    cache_service._get_cache().set(f"revoked_user_{user_id}", now)
    
    # Token issued before revocation → should be revoked
    assert cache_service.is_user_revoked(user_id, past_iat) is True
    
    # Token issued after revocation → should not be revoked
    assert cache_service.is_user_revoked(user_id, future_iat) is False

def test_is_user_revoked_unknown_type(cache_service):
    """Test is_user_revoked() fallback return False (line 277) for unknown types."""
    user_id = "user_unknown"
    token_iat = datetime.now(timezone.utc)
    
    # Store a value that is neither datetime nor int/float (e.g. a string)
    cache_service._get_cache().set(f"revoked_user_{user_id}", "some-invalid-value")
    
    # Should fall through to `return False`
    assert cache_service.is_user_revoked(user_id, token_iat) is False

