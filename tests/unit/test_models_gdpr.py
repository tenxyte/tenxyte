import pytest
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from tenxyte.models import AccountDeletionRequest, User

@pytest.fixture
def user(db):
    u = User.objects.create(email="gdpr_test@test.com", is_active=True)
    return u

@pytest.mark.django_db
def test_account_deletion_request_str(user):
    req = AccountDeletionRequest.create_request(user=user)
    assert str(req) == f"Deletion request for gdpr_test@test.com - pending"

@pytest.mark.django_db
def test_send_confirmation_email_success(user):
    req = AccountDeletionRequest.create_request(user=user)
    with patch("tenxyte.services.email_service.EmailService") as MockService:
        result = req.send_confirmation_email()
        assert result is True
        assert req.status == 'confirmation_sent'
        MockService.return_value.send_account_deletion_confirmation.assert_called_once_with(req)

@pytest.mark.django_db
def test_send_confirmation_email_failure(user):
    req = AccountDeletionRequest.create_request(user=user)
    with patch("tenxyte.services.email_service.EmailService") as MockService:
        MockService.return_value.send_account_deletion_confirmation.side_effect = Exception("Email failed")
        result = req.send_confirmation_email()
        assert result is False
        assert req.status == 'confirmation_sent'
        
        from tenxyte.models.security import AuditLog
        log = AuditLog.objects.get(action='deletion_confirmation_email_failed', user=user)
        assert log.details['error'] == "Email failed"

@pytest.mark.django_db
def test_execute_deletion_not_confirmed(user):
    req = AccountDeletionRequest.create_request(user=user)
    assert req.execute_deletion() is False

@pytest.mark.django_db
def test_execute_deletion_success_and_email_success(user):
    req = AccountDeletionRequest.create_request(user=user)
    req.confirm_request()
    
    with patch.object(user, 'soft_delete', return_value=True):
        with patch("tenxyte.services.email_service.EmailService") as MockService:
            result = req.execute_deletion()
            assert result is True
            assert req.status == 'completed'
            MockService.return_value.send_account_deletion_completed.assert_called_once_with(req)

@pytest.mark.django_db
def test_execute_deletion_success_email_failure(user):
    req = AccountDeletionRequest.create_request(user=user)
    req.confirm_request()
    
    with patch.object(user, 'soft_delete', return_value=True):
        with patch("tenxyte.services.email_service.EmailService") as MockService:
            MockService.return_value.send_account_deletion_completed.side_effect = Exception("Failed")
            result = req.execute_deletion()
            assert result is True
            assert req.status == 'completed'
            
            from tenxyte.models.security import AuditLog
            log = AuditLog.objects.get(action='deletion_completion_email_failed', user=user)
            assert log.details['error'] == "Failed"

@pytest.mark.django_db
def test_execute_deletion_soft_delete_fails(user):
    req = AccountDeletionRequest.create_request(user=user)
    req.confirm_request()
    
    with patch.object(user, 'soft_delete', return_value=False):
        result = req.execute_deletion()
        assert result is False
        assert req.status == 'confirmed'

@pytest.mark.django_db
def test_is_grace_period_expired():
    req = AccountDeletionRequest()
    req.grace_period_ends_at = None
    assert req.is_grace_period_expired() is False
    
    req.grace_period_ends_at = timezone.now() - timedelta(days=1)
    assert req.is_grace_period_expired() is True
    
    req.grace_period_ends_at = timezone.now() + timedelta(days=1)
    assert req.is_grace_period_expired() is False
