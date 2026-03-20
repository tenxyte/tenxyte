import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from tenxyte.admin import (
    UserAdmin, RefreshTokenAdmin, BlacklistedTokenAdmin, AccountDeletionRequestAdmin
)
from tenxyte.models import (
    get_user_model, get_role_model, get_permission_model, get_application_model,
    RefreshToken, AuditLog, BlacklistedToken, AccountDeletionRequest
)
from tenxyte.conf import org_settings

# Conditional Organization Imports
if org_settings.ORGANIZATIONS_ENABLED:
    from tenxyte.admin import (
        OrganizationAdmin, OrganizationMembershipAdmin, OrganizationInvitationAdmin
    )
    from tenxyte.models import (
        get_organization_model, get_organization_role_model, get_organization_membership_model, OrganizationInvitation
    )
    Organization = get_organization_model()
    OrganizationRole = get_organization_role_model()
    OrganizationMembership = get_organization_membership_model()

User = get_user_model()
Role = get_role_model()
Permission = get_permission_model()
Application = get_application_model()

@pytest.fixture
def admin_site():
    return AdminSite()

@pytest.fixture
def rf():
    return RequestFactory()

@pytest.fixture
def superuser(db):
    user = User.objects.create_superuser(
        email='admin@example.com',
        password='adminpassword',
        first_name='Admin',
        last_name='User'
    )
    return user

@pytest.mark.django_db
class TestUserAdmin:
    def test_ban_users(self, admin_site, rf, superuser):
        user1 = User.objects.create_user(email='user1@example.com', password='password')
        User.objects.create_user(email='user2@example.com', password='password', is_banned=True)
        
        request = rf.post('/')
        request.user = superuser
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        admin = UserAdmin(User, admin_site)
        queryset = User.objects.filter(id=user1.id)
        
        # Test ban_users
        with patch.object(admin, 'message_user') as mock_message:
            admin.ban_users(request, queryset)
            
        user1.refresh_from_db()
        assert user1.is_banned is True
        mock_message.assert_called_once()
        
        # Audit log should be created
        assert AuditLog.objects.filter(action='user_banned', user=user1).exists()

    def test_unban_users(self, admin_site, rf, superuser):
        user1 = User.objects.create_user(email='user1@example.com', password='password', is_banned=True)
        
        request = rf.post('/')
        request.user = superuser
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.1, 10.0.0.1'
        
        admin = UserAdmin(User, admin_site)
        queryset = User.objects.filter(id=user1.id)
        
        # Test unban_users
        with patch.object(admin, 'message_user') as mock_message:
            admin.unban_users(request, queryset)
            
        user1.refresh_from_db()
        assert user1.is_banned is False
        mock_message.assert_called_once()
        
        # Audit log should be created
        assert AuditLog.objects.filter(action='user_unbanned', user=user1).exists()

    def test_get_actions(self, admin_site, rf, superuser):
        user1 = User.objects.create_user(email='user1@example.com', password='password')
        user_banned = User.objects.create_user(email='banned@example.com', password='password', is_banned=True)
        
        admin = UserAdmin(User, admin_site)
        
        # Test without selected users
        request = rf.post('/')
        request.user = superuser
        actions = admin.get_actions(request)
        assert 'ban_users' in actions
        assert 'unban_users' in actions
        
        # Test with banned user selected (should not show ban_users)
        request = rf.post('/', {'_selected_action': [str(user_banned.id)]})
        request.user = superuser
        actions = admin.get_actions(request)
        assert 'ban_users' not in actions
        assert 'unban_users' in actions
        
        # Test with unbanned user selected (should not show unban_users)
        request = rf.post('/', {'_selected_action': [str(user1.id)]})
        request.user = superuser
        actions = admin.get_actions(request)
        assert 'ban_users' in actions
        assert 'unban_users' not in actions


@pytest.mark.django_db
class TestOtherAdmins:
    def test_refresh_token_admin_short_desc(self, admin_site):
        admin = RefreshTokenAdmin(RefreshToken, admin_site)
        token = RefreshToken(token="a"*50)
        assert admin.token_short(token) == "aaaaaaaaaaaaaaaaaaaa..."
        token_empty = RefreshToken(token="")
        assert admin.token_short(token_empty) == "-"

    def test_blacklisted_token_admin_short_desc(self, admin_site):
        admin = BlacklistedTokenAdmin(BlacklistedToken, admin_site)
        token = BlacklistedToken(token_jti="b"*50)
        assert admin.token_jti_short(token) == "bbbbbbbbbbbbbbbbbbbb..."
        token_empty = BlacklistedToken(token_jti="")
        assert admin.token_jti_short(token_empty) == "-"

    def test_user_admin_get_client_ip(self, admin_site, rf):
        admin = UserAdmin(User, admin_site)
        req1 = rf.get('/')
        req1.META['HTTP_X_FORWARDED_FOR'] = '1.1.1.1, 2.2.2.2'
        assert admin._get_client_ip(req1) == '1.1.1.1'
        
        req2 = rf.get('/')
        req2.META.pop('HTTP_X_FORWARDED_FOR', None)
        req2.META['REMOTE_ADDR'] = '3.3.3.3'
        assert admin._get_client_ip(req2) == '3.3.3.3'


@pytest.mark.django_db
class TestAccountDeletionRequestAdmin:
    def test_user_email(self, admin_site):
        admin = AccountDeletionRequestAdmin(AccountDeletionRequest, admin_site)
        user = User(email="test@example.com")
        req = AccountDeletionRequest(user=user)
        assert admin.user_email(req) == "test@example.com"
        
        req_no_u = MagicMock()
        req_no_u.user = None
        assert admin.user_email(req_no_u) == "N/A"

    def test_days_remaining(self, admin_site):
        admin = AccountDeletionRequestAdmin(AccountDeletionRequest, admin_site)
        now = timezone.now()
        
        req_future = AccountDeletionRequest(grace_period_ends_at=now + timedelta(days=2, hours=1))
        assert "2 days" in admin.days_remaining(req_future)
        
        req_soon = AccountDeletionRequest(grace_period_ends_at=now + timedelta(hours=5, minutes=1))
        assert "4 hours" in admin.days_remaining(req_soon) or "5 hours" in admin.days_remaining(req_soon)
        
        req_past = AccountDeletionRequest(grace_period_ends_at=now - timedelta(days=1))
        assert admin.days_remaining(req_past) == "Expired"
        
        req_none = AccountDeletionRequest(grace_period_ends_at=None)
        assert admin.days_remaining(req_none) == "-"

    @patch('tenxyte.services.account_deletion_service.AccountDeletionService.admin_process_request')
    def test_actions(self, mock_process, admin_site, rf, superuser):
        mock_process.return_value = (True, "Success")
        
        admin = AccountDeletionRequestAdmin(AccountDeletionRequest, admin_site)
        request = rf.post('/')
        request.user = superuser
        
        user = User.objects.create_user(email="del@example.com", password="pwd")
        req1 = AccountDeletionRequest.objects.create(user=user, status='confirmation_sent', confirmation_token="tok1")
        req2 = AccountDeletionRequest.objects.create(user=user, status='pending', confirmation_token="tok2")
        req3 = AccountDeletionRequest.objects.create(user=user, status='confirmed', confirmation_token="tok3")
        
        # test approve_requests
        with patch.object(admin, 'message_user') as mock_msg:
            admin.approve_requests(request, AccountDeletionRequest.objects.filter(id=req1.id))
            assert mock_process.call_count == 1
            mock_msg.assert_called_once()
            
            # test empty
            mock_process.reset_mock()
            mock_msg.reset_mock()
            admin.approve_requests(request, AccountDeletionRequest.objects.filter(id=req3.id))
            assert mock_process.call_count == 0
            mock_msg.assert_called_once()
            
        mock_process.reset_mock()
            
        # test reject_requests
        with patch.object(admin, 'message_user'):
            admin.reject_requests(request, AccountDeletionRequest.objects.filter(id=req2.id))
            assert mock_process.call_count == 1
            
            mock_process.reset_mock()
            admin.reject_requests(request, AccountDeletionRequest.objects.filter(id=req3.id))
            assert mock_process.call_count == 0
            
        mock_process.reset_mock()

        # test cancel_requests
        with patch.object(admin, 'message_user'):
            admin.cancel_requests(request, AccountDeletionRequest.objects.filter(id=req1.id))
            assert mock_process.call_count == 1
            
            mock_process.reset_mock()
            req_completed = AccountDeletionRequest.objects.create(user=user, status='completed', confirmation_token="tok4")
            admin.cancel_requests(request, AccountDeletionRequest.objects.filter(id=req_completed.id))
            assert mock_process.call_count == 0

        mock_process.reset_mock()

        # test execute_requests
        with patch.object(admin, 'message_user'):
            admin.execute_requests(request, AccountDeletionRequest.objects.filter(id=req3.id))
            assert mock_process.call_count == 1
            
            mock_process.reset_mock()
            admin.execute_requests(request, AccountDeletionRequest.objects.filter(id=req1.id))
            assert mock_process.call_count == 0

    def test_get_actions(self, admin_site, rf, superuser):
        admin = AccountDeletionRequestAdmin(AccountDeletionRequest, admin_site)
        user = User.objects.create_user(email="sel@example.com", password="pwd")
        req = AccountDeletionRequest.objects.create(user=user, status='confirmed', confirmation_token="tok5")
        req_sent = AccountDeletionRequest.objects.create(user=user, status='confirmation_sent', confirmation_token="tok6")
        
        request = rf.post('/')
        request.user = superuser
        request._selected_obj = AccountDeletionRequest.objects.filter(id=req.id)
        
        actions = admin.get_actions(request)
        assert 'execute_requests' in actions
        assert 'cancel_requests' in actions
        assert 'approve_requests' not in actions
        assert 'reject_requests' not in actions
        
        request._selected_obj = AccountDeletionRequest.objects.filter(id=req_sent.id)
        actions2 = admin.get_actions(request)
        assert 'approve_requests' in actions2
        assert 'reject_requests' in actions2
        
        req_completed = AccountDeletionRequest.objects.create(user=user, status='completed', confirmation_token="tok7")
        request._selected_obj = AccountDeletionRequest.objects.filter(id=req_completed.id)
        actions3 = admin.get_actions(request)
        assert 'cancel_requests' not in actions3
        assert 'execute_requests' not in actions3

if org_settings.ORGANIZATIONS_ENABLED:
    @pytest.mark.django_db
    class TestOrganizationAdmins:
        def test_member_count(self, admin_site):
            admin = OrganizationAdmin(Organization, admin_site)
            org = Organization(name="Test Org")
            with patch.object(org, 'get_member_count', return_value=5):
                assert admin.member_count(org) == 5
                
        def test_membership_properties(self, admin_site):
            admin = OrganizationMembershipAdmin(OrganizationMembership, admin_site)
            user = User(email="t1@example.com")
            org = Organization(name="Test Org")
            role = OrganizationRole(name="Admin")
            mem = OrganizationMembership(user=user, organization=org, role=role)
            
            assert admin.user_email(mem) == "t1@example.com"
            assert admin.organization_name(mem) == "Test Org"
            assert admin.role_name(mem) == "Admin"
            
            mem_empty = MagicMock()
            mem_empty.user = None
            mem_empty.organization = None
            mem_empty.role = None
            assert admin.user_email(mem_empty) == "N/A"
            assert admin.organization_name(mem_empty) == "N/A"
            assert admin.role_name(mem_empty) == "N/A"

        def test_invitation_properties(self, admin_site):
            admin = OrganizationInvitationAdmin(OrganizationInvitation, admin_site)
            org = Organization(name="Test Org")
            role = OrganizationRole(name="Admin")
            inviter = User(email="inviter@example.com")
            
            inv = OrganizationInvitation(organization=org, role=role, invited_by=inviter)
            assert admin.organization_name(inv) == "Test Org"
            assert admin.role_name(inv) == "Admin"
            assert admin.invited_by_email(inv) == "inviter@example.com"
            
            inv_empty = MagicMock()
            inv_empty.organization = None
            inv_empty.role = None
            inv_empty.invited_by = None
            assert admin.organization_name(inv_empty) == "N/A"
            assert admin.role_name(inv_empty) == "N/A"
            assert admin.invited_by_email(inv_empty) == "N/A"
