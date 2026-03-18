import pytest
from unittest.mock import patch, PropertyMock
from datetime import timedelta

# AuthService removed - use core services instead
# from tenxyte.core.jwt_service import JWTService
from tenxyte.models import Application, User, RefreshToken
from tests.integration.django.auth_service_compat import AuthService

@pytest.fixture
def user(db):
    user = User.objects.create(email="auth_cov@test.com")
    user.set_password("pass")
    user.save()
    return user

@pytest.fixture
def application(db):
    return Application.objects.create(name="Test App")

@pytest.mark.django_db
class TestAuthServiceCoverage:
    def test_validate_application_success(self, application):
        service = AuthService()
        app, raw_secret = Application.create_application(name="Valid App")
        success, returned_app, msg = service.validate_application(app.access_key, raw_secret)
        assert success is True
        assert returned_app.id == app.id
        assert msg == ''

    def test_refresh_access_token_extra_claims(self, user, application):
        service = AuthService()
        rt = RefreshToken.generate(user=user, application=application, ip_address="127.0.0.1", device_info="Mozilla/5.0")
        
        success, data, msg = service.refresh_access_token(
            rt.raw_token,
            application
        )
        assert success is True
        assert data is not None

    def test_generate_tokens_for_user_device_claim(self, user, application):
        service = AuthService()
        service.generate_tokens_for_user(
            user=user,
            application=application,
            ip_address="10.0.0.1",
            device_info="Mozilla/5.0" # triggers extra_claims['device']
        )
    @patch('tenxyte.conf.security.SecuritySettingsMixin.SESSION_LIMIT_ENABLED', new_callable=PropertyMock, return_value=True)
    @patch('tenxyte.conf.security.SecuritySettingsMixin.DEFAULT_MAX_SESSIONS', new_callable=PropertyMock, return_value=0)
    def test_enforce_session_limit_zero(self, mock_max, mock_enabled, user, application):
        service = AuthService()
        ok, msg = service._enforce_session_limit(user, application)
        assert ok is True
        assert msg == ""

    @patch('tenxyte.conf.security.SecuritySettingsMixin.DEVICE_LIMIT_ENABLED', new_callable=PropertyMock, return_value=True)
    @patch('tenxyte.conf.security.SecuritySettingsMixin.DEFAULT_MAX_DEVICES', new_callable=PropertyMock, return_value=0)
    def test_enforce_device_limit_zero(self, mock_max, mock_enabled, user, application):
        service = AuthService()
        ok, msg = service._enforce_device_limit(user, application, "device_info")
        assert ok is True
        assert msg == ""

    @patch('tenxyte.conf.security.SecuritySettingsMixin.SESSION_LIMIT_ENABLED', new_callable=PropertyMock, return_value=True)
    @patch('tenxyte.conf.security.SecuritySettingsMixin.DEFAULT_MAX_SESSIONS', new_callable=PropertyMock, return_value=1)
    @patch('tenxyte.conf.security.SecuritySettingsMixin.DEFAULT_SESSION_LIMIT_ACTION', new_callable=PropertyMock, return_value='deny')
    @patch('django.utils.timezone.now')
    def test_enforce_session_limit_zombies(self, mock_now, mock_action, mock_max, mock_enabled, user, application):
        import datetime
        tbase = datetime.datetime.now(datetime.timezone.utc)
        
        class TimeMocker:
            def __init__(self, start):
                self.times = [start, start + timedelta(seconds=2)]
                self.idx = 0
            def __call__(self):
                t = self.times[self.idx]
                if self.idx < len(self.times) - 1:
                    self.idx += 1
                return t
                
        # Active token that will expire between the counts
        # We ensure mock_now returns tbase temporarily for generate()
        mock_now.return_value = tbase
        rt = RefreshToken.generate(user=user, application=application, ip_address="127.0.0.1")
        RefreshToken.objects.filter(id=rt.id).update(expires_at=tbase + timedelta(seconds=1))

        # Hook TimeMocker for the method executions
        mock_now.side_effect = TimeMocker(tbase)

        user.max_sessions = 1
        user.save()

        service = AuthService()
        ok, msg = service._enforce_session_limit(user, application)
        assert ok is True
        assert msg == ""

    @patch('tenxyte.conf.security.SecuritySettingsMixin.DEVICE_LIMIT_ENABLED', new_callable=PropertyMock, return_value=True)
    @patch('tenxyte.conf.security.SecuritySettingsMixin.DEFAULT_MAX_DEVICES', new_callable=PropertyMock, return_value=1)
    @patch('tenxyte.conf.security.SecuritySettingsMixin.DEVICE_LIMIT_ACTION', new_callable=PropertyMock, return_value='deny')
    @patch('django.utils.timezone.now')
    def test_enforce_device_limit_zombies(self, mock_now, mock_action, mock_max, mock_enabled, user, application):
        import datetime
        tbase = datetime.datetime.now(datetime.timezone.utc)
        
        class TimeMocker:
            def __init__(self, start):
                self.times = [start, start + timedelta(seconds=2)]
                self.idx = 0
            def __call__(self):
                t = self.times[self.idx]
                if self.idx < len(self.times) - 1:
                    self.idx += 1
                return t
                
        mock_now.return_value = tbase
        
        # Active token with no device info (handles unknown device branch)
        rt1 = RefreshToken.generate(user=user, application=application, ip_address="127.0.0.1", device_info="")
        RefreshToken.objects.filter(id=rt1.id).update(expires_at=tbase + timedelta(seconds=1))

        # Active token with device info 
        rt2 = RefreshToken.generate(user=user, application=application, ip_address="127.0.0.1", device_info="Device 1")
        RefreshToken.objects.filter(id=rt2.id).update(expires_at=tbase + timedelta(seconds=1))
        
        # Hook TimeMocker for the logical checks
        mock_now.side_effect = TimeMocker(tbase)
        
        user.max_devices = 1
        user.save()

        service = AuthService()
        ok, msg = service._enforce_device_limit(user, application, "New Device")
        assert ok is True
        assert msg == ""
