import pytest
from unittest.mock import MagicMock, patch
from tenxyte.models import User
from tenxyte.services.auth_service import AuthService
from tenxyte.services.agent_service import AgentTokenService
from tenxyte.signals import (
    brute_force_detected,
    suspicious_login_detected,
    account_locked,
    agent_circuit_breaker_triggered
)

@pytest.fixture
def mock_app():
    from tenxyte.models import Application
    app = Application.objects.create(name="Test App", is_active=True)
    yield app
    app.delete()

@pytest.mark.django_db
class TestSecuritySignals:
    
    def test_brute_force_signal_emitted(self, mock_app):
        # Setup the signal receiver mock
        signal_handler = MagicMock()
        brute_force_detected.connect(signal_handler)
        
        service = AuthService()
        
        # We simulate too many failed logins to trigger rate limit
        # This requires RATE_LIMITING_ENABLED to be True
        from tenxyte.conf import auth_settings
        if not auth_settings.RATE_LIMITING_ENABLED:
            pytest.skip("Rate limiting disabled")
            
        for _ in range(service.max_login_attempts + 1):
            service.authenticate_by_email("unknown@test.com", "wrong", mock_app, "1.1.1.1")
            
        signal_handler.assert_called()
        args, kwargs = signal_handler.call_args
        assert kwargs["ip_address"] == "1.1.1.1"
        assert kwargs["attempt_count"] >= service.max_login_attempts
        
        brute_force_detected.disconnect(signal_handler)

    def test_suspicious_login_signal_emitted(self, mock_app):
        signal_handler = MagicMock()
        suspicious_login_detected.connect(signal_handler)
        
        user = User.objects.create(email="user@test.com", is_active=True)
        user.set_password("Pass123")
        user.save()
        
        service = AuthService()
        # Mocking the new device detection to always return True
        service._check_new_device_alert = MagicMock(return_value=True)
        
        service.authenticate_by_email("user@test.com", "Pass123", mock_app, "1.2.3.4", "Android")
        
        signal_handler.assert_called_once()
        args, kwargs = signal_handler.call_args
        assert kwargs["user"] == user
        assert kwargs["ip_address"] == "1.2.3.4"
        assert kwargs["reason"] == "new_device"
        
        suspicious_login_detected.disconnect(signal_handler)

    def test_agent_circuit_breaker_signal_emitted(self):
        signal_handler = MagicMock()
        agent_circuit_breaker_triggered.connect(signal_handler)
        
        service = AgentTokenService()
        dummy_token = MagicMock()
        
        # Suspending an agent should trigger the signal
        service.suspend(dummy_token, reason="ANOMALY")
        
        signal_handler.assert_called_once()
        args, kwargs = signal_handler.call_args
        assert kwargs["agent_token"] == dummy_token
        assert kwargs["reason"] == "ANOMALY"
        
        agent_circuit_breaker_triggered.disconnect(signal_handler)


@pytest.mark.django_db
class TestSignalHandlers:
    """Test internal signal handlers for audit logging."""

    def test_audit_user_deletion_with_audit_enabled(self):
        """Test that user deletion is logged when audit logging is enabled."""
        from tenxyte.signals import audit_user_deletion
        
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = True
            mock_settings.BCRYPT_ROUNDS = 4  # Lower rounds for testing
            
            # Create user after patching to avoid bcrypt issues
            user = User.objects.create(email="delete@test.com", is_active=True, password="")
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Call the signal handler directly to ensure it's triggered
                audit_user_deletion(sender=User, instance=user)
                
                # Verify AuditLog.log was called
                mock_audit_log.log.assert_called_once_with(
                    action='account_deleted',
                    user=None,
                    details={
                        'deleted_user_id': str(user.pk),
                        'deleted_user_email': 'delete@test.com',
                    }
                )

    def test_audit_user_deletion_with_audit_disabled(self):
        """Test that user deletion is not logged when audit logging is disabled."""
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = False
            mock_settings.BCRYPT_ROUNDS = 4  # Lower rounds for testing
            
            # Create user after patching to avoid bcrypt issues
            user = User.objects.create(email="delete2@test.com", is_active=True, password="")
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Trigger the pre_delete signal
                user.delete()
                
                # Verify AuditLog.log was not called
                mock_audit_log.log.assert_not_called()

    def test_audit_user_deletion_direct_signal_call(self):
        """Test audit_user_deletion by calling the signal handler directly."""
        from tenxyte.signals import audit_user_deletion
        
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = True
            mock_settings.BCRYPT_ROUNDS = 4
            
            user = User.objects.create(email="direct@test.com", is_active=True, password="")
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Call the signal handler directly
                audit_user_deletion(sender=User, instance=user)
                
                # Verify AuditLog.log was called
                mock_audit_log.log.assert_called_once_with(
                    action='account_deleted',
                    user=None,
                    details={
                        'deleted_user_id': str(user.pk),
                        'deleted_user_email': 'direct@test.com',
                    }
                )

    def test_audit_user_deletion_non_user_model(self):
        """Test that deletion of non-user models doesn't trigger audit logging."""
        from tenxyte.models import Application
        app = Application.objects.create(name="Test App")
        
        with patch('tenxyte.models.AuditLog') as mock_audit_log:
            # Trigger the pre_delete signal for non-user model
            app.delete()
            
            # Verify AuditLog.log was not called
            mock_audit_log.log.assert_not_called()

    def test_log_account_locked_with_audit_enabled(self):
        """Test that account locking is logged when audit logging is enabled."""
        # Create user first before patching to avoid bcrypt issues
        user = User.objects.create(email="lock@test.com", is_active=True, password="")
        
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = True
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Connect a mock to the account_locked signal to verify it's sent
                signal_handler = MagicMock()
                account_locked.connect(signal_handler)
                
                try:
                    # Trigger the post_save signal by locking the account
                    user.is_locked = True
                    user.save(update_fields=['is_locked'])
                    
                    # Verify AuditLog.log was called exactly once
                    mock_audit_log.log.assert_called_once_with(
                        action='account_locked',
                        user=user,
                        details={'reason': 'too_many_failed_attempts'}
                    )
                    
                    # Verify the public signal was sent
                    signal_handler.assert_called_once()
                    args, kwargs = signal_handler.call_args
                    assert kwargs["user"] == user
                    assert kwargs["reason"] == "too_many_failed_attempts"
                finally:
                    account_locked.disconnect(signal_handler)

    def test_log_account_locked_with_audit_disabled(self):
        """Test that account locking is not logged when audit logging is disabled."""
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = False
            mock_settings.BCRYPT_ROUNDS = 4  # Lower rounds for testing
            
            user = User.objects.create(email="lock2@test.com", is_active=True, password="")
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Connect a mock to the account_locked signal
                signal_handler = MagicMock()
                account_locked.connect(signal_handler)
                
                try:
                    # Trigger the post_save signal by locking the account
                    user.is_locked = True
                    user.save(update_fields=['is_locked'])
                    
                    # Verify AuditLog.log was not called
                    mock_audit_log.log.assert_not_called()
                    
                    # Verify the public signal was not sent
                    signal_handler.assert_not_called()
                finally:
                    account_locked.disconnect(signal_handler)

    def test_log_account_locked_update_fields_not_is_locked(self):
        """Test that updates without is_locked in update_fields don't trigger locking logic."""
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = True
            mock_settings.BCRYPT_ROUNDS = 4  # Lower rounds for testing
            
            user = User.objects.create(email="update@test.com", is_active=True, password="")
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Update user without is_locked in update_fields
                user.email = "updated@test.com"
                user.save(update_fields=['email'])
                
                # Verify AuditLog.log was not called
                mock_audit_log.log.assert_not_called()

    def test_audit_user_deletion_audit_logging_disabled_direct(self):
        """Test line 94: audit logging disabled early return."""
        from tenxyte.signals import audit_user_deletion
        
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = False
            mock_settings.BCRYPT_ROUNDS = 4
            
            user = User.objects.create(email="disabled@test.com", is_active=True, password="")
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Call the signal handler directly
                audit_user_deletion(sender=User, instance=user)
                
                # Verify AuditLog.log was NOT called (covers line 94)
                mock_audit_log.log.assert_not_called()

    def test_log_account_locked_model_without_is_locked_direct(self):
        """Test line 127: model without is_locked attribute early return."""
        from tenxyte.signals import log_account_locked
        from tenxyte.models import Application
        
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = True
            
            app = Application.objects.create(name="Test App")
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Mock _get_user_model_label to return Application label so we pass the sender check
                with patch('tenxyte.signals._get_user_model_label', return_value='tenxyte.Application'):
                    # Call the signal handler directly with a model that has no is_locked
                    log_account_locked(sender=Application, instance=app, created=False)
                    
                    # Verify AuditLog.log was NOT called (covers line 127)
                    mock_audit_log.log.assert_not_called()

    def test_log_account_locked_update_fields_not_is_locked_direct(self):
        """Test line 133: update_fields without is_locked early return."""
        from tenxyte.signals import log_account_locked
        
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = True
            mock_settings.BCRYPT_ROUNDS = 4
            
            user = User.objects.create(email="updatefields@test.com", is_active=True, password="", is_locked=True)
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Call the signal handler directly with update_fields not containing is_locked
                log_account_locked(
                    sender=User, 
                    instance=user, 
                    created=False, 
                    update_fields=['email']  # doesn't contain 'is_locked'
                )
                
                # Verify AuditLog.log was NOT called (covers line 133)
                mock_audit_log.log.assert_not_called()

    def test_get_user_model_label_default(self):
        """Test _get_user_model_label returns default when AUTH_USER_MODEL is not set."""
        with patch('tenxyte.signals.settings') as mock_settings:
            del mock_settings.AUTH_USER_MODEL  # Remove the attribute
            
            from tenxyte.signals import _get_user_model_label
            result = _get_user_model_label()
            
            assert result == 'tenxyte.User'

    def test_get_user_model_label_custom(self):
        """Test _get_user_model_label returns custom model when AUTH_USER_MODEL is set."""
        with patch('tenxyte.signals.settings') as mock_settings:
            mock_settings.AUTH_USER_MODEL = 'myapp.CustomUser'
            
            from tenxyte.signals import _get_user_model_label
            result = _get_user_model_label()
            
            assert result == 'myapp.CustomUser'

    def test_log_account_locked_non_user_model(self):
        """Test that non-user models don't trigger account locking logic."""
        from tenxyte.models import Application
        app = Application.objects.create(name="Test App")
        
        with patch('tenxyte.models.AuditLog') as mock_audit_log:
            # Trigger the post_save signal for non-user model
            app.save()
            
            # Verify AuditLog.log was not called
            mock_audit_log.log.assert_not_called()

    def test_log_account_locked_model_without_is_locked(self):
        """Test that models without is_locked attribute don't trigger locking logic."""
        # Create a model instance that doesn't have is_locked
        from tenxyte.models import Application
        app = Application.objects.create(name="Test App")
        
        with patch('tenxyte.models.AuditLog') as mock_audit_log:
            # Trigger the post_save signal
            app.save()
            
            # Verify AuditLog.log was not called (line 127 coverage)
            mock_audit_log.log.assert_not_called()

    def test_log_account_locked_creation_not_logged(self):
        """Test that user creation with is_locked=True is not logged as locking event."""
        with patch('tenxyte.conf.auth_settings') as mock_settings:
            mock_settings.AUDIT_LOGGING_ENABLED = True
            mock_settings.BCRYPT_ROUNDS = 4  # Lower rounds for testing
            
            with patch('tenxyte.models.AuditLog') as mock_audit_log:
                # Create user with is_locked=True (should not trigger locking logic)
                User.objects.create(
                    email="locked@test.com", 
                    is_active=True,
                    is_locked=True,
                    password=""
                )
                
                # Verify AuditLog.log was not called (creation should not trigger)
                mock_audit_log.log.assert_not_called()
