import pytest
from unittest.mock import patch
from tenxyte.services.email_service import EmailService
from tenxyte.models import User, AccountDeletionRequest

class TestLegacyEmailServiceExtras:
    
    def test_send_welcome_email(self):
        service = EmailService()
        
        with patch.object(service, "send_email", return_value=True) as mock_send:
            res = service.send_welcome_email("test@example.com")
            assert res is True
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            msg_content = kwargs.get('message', '')
            if not msg_content and args and len(args) > 2:
                msg_content = args[2]
            assert "Bonjour," in msg_content
            
            mock_send.reset_mock()
            
            res = service.send_welcome_email("test@example.com", first_name="Alice")
            assert res is True
            args, kwargs = mock_send.call_args
            msg_content = kwargs.get('message', '')
            if not msg_content and args and len(args) > 2:
                msg_content = args[2]
            assert "Bonjour Alice," in msg_content

    def test_send_magic_link_email(self):
        service = EmailService()
        
        with patch.object(service, "send_email", return_value=True) as mock_send:
            res = service.send_magic_link_email("test@example.com", token="abc-123", validation_url="http://validate")
            assert res is True
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            msg_content = kwargs.get('message', '')
            if not msg_content and args and len(args) > 2:
                msg_content = args[2]
            assert "http://validate?token=abc-123" in msg_content

    @pytest.mark.django_db
    def test_send_account_deletion_confirmation(self):
        service = EmailService()
        
        user = User.objects.create(email="del_conf_extra@test.com", is_active=True)
        user.set_password("pass123")
        user.save()
        
        with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
            del_req = AccountDeletionRequest.create_request(
                user=user, ip_address="1.1.1.1", user_agent="test"
            )
        
        with patch.object(service, "_send_template_email", return_value=True) as mock_send:
            res = service.send_account_deletion_confirmation(del_req)
            assert res is True
            mock_send.assert_called_once()
            
        with patch.object(service, "_send_template_email", side_effect=Exception("Render error")):
            res = service.send_account_deletion_confirmation(del_req)
            assert res is False

    def test_send_email_direct(self):
        service = EmailService()
        with patch.object(service.backend, "send_email", return_value=True) as mock_send:
            res = service.send_email("to@example.com", "Subj", "Msg")
            assert res is True
            mock_send.assert_called_once()
            
    def test_send_otp_email(self):
        service = EmailService()
        with patch.object(service, "send_email", return_value=True) as mock_send:
            # test standard path
            res = service.send_otp_email("test@example.com", "123456", otp_type="verification")
            assert res is True
            mock_send.assert_called_once()
            kwargs = mock_send.call_args.kwargs
            assert "123456" in kwargs['message']
            assert "Code de vérification" in kwargs['subject']

            mock_send.reset_mock()
            # test fallback subject path
            res = service.send_otp_email("test@example.com", "123456", otp_type="unknown_type")
            assert res is True
            kwargs = mock_send.call_args.kwargs
            assert "Tenxyte - Votre code" in kwargs['subject']
            
    def test_send_security_alert_email(self):
        service = EmailService()
        with patch.object(service, "send_email", return_value=True) as mock_send:
            # Test known alert type with IP and device
            res = service.send_security_alert_email(
                "test@example.com", 
                alert_type="new_login", 
                details={"ip": "127.0.0.1", "device": "Chrome"},
                first_name="Alice"
            )
            assert res is True
            mock_send.assert_called_once()
            kwargs = mock_send.call_args.kwargs
            assert "Nouvelle connexion" in kwargs['subject']
            assert "127.0.0.1" in kwargs['message']
            assert "Chrome" in kwargs['message']
            
            mock_send.reset_mock()
            
            # Test unknown alert type and no details/first_name
            res = service.send_security_alert_email("test@example.com", alert_type="unknown")
            assert res is True
            kwargs = mock_send.call_args.kwargs
            assert "Alerte de sécurité" in kwargs['subject']
            assert "Bonjour," in kwargs['message']
            assert "Inconnue" not in kwargs['message']
