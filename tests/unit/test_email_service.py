import pytest
from unittest.mock import patch, MagicMock

from tenxyte.models import User, AccountDeletionRequest
from tenxyte.services.email_service import EmailService

@pytest.fixture
def user(db):
    u = User.objects.create(email="test_email_svc@test.com", is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u

@pytest.mark.django_db
def test_send_welcome_email():
    service = EmailService()
    
    with patch.object(service, 'send_email', return_value=True) as mock_send:
        result = service.send_welcome_email(
            to_email="newuser@test.com",
            first_name="John",
            app_name="TestApp"
        )
        
    assert result is True
    mock_send.assert_called_once()
    call_args = mock_send.call_args.kwargs
    assert call_args['to_email'] == "newuser@test.com"
    assert "Bienvenue sur TestApp" in call_args['subject']
    assert "John," in call_args['message']
    assert "John," in call_args['html_message']

@pytest.mark.django_db
def test_send_magic_link_email():
    service = EmailService()
    
    with patch.object(service, 'send_email', return_value=True) as mock_send:
        result = service.send_magic_link_email(
            to_email="magic@test.com",
            token="test-token-123",
            first_name="Jane",
            expiry_minutes=30,
            app_name="TestApp",
            validation_url="https://test.com/magic/"
        )
        
    assert result is True
    mock_send.assert_called_once()
    call_args = mock_send.call_args.kwargs
    assert call_args['to_email'] == "magic@test.com"
    assert "Votre lien de connexion" in call_args['subject']
    assert "Jane," in call_args['message']
    assert "https://test.com/magic/?token=test-token-123" in call_args['message']
    assert "https://test.com/magic/?token=test-token-123" in call_args['html_message']

@pytest.mark.django_db
def test_send_account_deletion_confirmation(user):
    from django.utils import timezone
    service = EmailService()
    
    with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
        req = AccountDeletionRequest.create_request(
            user=user, ip_address="1.2.3.4", user_agent="test"
        )
    
    mock_site = MagicMock()
    mock_site.domain = 'testserver.com'
    with patch('django.contrib.sites.shortcuts.get_current_site', return_value=mock_site), \
         patch.object(service, '_send_template_email', return_value=True) as mock_send:
        result = service.send_account_deletion_confirmation(req)
        
    assert result is True
    mock_send.assert_called_once()
    call_args = mock_send.call_args.kwargs
    assert call_args['to_email'] == user.email
    assert "Confirmez votre demande de suppression" in call_args['subject']
    assert 'account_deletion_confirmation.html' in call_args['template_name']
    assert call_args['context']['user'] == user
    assert req.confirmation_token in call_args['context']['confirmation_url']

@pytest.mark.django_db
def test_send_account_deletion_confirmation_failure(user):
    service = EmailService()
    
    with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
        req = AccountDeletionRequest.create_request(
            user=user, ip_address="1.2.3.4", user_agent="test"
        )
    
    with patch('django.contrib.sites.shortcuts.get_current_site', side_effect=Exception("Failed to get site")):
        result = service.send_account_deletion_confirmation(req)
        
    assert result is False
