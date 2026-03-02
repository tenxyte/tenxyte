import pytest
from unittest.mock import MagicMock
from django.conf import settings
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
            
        from tenxyte.models import LoginAttempt
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
