"""
Tests email_service.py - Account deletion email methods.

Coverage cible : services/email_service.py méthodes account deletion (30% → ~60%)
"""

import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta

from tenxyte.models import User, AccountDeletionRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(email):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


def _make_deletion_request(user, status_val="pending"):
    with patch.object(AccountDeletionRequest, 'send_confirmation_email', return_value=None):
        req = AccountDeletionRequest.create_request(
            user=user, ip_address="1.2.3.4", user_agent="test"
        )
    req.status = status_val
    req.reason = "Test reason"
    req.save()
    return req


# ===========================================================================
# send_account_deletion_confirmed
# ===========================================================================

class TestSendAccountDeletionConfirmed:

    @pytest.mark.django_db
    def test_sends_email_successfully(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_confirmed_email@test.com")
        del_req = _make_deletion_request(user, "confirmed")
        del_req.grace_period_ends_at = timezone.now() + timedelta(days=30)
        del_req.save()

        service = EmailService()
        mock_site = MagicMock()
        mock_site.domain = 'testserver'
        with patch('django.contrib.sites.shortcuts.get_current_site', return_value=mock_site), \
             patch.object(service, '_send_template_email', return_value=True) as mock_send:
            result = service.send_account_deletion_confirmed(del_req)

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.django_db
    def test_returns_false_on_exception(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_confirmed_fail@test.com")
        del_req = _make_deletion_request(user)
        del_req.grace_period_ends_at = timezone.now() + timedelta(days=30)
        del_req.save()

        service = EmailService()
        mock_site = MagicMock()
        mock_site.domain = 'testserver'
        with patch('django.contrib.sites.shortcuts.get_current_site', return_value=mock_site), \
             patch.object(service, '_send_template_email', side_effect=Exception("SMTP error")):
            result = service.send_account_deletion_confirmed(del_req)

        assert result is False

    @pytest.mark.django_db
    def test_context_contains_required_fields(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_confirmed_ctx@test.com")
        del_req = _make_deletion_request(user, "confirmed")
        del_req.grace_period_ends_at = timezone.now() + timedelta(days=30)
        del_req.save()

        service = EmailService()
        captured_context = {}

        def capture_send(**kwargs):
            captured_context.update(kwargs.get('context', {}))
            return True

        mock_site = MagicMock()
        mock_site.domain = 'testserver'
        with patch('django.contrib.sites.shortcuts.get_current_site', return_value=mock_site), \
             patch.object(service, '_send_template_email', side_effect=capture_send):
            service.send_account_deletion_confirmed(del_req)

        assert 'user' in captured_context
        assert 'cancel_url' in captured_context
        assert 'days_remaining' in captured_context
        assert captured_context['days_remaining'] >= 0

    @pytest.mark.django_db
    def test_no_grace_period_days_remaining_is_zero(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_confirmed_nograce@test.com")
        del_req = _make_deletion_request(user)
        del_req.grace_period_ends_at = None
        del_req.save()

        service = EmailService()
        captured_context = {}

        def capture_send(**kwargs):
            captured_context.update(kwargs.get('context', {}))
            return True

        mock_site = MagicMock()
        mock_site.domain = 'testserver'
        with patch('django.contrib.sites.shortcuts.get_current_site', return_value=mock_site), \
             patch.object(service, '_send_template_email', side_effect=capture_send):
            service.send_account_deletion_confirmed(del_req)

        # grace_period_ends_at is None so days_remaining should be 0
        assert captured_context.get('days_remaining', 0) == 0

    @pytest.mark.django_db
    def test_calls_send_template_email_with_correct_template(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_confirmed_tmpl@test.com")
        del_req = _make_deletion_request(user, "confirmed")
        del_req.grace_period_ends_at = timezone.now() + timedelta(days=30)
        del_req.save()

        service = EmailService()
        mock_site = MagicMock()
        mock_site.domain = 'testserver'
        with patch('django.contrib.sites.shortcuts.get_current_site', return_value=mock_site), \
             patch.object(service, '_send_template_email', return_value=True) as mock_send:
            service.send_account_deletion_confirmed(del_req)

        call_kwargs = mock_send.call_args.kwargs if mock_send.call_args else {}
        template = call_kwargs.get('template_name', '')
        assert 'account_deletion_confirmed' in template


# ===========================================================================
# send_account_deletion_completed
# ===========================================================================

class TestSendAccountDeletionCompleted:

    @pytest.mark.django_db
    def test_sends_email_successfully(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_completed_email@test.com")
        del_req = _make_deletion_request(user, "completed")
        del_req.confirmed_at = timezone.now()
        del_req.completed_at = timezone.now()
        del_req.save()

        service = EmailService()
        with patch.object(service, '_send_template_email', return_value=True) as mock_send:
            result = service.send_account_deletion_completed(del_req)

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.django_db
    def test_returns_false_on_exception(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_completed_fail@test.com")
        del_req = _make_deletion_request(user)

        service = EmailService()
        with patch.object(service, '_send_template_email', side_effect=Exception("error")):
            result = service.send_account_deletion_completed(del_req)

        assert result is False

    @pytest.mark.django_db
    def test_context_contains_required_fields(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_completed_ctx@test.com")
        del_req = _make_deletion_request(user, "completed")
        del_req.confirmed_at = timezone.now()
        del_req.completed_at = timezone.now()
        del_req.save()

        service = EmailService()
        captured_context = {}

        def capture_send(**kwargs):
            captured_context.update(kwargs.get('context', {}))
            return True

        with patch.object(service, '_send_template_email', side_effect=capture_send):
            service.send_account_deletion_completed(del_req)

        assert len(captured_context) > 0
        assert 'user_email' in captured_context
        assert 'requested_at' in captured_context
        assert 'reason' in captured_context


# ===========================================================================
# send_deletion_request_rejected
# ===========================================================================

class TestSendDeletionRequestRejected:

    @pytest.mark.django_db
    def test_sends_email_successfully(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_rejected_email@test.com")
        del_req = _make_deletion_request(user, "cancelled")
        del_req.admin_notes = "Not valid request"
        del_req.save()

        service = EmailService()
        mock_site = MagicMock()
        mock_site.domain = 'testserver'
        with patch('django.contrib.sites.shortcuts.get_current_site', return_value=mock_site), \
             patch.object(service, '_send_template_email', return_value=True) as mock_send:
            result = service.send_deletion_request_rejected(del_req)

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.django_db
    def test_returns_false_on_exception(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_rejected_fail@test.com")
        del_req = _make_deletion_request(user)

        service = EmailService()
        with patch.object(service, '_send_template_email', side_effect=Exception("error")):
            result = service.send_deletion_request_rejected(del_req)

        assert result is False

    @pytest.mark.django_db
    def test_context_contains_required_fields(self):
        from tenxyte.services.email_service import EmailService
        user = _user("del_rejected_ctx@test.com")
        del_req = _make_deletion_request(user, "cancelled")
        del_req.admin_notes = "Rejected by admin"
        del_req.save()

        service = EmailService()
        captured_context = {}

        def capture_send(**kwargs):
            captured_context.update(kwargs.get('context', {}))
            return True

        mock_site = MagicMock()
        mock_site.domain = 'testserver'
        with patch('django.contrib.sites.shortcuts.get_current_site', return_value=mock_site), \
             patch.object(service, '_send_template_email', side_effect=capture_send):
            service.send_deletion_request_rejected(del_req)

        assert len(captured_context) > 0
        assert 'user' in captured_context
        assert 'login_url' in captured_context
        assert 'admin_notes' in captured_context
        assert captured_context['admin_notes'] == "Rejected by admin"


# ===========================================================================
# _send_template_email (internal)
# ===========================================================================

class TestSendTemplateEmail:

    @pytest.mark.django_db
    def test_returns_true_on_success(self):
        from tenxyte.services.email_service import EmailService
        service = EmailService()

        # render_to_string and EmailMultiAlternatives are imported locally inside the method
        with patch('django.template.loader.render_to_string', return_value='<html>test</html>'), \
             patch('django.core.mail.EmailMultiAlternatives') as MockEmail:
            mock_instance = MagicMock()
            MockEmail.return_value = mock_instance
            result = service._send_template_email(
                to_email="test@test.com",
                subject="Test Subject",
                template_name="emails/test.html",
                context={}
            )

        assert result is True
        mock_instance.send.assert_called_once()

    @pytest.mark.django_db
    def test_returns_false_on_exception(self):
        from tenxyte.services.email_service import EmailService
        service = EmailService()

        with patch('django.template.loader.render_to_string', side_effect=Exception("Template not found")):
            result = service._send_template_email(
                to_email="test@test.com",
                subject="Test",
                template_name="emails/nonexistent.html",
                context={}
            )

        assert result is False


# ===========================================================================
# _generate_text_alternative
# ===========================================================================

class TestGenerateTextAlternative:

    def test_strips_html_tags(self):
        from tenxyte.services.email_service import EmailService
        service = EmailService()
        html = "<h1>Hello</h1><p>World</p>"
        result = service._generate_text_alternative(html)
        assert "<h1>" not in result
        assert "Hello" in result
        assert "World" in result

    def test_collapses_whitespace(self):
        from tenxyte.services.email_service import EmailService
        service = EmailService()
        html = "<p>Hello   World</p>"
        result = service._generate_text_alternative(html)
        assert "  " not in result

    def test_empty_html_returns_empty(self):
        from tenxyte.services.email_service import EmailService
        service = EmailService()
        result = service._generate_text_alternative("")
        assert result == ""
