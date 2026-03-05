import pytest
import json
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.test import override_settings

from tenxyte.models import User
from tenxyte.models.security import BlacklistedToken, AuditLog

@pytest.fixture
def user(db):
    return User.objects.create(email="sec_test@test.com", password="pass")

@pytest.fixture
def user2(db):
    return User.objects.create(email="sec2_test@test.com", password="pass")

@pytest.mark.django_db
class TestBlacklistedTokenModel:
    def test_str_method(self, user):
        bt = BlacklistedToken.objects.create(
            token_jti="12345678901234567890abcdef", user=user, expires_at=timezone.now()
        )
        assert str(bt) == "Blacklisted: 12345678901234567890..."

    def test_is_blacklisted_db_fallback(self, user):
        from django.core.cache import cache
        # Create token directly in DB, so it's not in cache
        BlacklistedToken.objects.create(
            token_jti="missing_from_cache_jti", user=user, expires_at=timezone.now() + timedelta(hours=1)
        )
        # Ensure cache is clean
        cache.delete("bl_token_missing_from_cache_jti")
        
        # When checking, it should miss cache, hit DB, and repopulate cache
        assert BlacklistedToken.is_blacklisted("missing_from_cache_jti") is True
        
        # Optionally verify that caching happened afterwards
        assert cache.get("bl_token_missing_from_cache_jti") is True

@pytest.mark.django_db
class TestAuditLogModel:
    def test_str_method(self, user):
        log = AuditLog.objects.create(
            user=user, action="login", ip_address="127.0.0.1"
        )
        assert str(log) == f"login - {user} - {log.created_at}"

    def test_log_truncation_large_payload(self, user, caplog):
        large_dict = {"key": "x" * 15000}
        log = AuditLog.log(action="login", user=user, details=large_dict)
        
        assert log.details.get("truncated") is True
        assert log.details.get("error") == "Payload too large to store"
        assert "key" in log.details.get("original_keys", [])
        assert "exceeded 10KB" in caplog.text

    def test_log_truncation_non_serializable(self, user):
        class NonSerializable:
            pass
            
        bad_dict = {"obj": NonSerializable()}
        log = AuditLog.log(action="login", user=user, details=bad_dict)
        
        assert log.details.get("truncated") is True
        assert log.details.get("error") == "Non-serializable payload"

    def test_get_user_activity(self, user, user2):
        AuditLog.log(action="login", user=user)
        AuditLog.log(action="logout", user=user)
        AuditLog.log(action="login", user=user2)
        
        activity = AuditLog.get_user_activity(user, limit=5)
        assert activity.count() == 2

    def test_get_suspicious_activity(self, user):
        # Create an old suspicious activity
        log1 = AuditLog.log(action="login_failed", user=user)
        log1.created_at = timezone.now() - timedelta(hours=48)
        log1.save()
        
        # Create a new suspicious activity
        log2 = AuditLog.log(action="suspicious_activity", user=user)
        
        # Create a non-suspicious activity
        AuditLog.log(action="login", user=user)
        
        activity = AuditLog.get_suspicious_activity(hours=24)
        print(activity) # debug
        
        assert activity.count() == 1
        assert activity.first().id == log2.id

@pytest.mark.django_db
class TestAuditLogWebhookSignal:
    @patch('tenxyte.conf.auth_settings.AUDIT_WEBHOOK_URL', new="http://example.com/webhook", create=True)
    @patch('requests.post')
    def test_trigger_audit_log_webhook_success(self, mock_post, user):
        with patch('threading.Thread') as mock_thread:
            def side_effect(*args, **kwargs):
                target = kwargs.get('target')
                if target:
                    target()
                mock = MagicMock()
                return mock
            mock_thread.side_effect = side_effect

            AuditLog.log(action="login", user=user)
            
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "http://example.com/webhook"
            assert kwargs['json']['action'] == "login"
            assert kwargs['json']['user_id'] == user.id

    @patch('tenxyte.conf.auth_settings.AUDIT_WEBHOOK_URL', new="http://example.com/webhook", create=True)
    @patch('requests.post', side_effect=Exception("Webhook error"))
    def test_trigger_audit_log_webhook_error(self, mock_post, user, caplog):
        with patch('threading.Thread') as mock_thread:
            def side_effect(*args, **kwargs):
                target = kwargs.get('target')
                if target:
                    target()
                mock = MagicMock()
                return mock
            mock_thread.side_effect = side_effect

            AuditLog.log(action="login", user=user)
            
            mock_post.assert_called_once()
            assert "Failed to send audit webhook: Webhook error" in caplog.text
