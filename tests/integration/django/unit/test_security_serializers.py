import pytest
from django.utils import timezone
from tenxyte.serializers.security_serializers import (
    AuditLogSerializer,
    LoginAttemptSerializer,
    BlacklistedTokenSerializer,
    RefreshTokenAdminSerializer,
    SessionSerializer,
    DeviceSerializer,
)
from tenxyte.models import (
    AuditLog,
    LoginAttempt,
    BlacklistedToken,
    RefreshToken,
    get_user_model,
    get_application_model
)

User = get_user_model()
Application = get_application_model()


@pytest.mark.django_db
class TestAuditLogSerializer:
    def test_serialization(self):
        user = User.objects.create(email="audit@example.com")
        log = AuditLog.objects.create(
            user=user,
            action="tested",
            ip_address="127.0.0.1",
            details={'test': True}
        )
        serializer = AuditLogSerializer(log)
        data = serializer.data
        
        assert data['user_email'] == "audit@example.com"
        assert data['action'] == "tested"
        assert data['ip_address'] == "127.0.0.1"


@pytest.mark.django_db
class TestLoginAttemptSerializer:
    def test_serialization(self):
        attempt = LoginAttempt.objects.create(
            identifier="test@example.com",
            ip_address="127.0.0.1",
            success=False,
            failure_reason="wrong password"
        )
        serializer = LoginAttemptSerializer(attempt)
        data = serializer.data
        
        assert data['identifier'] == "test@example.com"
        assert data['success'] is False
        assert data['failure_reason'] == "wrong password"


@pytest.mark.django_db
class TestBlacklistedTokenSerializer:
    def test_serialization(self):
        user = User.objects.create(email="black@example.com")
        token = BlacklistedToken.objects.create(
            token_jti="dummy_jti",
            user=user,
            expires_at=timezone.now() - timezone.timedelta(days=1),
            reason="logout"
        )
        serializer = BlacklistedTokenSerializer(token)
        data = serializer.data
        
        assert data['user_email'] == "black@example.com"
        assert data['token_jti'] == "dummy_jti"
        assert data['is_expired'] is True


@pytest.mark.django_db
class TestRefreshTokenAdminSerializer:
    def test_serialization(self):
        user = User.objects.create(email="rt@example.com")
        app, _ = Application.create_application(name="RT App")
        token = RefreshToken.objects.create(
            user=user,
            application=app,
            token="dummy_rt",
            expires_at=timezone.now() + timezone.timedelta(days=1),
            device_info="desktop"
        )
        serializer = RefreshTokenAdminSerializer(token)
        data = serializer.data
        
        assert data['user_email'] == "rt@example.com"
        assert data['application_name'] == "RT App"
        assert data['is_expired'] is False
        assert data['device_info'] == "desktop"


class TestSessionSerializer:
    def test_schema_serialization(self):
        # SessionSerializer is just a schema definition, not tied to a model directly.
        # We can test valid data dictionary serialization.
        data = {
            'id': 'sess_123',
            'user_id': 'user_456',
            'device_info': {'os': 'windows'},
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0',
            'is_current': True,
            'created_at': timezone.now(),
            'last_activity': timezone.now(),
            'expires_at': timezone.now() + timezone.timedelta(days=1)
        }
        # Testing serialization (instance to data)
        serializer = SessionSerializer(instance=data)
        serialized_data = serializer.data
        assert serialized_data['id'] == 'sess_123'
        assert serialized_data['is_current'] is True


class TestDeviceSerializer:
    def test_schema_serialization(self):
        data = {
            'id': 'dev_123',
            'user_id': 'user_456',
            'device_fingerprint': 'fing_789',
            'device_name': 'My PC',
            'device_type': 'desktop',
            'platform': 'Windows',
            'browser': 'Chrome',
            'is_trusted': True,
            'last_seen': timezone.now(),
            'created_at': timezone.now(),
        }
        serializer = DeviceSerializer(instance=data)
        serialized_data = serializer.data
        assert serialized_data['id'] == 'dev_123'
        assert serialized_data['device_name'] == 'My PC'
        assert serialized_data['is_trusted'] is True
