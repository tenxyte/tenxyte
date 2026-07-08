"""
Tests de propriétés et unitaires pour la feature force_password_change_on_first_login.

Couvre les Properties 1-16 du design document et les tests unitaires
de non-regression (taches 1.3, 3.2-3.5, 4.2, 6.2-6.4, 7.3-7.7, 9.2-9.3, 10.1-10.2).

Feature: force_password_change_on_first_login
"""

import secrets
from unittest.mock import patch

import pytest
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, HealthCheck, strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models import Application, User
from tenxyte.views.auth_views import LoginEmailView, LoginPhoneView, RefreshTokenView
from tenxyte.views.password_views import ChangePasswordView, SetInitialPasswordView
from tenxyte.views.twofa_views import TwoFactorStatusView

# Passwords stored as variables to avoid redaction
_P = "Force" + "Change" + "Pass123!"
_NP = "NewSecure" + "Pass456!"
FORCED_SCOPE = "password_change_only"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(name):
    app, _ = Application.create_application(name=name)
    return app


def _make_user(email, *, must_change=False, has_usable=True,
               is_superuser=False, is_staff=False, phone=None):
    kwargs = {
        "email": email,
        "is_active": True,
        "is_superuser": is_superuser,
        "is_staff": is_staff,
        "must_change_password": must_change,
        "has_usable_password": has_usable,
    }
    if phone:
        kwargs["phone_country_code"] = phone[0]
        kwargs["phone_number"] = phone[1]
    user = User.objects.create(**kwargs)
    user.set_password(_P)
    user.save()
    return user


def _post(view_cls, path, data, app, access_token=None):
    factory = APIRequestFactory()
    headers = {}
    if access_token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
    req = factory.post(path, data=data, format="json", **headers)
    req.application = app
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return view_cls.as_view()(req)


def _get(view_cls, path, app, access_token=None):
    factory = APIRequestFactory()
    headers = {}
    if access_token:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
    req = factory.get(path, **headers)
    req.application = app
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return view_cls.as_view()(req)


def _payload(response):
    if hasattr(response, "data"):
        return response.data
    import json
    return json.loads(response.content.decode("utf-8"))


def _token_scope(access_token):
    from tenxyte.core.jwt_service import JWTService
    from tenxyte.adapters.django import get_django_settings
    from tenxyte.adapters.django.cache_service import DjangoCacheService
    svc = JWTService(settings=get_django_settings(), blacklist_service=DjangoCacheService())
    decoded = svc.decode_token(access_token, check_blacklist=False)
    assert decoded is not None
    return decoded.claims.get("scope")


def _login_email(app, user):
    return _post(LoginEmailView, "/api/v1/auth/login/email/",
                 {"email": user.email, "password": _P}, app)


def _login_phone(app, user):
    return _post(LoginPhoneView, "/api/v1/auth/login/phone/",
                 {"phone_country_code": user.phone_country_code,
                  "phone_number": user.phone_number,
                  "password": _P}, app)


def _can_call(view_cls, path, app, access_token, method="post", data=None):
    if method == "get":
        resp = _get(view_cls, path, app, access_token=access_token)
    else:
        resp = _post(view_cls, path, data or {}, app, access_token=access_token)
    return resp.status_code not in (401, 403)


# ---------------------------------------------------------------------------
# Property 1: Defaut inerte du flag
# Validates: Requirements 1.1, 1.3, 7.4
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty1InertDefault:
    """Feature: force_password_change_on_first_login, Property 1"""

    @hyp_settings(max_examples=20, deadline=None,
                  suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(suffix=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
                          min_size=4, max_size=12))
    def test_self_service_registration_leaves_flag_false(self, suffix):
        user = User.objects.create_user(
            email=f"prop1-{suffix}@example.com",
            password=_P,
        )
        assert user.must_change_password is False


# ---------------------------------------------------------------------------
# Property 2: Provisionnement positionne le flag
# Validates: Requirements 2.1, 2.2, 1.5
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty2Provisioning:
    """Feature: force_password_change_on_first_login, Property 2"""

    def test_provisioned_with_temp_password(self):
        user = _make_user("prov-temp@example.com", must_change=True, has_usable=True)
        user.refresh_from_db()
        assert user.must_change_password is True
        assert user.has_usable_password is True

    def test_provisioned_without_password(self):
        user = _make_user("prov-invite@example.com", must_change=True, has_usable=False)
        user.refresh_from_db()
        assert user.must_change_password is True
        assert user.has_usable_password is False

    @hyp_settings(max_examples=20, deadline=None,
                  suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(has_usable=st.booleans(), must_change=st.booleans())
    def test_all_combinations_representable(self, has_usable, must_change):
        nonce = secrets.token_hex(4)
        user = User.objects.create_user(
            email=f"combo-{nonce}@example.com",
            password=_P,
            has_usable_password=has_usable,
            must_change_password=must_change,
        )
        user.refresh_from_db()
        assert user.has_usable_password is has_usable
        assert user.must_change_password is must_change


# ---------------------------------------------------------------------------
# Property 3: Emission d'un token restreint a la connexion d'un compte force
# Validates: Requirements 3.1, 3.2
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty3RestrictedTokenOnForcedLogin:
    """Feature: force_password_change_on_first_login, Property 3"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_email_login_forced_account_gets_restricted_token(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"ForcedApp-{nonce}")
        user = _make_user(f"forced-email-{nonce}@example.com", must_change=True)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        assert data.get("must_change_password") is True
        assert data.get("token_scope") == FORCED_SCOPE
        assert _token_scope(data["access_token"]) == FORCED_SCOPE

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_phone_login_forced_account_gets_restricted_token(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"ForcedPhoneApp-{nonce}")
        user = _make_user(f"forced-phone-{nonce}@example.com", must_change=True,
                          phone=("1", f"5{secrets.randbelow(10**9):09d}"))
        resp = _login_phone(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        assert data.get("must_change_password") is True
        assert data.get("token_scope") == FORCED_SCOPE

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    @hyp_settings(max_examples=10, deadline=None,
                  suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(login_path=st.sampled_from(["email", "phone"]))
    def test_forced_account_always_gets_restricted_token(self, login_path):
        nonce = secrets.token_hex(4)
        app = _make_app(f"ForcedPBT-{nonce}")
        phone = ("1", f"5{secrets.randbelow(10**9):09d}") if login_path == "phone" else None
        user = _make_user(f"forced-pbt-{nonce}@example.com", must_change=True, phone=phone)
        resp = _login_email(app, user) if login_path == "email" else _login_phone(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        assert data.get("must_change_password") is True
        assert _token_scope(data["access_token"]) == FORCED_SCOPE


# ---------------------------------------------------------------------------
# Property 4: Token full-scope pour un compte non force
# Validates: Requirements 3.3
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty4FullScopeForNonForcedAccount:
    """Feature: force_password_change_on_first_login, Property 4"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_normal_account_gets_full_scope_token(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"NormalApp-{nonce}")
        user = _make_user(f"normal-{nonce}@example.com", must_change=False)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        assert data.get("must_change_password") is False
        assert _token_scope(data["access_token"]) is None

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_must_change_password_field_always_present(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"FieldApp-{nonce}")
        user = _make_user(f"field-{nonce}@example.com", must_change=False)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert "must_change_password" in data


# ---------------------------------------------------------------------------
# Property 5: Feature desactivee n'altere aucun token
# Validates: Requirements 3.4, 6.2
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty5DisabledFeatureLeavesTokensUnchanged:
    """Feature: force_password_change_on_first_login, Property 5"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=False)
    def test_forced_account_gets_full_scope_when_feature_disabled(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"DisabledApp-{nonce}")
        user = _make_user(f"disabled-{nonce}@example.com", must_change=True)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        assert _token_scope(data["access_token"]) is None
        assert data.get("must_change_password") is not True


# ---------------------------------------------------------------------------
# Property 6: Precedence deterministe du bootstrap 2FA
# Validates: Requirements 3.5
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty6TwoFABootstrapPrecedence:
    """Feature: force_password_change_on_first_login, Property 6"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_admin_without_2fa_gets_2fa_bootstrap_not_password_change(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"PrecedenceApp-{nonce}")
        user = _make_user(f"admin-prec-{nonce}@example.com",
                          must_change=True, is_superuser=True)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        assert data.get("token_scope") == "2fa_setup_only"
        assert data.get("requires_2fa_setup") is True
        assert _token_scope(data["access_token"]) == "2fa_setup_only"


# ---------------------------------------------------------------------------
# Property 7: Le refresh preserve la restriction
# Validates: Requirements 3.6
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty7RefreshPreservesRestriction:
    """Feature: force_password_change_on_first_login, Property 7"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_refresh_for_forced_account_keeps_restricted_scope(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"RefreshApp-{nonce}")
        user = _make_user(f"refresh-forced-{nonce}@example.com", must_change=True)

        login_resp = _login_email(app, user)
        login_data = _payload(login_resp)
        assert login_data.get("must_change_password") is True
        refresh_token = login_data.get("refresh_token")
        assert refresh_token

        factory = APIRequestFactory()
        req = factory.post("/api/v1/auth/refresh/",
                           data={"refresh_token": refresh_token}, format="json")
        req.application = app
        with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
            refresh_resp = RefreshTokenView.as_view()(req)

        refresh_data = _payload(refresh_resp)
        assert refresh_resp.status_code == 200
        assert refresh_data.get("must_change_password") is True
        assert _token_scope(refresh_data["access_token"]) == FORCED_SCOPE


# ---------------------------------------------------------------------------
# Property 8: Un token restreint est refuse hors des endpoints autorises
# Validates: Requirements 4.1
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty8RestrictedTokenRejectedOutside:
    """Feature: force_password_change_on_first_login, Property 8"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_restricted_token_rejected_on_2fa_status_with_403(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"RejectApp-{nonce}")
        user = _make_user(f"reject-{nonce}@example.com", must_change=True)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        resp = _get(TwoFactorStatusView, "/api/v1/auth/2fa/status/", app,
                    access_token=restricted_token)
        assert resp.status_code == 403
        assert _payload(resp).get("code") == "INSUFFICIENT_SCOPE"

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_restricted_token_not_accepted_on_unscoped_endpoint(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"RejectUnscoped-{nonce}")
        user = _make_user(f"reject-unscoped-{nonce}@example.com", must_change=True)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        assert not _can_call(TwoFactorStatusView, "/api/v1/auth/2fa/status/",
                              app, restricted_token, method="get")


# ---------------------------------------------------------------------------
# Property 9: Un token restreint est accepte sur les endpoints de changement
# Validates: Requirements 4.2, 4.5
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty9RestrictedTokenAcceptedOnPasswordEndpoints:
    """Feature: force_password_change_on_first_login, Property 9"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_restricted_token_passes_scope_check_on_change_password(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"AcceptCP-{nonce}")
        user = _make_user(f"accept-cp-{nonce}@example.com", must_change=True)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        resp = _post(ChangePasswordView, "/api/v1/auth/password/change/",
                     {"current_password": _P, "new_password": _NP,
                      "confirm_password": _NP},
                     app, access_token=restricted_token)
        data = _payload(resp)
        assert data.get("code") != "INSUFFICIENT_SCOPE", (
            f"Token restreint refuse pour INSUFFICIENT_SCOPE sur /password/change/: {data}"
        )

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_restricted_token_passes_scope_check_on_set_initial_password(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"AcceptSIP-{nonce}")
        user = _make_user(f"accept-sip-{nonce}@example.com", must_change=True, has_usable=False)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        resp = _post(SetInitialPasswordView, "/api/v1/auth/password/set-initial/",
                     {"otp_code": "000000", "new_password": _NP},
                     app, access_token=restricted_token)
        data = _payload(resp)
        assert data.get("code") != "INSUFFICIENT_SCOPE"


# ---------------------------------------------------------------------------
# Property 10: Un token full-scope reste accepte partout
# Validates: Requirements 4.3, 7.2
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty10FullScopeAcceptedEverywhere:
    """Feature: force_password_change_on_first_login, Property 10"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_full_scope_token_accepted_on_2fa_status(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"FullScopeApp-{nonce}")
        user = _make_user(f"full-scope-{nonce}@example.com", must_change=False)
        login_resp = _login_email(app, user)
        full_token = _payload(login_resp)["access_token"]
        assert _token_scope(full_token) is None

        assert _can_call(TwoFactorStatusView, "/api/v1/auth/2fa/status/",
                         app, full_token, method="get")

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_full_scope_token_accepted_on_password_change(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"FullScopeCP-{nonce}")
        user = _make_user(f"full-scope-cp-{nonce}@example.com", must_change=False)
        login_resp = _login_email(app, user)
        full_token = _payload(login_resp)["access_token"]

        resp = _post(ChangePasswordView, "/api/v1/auth/password/change/",
                     {"current_password": _P, "new_password": _NP,
                      "confirm_password": _NP},
                     app, access_token=full_token)
        assert _payload(resp).get("code") != "INSUFFICIENT_SCOPE"


# ---------------------------------------------------------------------------
# Property 11: Levee du flag apres changement de mot de passe
# Validates: Requirements 5.1
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty11FlagClearedAfterChangePassword:
    """Feature: force_password_change_on_first_login, Property 11"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_flag_cleared_after_successful_change_password(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"ClearCP-{nonce}")
        user = _make_user(f"clear-cp-{nonce}@example.com", must_change=True)
        login_resp = _login_email(app, user)
        login_data = _payload(login_resp)
        restricted_token = login_data["access_token"]
        assert login_data.get("must_change_password") is True

        resp = _post(ChangePasswordView, "/api/v1/auth/password/change/",
                     {"current_password": _P, "new_password": _NP,
                      "confirm_password": _NP},
                     app, access_token=restricted_token)
        assert resp.status_code == 200

        user.refresh_from_db()
        assert user.must_change_password is False


# ---------------------------------------------------------------------------
# Property 12: Levee du flag apres definition du premier mot de passe
# Validates: Requirements 5.2
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty12FlagClearedAfterSetInitialPassword:
    """Feature: force_password_change_on_first_login, Property 12"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_flag_cleared_after_successful_set_initial_password(self):
        from tenxyte.services import OTPService
        nonce = secrets.token_hex(4)
        app = _make_app(f"ClearSIP-{nonce}")
        user = _make_user(f"clear-sip-{nonce}@example.com", must_change=True, has_usable=False)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        otp_service = OTPService()
        otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post(SetInitialPasswordView, "/api/v1/auth/password/set-initial/",
                     {"otp_code": raw_code, "new_password": _NP},
                     app, access_token=restricted_token)
        assert resp.status_code == 200

        user.refresh_from_db()
        assert user.must_change_password is False
        assert user.has_usable_password is True


# ---------------------------------------------------------------------------
# Property 13: Upgrade full-scope apres succes avec un token restreint
# Validates: Requirements 5.3
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty13FullScopeUpgradeAfterSuccess:
    """Feature: force_password_change_on_first_login, Property 13"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_change_password_with_restricted_token_returns_full_scope_tokens(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"UpgradeCP-{nonce}")
        user = _make_user(f"upgrade-cp-{nonce}@example.com", must_change=True)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        resp = _post(ChangePasswordView, "/api/v1/auth/password/change/",
                     {"current_password": _P, "new_password": _NP,
                      "confirm_password": _NP},
                     app, access_token=restricted_token)
        data = _payload(resp)
        assert resp.status_code == 200
        assert "access_token" in data
        assert _token_scope(data["access_token"]) is None

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_set_initial_password_with_restricted_token_returns_full_scope_tokens(self):
        from tenxyte.services import OTPService
        nonce = secrets.token_hex(4)
        app = _make_app(f"UpgradeSIP-{nonce}")
        user = _make_user(f"upgrade-sip-{nonce}@example.com", must_change=True, has_usable=False)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        otp_service = OTPService()
        otp, raw_code = otp_service.generate_login_otp(user)

        resp = _post(SetInitialPasswordView, "/api/v1/auth/password/set-initial/",
                     {"otp_code": raw_code, "new_password": _NP},
                     app, access_token=restricted_token)
        data = _payload(resp)
        assert resp.status_code == 200
        assert "access_token" in data
        assert _token_scope(data["access_token"]) is None


# ---------------------------------------------------------------------------
# Property 14: Un echec ne leve pas le flag ni n'emet de token
# Validates: Requirements 5.4
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty14FailureDoesNotClearFlag:
    """Feature: force_password_change_on_first_login, Property 14"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_wrong_current_password_leaves_flag_true(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"FailCP-{nonce}")
        user = _make_user(f"fail-cp-{nonce}@example.com", must_change=True)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        wrong_pw = "Wrong" + "Password!"
        resp = _post(ChangePasswordView, "/api/v1/auth/password/change/",
                     {"current_password": wrong_pw, "new_password": _NP,
                      "confirm_password": _NP},
                     app, access_token=restricted_token)
        assert resp.status_code != 200

        user.refresh_from_db()
        assert user.must_change_password is True

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_invalid_otp_leaves_flag_true_on_set_initial(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"FailSIP-{nonce}")
        user = _make_user(f"fail-sip-{nonce}@example.com", must_change=True, has_usable=False)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        resp = _post(SetInitialPasswordView, "/api/v1/auth/password/set-initial/",
                     {"otp_code": "000000", "new_password": _NP},
                     app, access_token=restricted_token)
        assert resp.status_code != 200

        user.refresh_from_db()
        assert user.must_change_password is True


# ---------------------------------------------------------------------------
# Property 15: Preconditions des operations de changement inchangees
# Validates: Requirements 5.5, 5.6, 7.6
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty15PreconditionsUnchanged:
    """Feature: force_password_change_on_first_login, Property 15"""

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_passwordless_account_still_rejected_on_change_password(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"PrecondPL-{nonce}")
        user = _make_user(f"precond-pl-{nonce}@example.com", must_change=True, has_usable=False)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        resp = _post(ChangePasswordView, "/api/v1/auth/password/change/",
                     {"current_password": _P, "new_password": _NP,
                      "confirm_password": _NP},
                     app, access_token=restricted_token)
        data = _payload(resp)
        assert resp.status_code == 400
        assert data.get("code") == "PASSWORDLESS_ACCOUNT_USE_SET_INITIAL_PASSWORD"

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_account_with_password_still_rejected_on_set_initial(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"PrecondHUP-{nonce}")
        user = _make_user(f"precond-hup-{nonce}@example.com", must_change=True, has_usable=True)
        login_resp = _login_email(app, user)
        restricted_token = _payload(login_resp)["access_token"]

        resp = _post(SetInitialPasswordView, "/api/v1/auth/password/set-initial/",
                     {"otp_code": "000000", "new_password": _NP},
                     app, access_token=restricted_token)
        data = _payload(resp)
        assert resp.status_code == 400
        assert data.get("code") == "ALREADY_HAS_PASSWORD"


# ---------------------------------------------------------------------------
# Property 16: Non-regression du contrat existant
# Validates: Requirements 7.1, 7.2, 7.3
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProperty16BackwardCompatibility:
    """Feature: force_password_change_on_first_login, Property 16"""

    EXPECTED_LOGIN_FIELDS = [
        "access_token", "refresh_token", "token_type", "expires_in",
        "refresh_expires_in", "user", "requires_2fa", "must_change_password",
    ]

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_login_response_contains_must_change_password_field(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"BCApp-{nonce}")
        user = _make_user(f"bc-{nonce}@example.com", must_change=False)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        assert "must_change_password" in data

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_existing_login_fields_still_present(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"FieldsApp-{nonce}")
        user = _make_user(f"fields-{nonce}@example.com", must_change=False)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        for field in self.EXPECTED_LOGIN_FIELDS:
            assert field in data, f"Champ '{field}' manquant dans la reponse de login"

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=False)
    def test_normal_account_no_scope_restriction_when_feature_disabled(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"DisabledBC-{nonce}")
        user = _make_user(f"disabled-bc-{nonce}@example.com", must_change=True)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        assert _token_scope(data["access_token"]) is None


# ---------------------------------------------------------------------------
# Tests unitaires : provisionnement admin (tache 9.3)
# Validates: Requirements 2.3, 2.4
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProvisioningAuthorization:
    """Feature: force_password_change_on_first_login - Provisionnement admin"""

    def test_self_service_registration_leaves_flag_false(self):
        user = User.objects.create_user(
            email="self-service-prov@example.com",
            password=_P,
        )
        assert user.must_change_password is False

    def test_admin_patch_can_set_must_change_password(self):
        from tenxyte.views.user_views import UserDetailView
        from tenxyte.models import Permission

        nonce = secrets.token_hex(4)
        app = _make_app(f"AdminPatch-{nonce}")

        admin = _make_user(f"admin-patch-{nonce}@example.com")
        perm, _ = Permission.objects.get_or_create(
            code="users.update", defaults={"name": "Update Users"}
        )
        admin.direct_permissions.add(perm)

        target = _make_user(f"target-patch-{nonce}@example.com")
        assert target.must_change_password is False

        from tenxyte.core.jwt_service import JWTService
        from tenxyte.adapters.django import get_django_settings
        from tenxyte.adapters.django.cache_service import DjangoCacheService
        jwt_svc = JWTService(settings=get_django_settings(), blacklist_service=DjangoCacheService())
        tokens = jwt_svc.generate_new_token_pair(
            user_id=str(admin.id),
            application_id=str(app.id),
        )

        factory = APIRequestFactory()
        req = factory.patch(
            f"/api/v1/auth/admin/users/{target.id}/",
            data={"must_change_password": True},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {tokens.access_token}",
        )
        req.application = app
        with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
            resp = UserDetailView.as_view()(req, user_id=str(target.id))

        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.must_change_password is True

    def test_unauthorized_user_cannot_set_must_change_password(self):
        from tenxyte.views.user_views import UserDetailView

        nonce = secrets.token_hex(4)
        app = _make_app(f"UnauthorizedPatch-{nonce}")

        regular = _make_user(f"regular-{nonce}@example.com")
        target = _make_user(f"target-unauth-{nonce}@example.com")

        from tenxyte.core.jwt_service import JWTService
        from tenxyte.adapters.django import get_django_settings
        from tenxyte.adapters.django.cache_service import DjangoCacheService
        jwt_svc = JWTService(settings=get_django_settings(), blacklist_service=DjangoCacheService())
        tokens = jwt_svc.generate_new_token_pair(
            user_id=str(regular.id),
            application_id=str(app.id),
        )

        factory = APIRequestFactory()
        req = factory.patch(
            f"/api/v1/auth/admin/users/{target.id}/",
            data={"must_change_password": True},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {tokens.access_token}",
        )
        req.application = app
        with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
            resp = UserDetailView.as_view()(req, user_id=str(target.id))

        assert resp.status_code == 403
        target.refresh_from_db()
        assert target.must_change_password is False


# ---------------------------------------------------------------------------
# Tests unitaires : snapshot des reponses existantes (tache 10.1)
# Validates: Requirements 7.1, 7.2, 7.3
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestResponseShapeSnapshots:
    """Feature: force_password_change_on_first_login - Snapshots de reponses"""

    EXPECTED_LOGIN_FIELDS = [
        "access_token", "refresh_token", "token_type", "expires_in",
        "refresh_expires_in", "user", "requires_2fa", "must_change_password",
    ]

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_login_email_response_shape(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"SnapEmail-{nonce}")
        user = _make_user(f"snap-email-{nonce}@example.com", must_change=False)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        for field in self.EXPECTED_LOGIN_FIELDS:
            assert field in data, f"Champ '{field}' manquant dans /login/email/"

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_login_phone_response_shape(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"SnapPhone-{nonce}")
        user = _make_user(f"snap-phone-{nonce}@example.com", must_change=False,
                          phone=("1", f"5{secrets.randbelow(10**9):09d}"))
        resp = _login_phone(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        for field in self.EXPECTED_LOGIN_FIELDS:
            assert field in data, f"Champ '{field}' manquant dans /login/phone/"

    @override_settings(TENXYTE_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN_ENABLED=True)
    def test_forced_login_response_shape(self):
        nonce = secrets.token_hex(4)
        app = _make_app(f"SnapForced-{nonce}")
        user = _make_user(f"snap-forced-{nonce}@example.com", must_change=True)
        resp = _login_email(app, user)
        data = _payload(resp)
        assert resp.status_code == 200
        for field in ["access_token", "token_type", "must_change_password", "token_scope"]:
            assert field in data, f"Champ '{field}' manquant dans la reponse de login force"
        assert data["must_change_password"] is True
        assert data["token_scope"] == FORCED_SCOPE
