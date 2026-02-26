"""
Tests filters.py - Organization, member, audit log, and login attempt filters.

Coverage cible : filters.py (46% → ~75%)
"""

import pytest
from unittest.mock import MagicMock
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application, AuditLog
from tenxyte.models.organization import Organization, OrganizationMembership
from tenxyte.services.organization_service import OrganizationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_request(**params):
    """Build a DRF Request with query_params."""
    from rest_framework.request import Request as DRFRequest
    factory = APIRequestFactory()
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    wsgi_req = factory.get(f"/?{qs}")
    return DRFRequest(wsgi_req)


def _app(name="FilterApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    u.save()
    return u


def _setup_org(owner):
    service = OrganizationService()
    service.initialize_system_roles()
    _, org, _ = service.create_organization(name="Filter Org", created_by=owner)
    return org, service


# ===========================================================================
# apply_ordering
# ===========================================================================

class TestApplyOrdering:

    @pytest.mark.django_db
    def test_default_ordering_applied_when_no_param(self):
        from tenxyte.filters import apply_ordering
        qs = AuditLog.objects.all()
        req = _mock_request()
        result = apply_ordering(qs, req, default='-created_at')
        assert str(result.query).count('ORDER BY') == 1

    @pytest.mark.django_db
    def test_custom_ordering_applied(self):
        from tenxyte.filters import apply_ordering
        qs = AuditLog.objects.all()
        req = _mock_request(ordering='created_at')
        result = apply_ordering(qs, req, default='-created_at', allowed_fields=['created_at'])
        assert 'created_at' in str(result.query)

    @pytest.mark.django_db
    def test_disallowed_field_ignored(self):
        from tenxyte.filters import apply_ordering
        qs = AuditLog.objects.all()
        req = _mock_request(ordering='hacked_field')
        result = apply_ordering(qs, req, default='-created_at', allowed_fields=['created_at'])
        # Falls back to default
        assert result is not None

    @pytest.mark.django_db
    def test_no_default_no_param_returns_unordered(self):
        from tenxyte.filters import apply_ordering
        qs = AuditLog.objects.all()
        req = _mock_request()
        result = apply_ordering(qs, req, default=None)
        assert result is not None

    @pytest.mark.django_db
    def test_multi_field_ordering(self):
        from tenxyte.filters import apply_ordering
        qs = AuditLog.objects.all()
        req = _mock_request(ordering='action,-created_at')
        result = apply_ordering(qs, req, default='-created_at', allowed_fields=['action', 'created_at'])
        assert result is not None


# ===========================================================================
# apply_search
# ===========================================================================

class TestApplySearch:

    @pytest.mark.django_db
    def test_search_filters_by_email(self):
        from tenxyte.filters import apply_search
        _user("search_match@test.com")
        _user("nomatch@other.com")
        qs = User.objects.all()
        req = _mock_request(search="search_match")
        result = apply_search(qs, req, ['email'])
        assert result.filter(email="search_match@test.com").exists()

    @pytest.mark.django_db
    def test_empty_search_returns_all(self):
        from tenxyte.filters import apply_search
        _user("all1@test.com")
        _user("all2@test.com")
        qs = User.objects.filter(email__in=["all1@test.com", "all2@test.com"])
        req = _mock_request()
        result = apply_search(qs, req, ['email'])
        assert result.count() == 2


# ===========================================================================
# apply_date_range
# ===========================================================================

class TestApplyDateRange:

    @pytest.mark.django_db
    def test_date_from_filters(self):
        from tenxyte.filters import apply_date_range
        user = _user("daterange@test.com")
        AuditLog.objects.create(user=user, action="test", ip_address="1.2.3.4", details={})
        qs = AuditLog.objects.all()
        req = _mock_request(date_from="2000-01-01")
        result = apply_date_range(qs, req)
        assert result.count() >= 1

    @pytest.mark.django_db
    def test_date_to_filters(self):
        from tenxyte.filters import apply_date_range
        user = _user("dateto@test.com")
        AuditLog.objects.create(user=user, action="test", ip_address="1.2.3.4", details={})
        qs = AuditLog.objects.all()
        req = _mock_request(date_to="2099-12-31")
        result = apply_date_range(qs, req)
        assert result.count() >= 1

    @pytest.mark.django_db
    def test_no_date_params_returns_all(self):
        from tenxyte.filters import apply_date_range
        user = _user("dateall@test.com")
        AuditLog.objects.create(user=user, action="test", ip_address="1.2.3.4", details={})
        qs = AuditLog.objects.all()
        req = _mock_request()
        result = apply_date_range(qs, req)
        assert result.count() >= 1


# ===========================================================================
# apply_boolean_filter
# ===========================================================================

class TestApplyBooleanFilter:

    @pytest.mark.django_db
    def test_true_filters_active_users(self):
        from tenxyte.filters import apply_boolean_filter
        _user("bool_active@test.com")
        u2 = _user("bool_inactive@test.com")
        u2.is_active = False
        u2.save()
        qs = User.objects.filter(email__in=["bool_active@test.com", "bool_inactive@test.com"])
        req = _mock_request(is_active="true")
        result = apply_boolean_filter(qs, req, 'is_active')
        assert result.count() == 1
        assert result.first().email == "bool_active@test.com"

    @pytest.mark.django_db
    def test_false_filters_inactive_users(self):
        from tenxyte.filters import apply_boolean_filter
        _user("bool_active2@test.com")
        u2 = _user("bool_inactive2@test.com")
        u2.is_active = False
        u2.save()
        qs = User.objects.filter(email__in=["bool_active2@test.com", "bool_inactive2@test.com"])
        req = _mock_request(is_active="false")
        result = apply_boolean_filter(qs, req, 'is_active')
        assert result.count() == 1
        assert result.first().email == "bool_inactive2@test.com"

    @pytest.mark.django_db
    def test_no_param_returns_all(self):
        from tenxyte.filters import apply_boolean_filter
        _user("bool_all1@test.com")
        _user("bool_all2@test.com")
        qs = User.objects.filter(email__in=["bool_all1@test.com", "bool_all2@test.com"])
        req = _mock_request()
        result = apply_boolean_filter(qs, req, 'is_active')
        assert result.count() == 2

    @pytest.mark.django_db
    def test_1_and_0_values_work(self):
        from tenxyte.filters import apply_boolean_filter
        _user("bool_one@test.com")
        u2 = _user("bool_zero@test.com")
        u2.is_active = False
        u2.save()
        qs = User.objects.filter(email__in=["bool_one@test.com", "bool_zero@test.com"])
        req = _mock_request(is_active="1")
        result = apply_boolean_filter(qs, req, 'is_active')
        assert result.count() == 1

    @pytest.mark.django_db
    def test_invalid_boolean_returns_all(self):
        from tenxyte.filters import apply_boolean_filter
        _user("bool_one2@test.com")
        qs = User.objects.all()
        req = _mock_request(is_active="not_a_bool")
        result = apply_boolean_filter(qs, req, 'is_active')
        assert result.count() > 0


# ===========================================================================
# apply_organization_filters
# ===========================================================================

class TestApplyOrganizationFilters:

    @pytest.mark.django_db
    def test_search_by_name(self):
        from tenxyte.filters import apply_organization_filters
        owner = _user("org_filter_owner@test.com")
        org, _ = _setup_org(owner)
        qs = Organization.objects.all()
        req = _mock_request(search="Filter")
        result = apply_organization_filters(qs, req)
        assert result.filter(id=org.id).exists()

    @pytest.mark.django_db
    def test_filter_active_only(self):
        from tenxyte.filters import apply_organization_filters
        owner = _user("org_active_owner@test.com")
        org, _ = _setup_org(owner)
        qs = Organization.objects.all()
        req = _mock_request(is_active="true")
        result = apply_organization_filters(qs, req)
        assert result.filter(id=org.id).exists()

    @pytest.mark.django_db
    def test_filter_root_orgs(self):
        from tenxyte.filters import apply_organization_filters
        owner = _user("org_root_owner@test.com")
        org, _ = _setup_org(owner)
        qs = Organization.objects.all()
        req = _mock_request(parent="null")
        result = apply_organization_filters(qs, req)
        assert result.filter(id=org.id).exists()

    @pytest.mark.django_db
    def test_filter_by_parent_id(self):
        from tenxyte.filters import apply_organization_filters
        owner = _user("org_parent_owner@test.com")
        parent_org, service = _setup_org(owner)
        _, child_org, _ = service.create_organization(
            name="Child Org", created_by=owner, parent_id=parent_org.id
        )
        qs = Organization.objects.all()
        req = _mock_request(parent=str(parent_org.id))
        result = apply_organization_filters(qs, req)
        assert result.filter(id=child_org.id).exists()
        assert not result.filter(id=parent_org.id).exists()

    @pytest.mark.django_db
    def test_ordering_by_name(self):
        from tenxyte.filters import apply_organization_filters
        owner = _user("org_order_owner@test.com")
        _setup_org(owner)
        qs = Organization.objects.all()
        req = _mock_request(ordering="name")
        result = apply_organization_filters(qs, req)
        assert result is not None


# ===========================================================================
# apply_member_filters
# ===========================================================================

class TestApplyMemberFilters:

    @pytest.mark.django_db
    def test_search_by_email(self):
        from tenxyte.filters import apply_member_filters
        owner = _user("member_filter_owner@test.com")
        member = _user("member_filter_target@test.com")
        org, service = _setup_org(owner)
        service.add_member(org, member, "member", owner)

        qs = OrganizationMembership.objects.filter(organization=org)
        req = _mock_request(search="member_filter_target")
        result = apply_member_filters(qs, req)
        assert result.filter(user=member).exists()

    @pytest.mark.django_db
    def test_filter_by_role(self):
        from tenxyte.filters import apply_member_filters
        owner = _user("member_role_owner@test.com")
        member = _user("member_role_target@test.com")
        org, service = _setup_org(owner)
        service.add_member(org, member, "member", owner)

        qs = OrganizationMembership.objects.filter(organization=org)
        req = _mock_request(role="member")
        result = apply_member_filters(qs, req)
        assert result.filter(user=member).exists()
        assert not result.filter(user=owner).exists()

    @pytest.mark.django_db
    def test_filter_by_status(self):
        from tenxyte.filters import apply_member_filters
        owner = _user("member_status_owner@test.com")
        member = _user("member_status_target@test.com")
        org, service = _setup_org(owner)
        service.add_member(org, member, "member", owner)

        qs = OrganizationMembership.objects.filter(organization=org)
        req = _mock_request(status="active")
        result = apply_member_filters(qs, req)
        assert result.count() == 2  # owner + member

    @pytest.mark.django_db
    def test_ordering_by_email(self):
        from tenxyte.filters import apply_member_filters
        owner = _user("member_order_owner@test.com")
        org, _ = _setup_org(owner)

        qs = OrganizationMembership.objects.filter(organization=org)
        req = _mock_request(ordering="user__email")
        result = apply_member_filters(qs, req)
        assert result is not None

    @pytest.mark.django_db
    def test_no_filters_returns_all(self):
        from tenxyte.filters import apply_member_filters
        owner = _user("member_all_owner@test.com")
        member = _user("member_all_target@test.com")
        org, service = _setup_org(owner)
        service.add_member(org, member, "member", owner)

        qs = OrganizationMembership.objects.filter(organization=org)
        req = _mock_request()
        result = apply_member_filters(qs, req)
        assert result.count() == 2


# ===========================================================================
# apply_audit_log_filters
# ===========================================================================

class TestApplyAuditLogFilters:

    @pytest.mark.django_db
    def test_filter_by_user_id(self):
        from tenxyte.filters import apply_audit_log_filters
        user = _user("audit_filter_user@test.com")
        AuditLog.objects.create(user=user, action="login", ip_address="1.2.3.4", details={})
        qs = AuditLog.objects.all()
        req = _mock_request(user_id=str(user.id))
        result = apply_audit_log_filters(qs, req)
        assert result.filter(user=user).exists()

    @pytest.mark.django_db
    def test_filter_by_action(self):
        from tenxyte.filters import apply_audit_log_filters
        user = _user("audit_action_user@test.com")
        AuditLog.objects.create(user=user, action="login", ip_address="1.2.3.4", details={})
        AuditLog.objects.create(user=user, action="logout", ip_address="1.2.3.4", details={})
        qs = AuditLog.objects.filter(user=user)
        req = _mock_request(action="login")
        result = apply_audit_log_filters(qs, req)
        assert result.count() == 1
        assert result.first().action == "login"

    @pytest.mark.django_db
    def test_filter_by_multiple_actions(self):
        from tenxyte.filters import apply_audit_log_filters
        user = _user("audit_multi_action@test.com")
        AuditLog.objects.create(user=user, action="login", ip_address="1.2.3.4", details={})
        AuditLog.objects.create(user=user, action="logout", ip_address="1.2.3.4", details={})
        AuditLog.objects.create(user=user, action="password_change", ip_address="1.2.3.4", details={})
        qs = AuditLog.objects.filter(user=user)
        req = _mock_request(action="login,logout")
        result = apply_audit_log_filters(qs, req)
        assert result.count() == 2

    @pytest.mark.django_db
    def test_filter_by_ip(self):
        from tenxyte.filters import apply_audit_log_filters
        user = _user("audit_ip_user@test.com")
        AuditLog.objects.create(user=user, action="login", ip_address="9.9.9.9", details={})
        qs = AuditLog.objects.filter(user=user)
        req = _mock_request(ip_address="9.9.9.9")
        result = apply_audit_log_filters(qs, req)
        assert result.count() == 1

    @pytest.mark.django_db
    def test_no_filters_returns_all(self):
        from tenxyte.filters import apply_audit_log_filters
        user = _user("audit_all_user@test.com")
        AuditLog.objects.create(user=user, action="login", ip_address="1.2.3.4", details={})
        AuditLog.objects.create(user=user, action="logout", ip_address="1.2.3.4", details={})
        qs = AuditLog.objects.filter(user=user)
        req = _mock_request()
        result = apply_audit_log_filters(qs, req)
        assert result.count() == 2

    @pytest.mark.django_db
    def test_filter_by_application_id(self):
        from tenxyte.filters import apply_audit_log_filters
        app = _app("AuditFilterApp")
        user = _user("audit_app_user@test.com")
        AuditLog.objects.create(user=user, action="login", ip_address="1.2.3.4", application=app, details={})
        qs = AuditLog.objects.all()
        req = _mock_request(application_id=str(app.id))
        result = apply_audit_log_filters(qs, req)
        assert result.filter(application=app).exists()


# ===========================================================================
# apply_login_attempt_filters
# ===========================================================================

class TestApplyLoginAttemptFilters:

    @pytest.mark.django_db
    def test_filter_by_identifier(self):
        from tenxyte.filters import apply_login_attempt_filters
        from tenxyte.models import LoginAttempt
        app = _app("LoginAttemptFilterApp")
        LoginAttempt.objects.create(
            identifier="filter_user@test.com",
            ip_address="1.2.3.4",
            application=app,
            success=False
        )
        qs = LoginAttempt.objects.all()
        req = _mock_request(identifier="filter_user")
        result = apply_login_attempt_filters(qs, req)
        assert result.filter(identifier="filter_user@test.com").exists()

    @pytest.mark.django_db
    def test_filter_by_ip(self):
        from tenxyte.filters import apply_login_attempt_filters
        from tenxyte.models import LoginAttempt
        app = _app("LoginIPFilterApp")
        LoginAttempt.objects.create(
            identifier="ip_user@test.com",
            ip_address="5.5.5.5",
            application=app,
            success=False
        )
        qs = LoginAttempt.objects.all()
        req = _mock_request(ip_address="5.5.5.5")
        result = apply_login_attempt_filters(qs, req)
        assert result.filter(ip_address="5.5.5.5").exists()

    @pytest.mark.django_db
    def test_filter_by_success_true(self):
        from tenxyte.filters import apply_login_attempt_filters
        from tenxyte.models import LoginAttempt
        app = _app("LoginSuccessFilterApp")
        LoginAttempt.objects.create(
            identifier="success_user@test.com",
            ip_address="1.2.3.4",
            application=app,
            success=True
        )
        LoginAttempt.objects.create(
            identifier="fail_user@test.com",
            ip_address="1.2.3.4",
            application=app,
            success=False
        )
        qs = LoginAttempt.objects.filter(
            identifier__in=["success_user@test.com", "fail_user@test.com"]
        )
        req = _mock_request(success="true")
        result = apply_login_attempt_filters(qs, req)
        assert result.count() == 1
        assert result.first().identifier == "success_user@test.com"

    @pytest.mark.django_db
    def test_no_filters_returns_all(self):
        from tenxyte.filters import apply_login_attempt_filters
        from tenxyte.models import LoginAttempt
        app = _app("LoginAllFilterApp")
        LoginAttempt.objects.create(
            identifier="all1@test.com", ip_address="1.2.3.4",
            application=app, success=True
        )
        LoginAttempt.objects.create(
            identifier="all2@test.com", ip_address="1.2.3.4",
            application=app, success=False
        )
        qs = LoginAttempt.objects.filter(identifier__in=["all1@test.com", "all2@test.com"])
        req = _mock_request()
        result = apply_login_attempt_filters(qs, req)
        assert result.count() == 2

# ===========================================================================
# apply_permission_filters
# ===========================================================================

class TestApplyPermissionFilters:
    @pytest.mark.django_db
    def test_apply_permission_filters(self):
        from tenxyte.filters import apply_permission_filters
        from tenxyte.models import Permission
        p1 = Permission.objects.create(code='p_test_1', name='Perm 1')
        p2 = Permission.objects.create(code='p_test_2', name='Perm 2', parent=p1)
        qs = Permission.objects.all()
        
        req = _mock_request(search='Perm 1')
        res = apply_permission_filters(qs, req)
        assert res.filter(code='p_test_1').exists()

        req = _mock_request(parent='null')
        res = apply_permission_filters(qs, req)
        assert res.filter(code='p_test_1').exists()

        req = _mock_request(parent=str(p1.id))
        res = apply_permission_filters(qs, req)
        assert res.filter(code='p_test_2').exists()

# ===========================================================================
# apply_role_filters
# ===========================================================================

class TestApplyRoleFilters:
    @pytest.mark.django_db
    def test_apply_role_filters(self):
        from tenxyte.filters import apply_role_filters
        from tenxyte.models import Role
        r1, _ = Role.objects.get_or_create(code='r_test_1', name='Role 1', defaults={'is_default': True})
        r2, _ = Role.objects.get_or_create(code='r_test_2', name='Role 2', defaults={'is_default': False})
        qs = Role.objects.all()

        req = _mock_request(search='Role 1')
        assert apply_role_filters(qs, req).filter(code='r_test_1').exists()

        req = _mock_request(is_default='true')
        assert apply_role_filters(qs, req).filter(code='r_test_1').exists()

# ===========================================================================
# apply_application_filters
# ===========================================================================

class TestApplyApplicationFilters:
    @pytest.mark.django_db
    def test_apply_application_filters(self):
        from tenxyte.filters import apply_application_filters
        from tenxyte.models import Application
        app1 = _app("App 1 Filters")
        qs = Application.objects.all()
        
        req = _mock_request(search='App 1 Filters')
        assert apply_application_filters(qs, req).filter(id=app1.id).exists()
        
        req = _mock_request(is_active='true')
        assert apply_application_filters(qs, req).filter(id=app1.id).exists()

# ===========================================================================
# apply_user_filters
# ===========================================================================

class TestApplyUserFilters:
    @pytest.mark.django_db
    def test_apply_user_filters(self):
        from tenxyte.filters import apply_user_filters
        from tenxyte.models import User, Role
        u = _user("user_filters@test.com")
        u.is_active = True
        u.is_locked = False
        u.is_banned = False
        u.is_deleted = False
        u.is_email_verified = True
        u.is_2fa_enabled = False
        u.save()
        
        role, _ = Role.objects.get_or_create(code='testrole', name='Test')
        u.roles.add(role)

        qs = User.objects.all()
        
        req = _mock_request(search='user_filters')
        assert apply_user_filters(qs, req).filter(id=u.id).exists()

        req = _mock_request(is_active='true', is_locked='false', is_banned='false')
        assert apply_user_filters(qs, req).filter(id=u.id).exists()
        
        req = _mock_request(is_deleted='false', is_email_verified='true', is_2fa_enabled='false')
        assert apply_user_filters(qs, req).filter(id=u.id).exists()

        req = _mock_request(role='testrole')
        assert apply_user_filters(qs, req).filter(id=u.id).exists()

# ===========================================================================
# apply_permission_filters
# ===========================================================================

class TestApplyPermissionFilters:
    @pytest.mark.django_db
    def test_apply_permission_filters(self):
        from tenxyte.filters import apply_permission_filters
        from tenxyte.models import Permission
        p1 = Permission.objects.create(code='p_test_1', name='Perm 1')
        p2 = Permission.objects.create(code='p_test_2', name='Perm 2', parent=p1)
        qs = Permission.objects.all()
        
        req = _mock_request(search='Perm 1')
        res = apply_permission_filters(qs, req)
        assert res.filter(code='p_test_1').exists()

        req = _mock_request(parent='null')
        res = apply_permission_filters(qs, req)
        assert res.filter(code='p_test_1').exists()

        req = _mock_request(parent=str(p1.id))
        res = apply_permission_filters(qs, req)
        assert res.filter(code='p_test_2').exists()

# ===========================================================================
# apply_role_filters
# ===========================================================================

class TestApplyRoleFilters:
    @pytest.mark.django_db
    def test_apply_role_filters(self):
        from tenxyte.filters import apply_role_filters
        from tenxyte.models import Role
        r1, _ = Role.objects.get_or_create(code='r_test_1', name='Role 1', defaults={'is_default': True})
        r2, _ = Role.objects.get_or_create(code='r_test_2', name='Role 2', defaults={'is_default': False})
        qs = Role.objects.all()

        req = _mock_request(search='Role 1')
        assert apply_role_filters(qs, req).filter(code='r_test_1').exists()

        req = _mock_request(is_default='true')
        assert apply_role_filters(qs, req).filter(code='r_test_1').exists()

# ===========================================================================
# apply_application_filters
# ===========================================================================

class TestApplyApplicationFilters:
    @pytest.mark.django_db
    def test_apply_application_filters(self):
        from tenxyte.filters import apply_application_filters
        from tenxyte.models import Application
        app1 = _app("App 1 Filters")
        qs = Application.objects.all()
        
        req = _mock_request(search='App 1 Filters')
        assert apply_application_filters(qs, req).filter(id=app1.id).exists()
        
        req = _mock_request(is_active='true')
        assert apply_application_filters(qs, req).filter(id=app1.id).exists()

# ===========================================================================
# apply_user_filters
# ===========================================================================

class TestApplyUserFilters:
    @pytest.mark.django_db
    def test_apply_user_filters(self):
        from tenxyte.filters import apply_user_filters
        from tenxyte.models import User, Role
        u = _user("user_filters@test.com")
        u.is_active = True
        u.is_locked = False
        u.is_banned = False
        u.is_deleted = False
        u.is_email_verified = True
        u.is_2fa_enabled = False
        u.save()
        
        role, _ = Role.objects.get_or_create(code='testrole', name='Test')
        u.roles.add(role)

        qs = User.objects.all()
        
        req = _mock_request(search='user_filters')
        assert apply_user_filters(qs, req).filter(id=u.id).exists()

        req = _mock_request(is_active='true', is_locked='false', is_banned='false')
        assert apply_user_filters(qs, req).filter(id=u.id).exists()
        
        req = _mock_request(is_deleted='false', is_email_verified='true', is_2fa_enabled='false')
        assert apply_user_filters(qs, req).filter(id=u.id).exists()

        req = _mock_request(role='testrole')
        assert apply_user_filters(qs, req).filter(id=u.id).exists()

