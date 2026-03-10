"""
Tests otp_views.py — RequestOTPView, VerifyEmailOTPView, VerifyPhoneOTPView.

Coverage cible : views/otp_views.py (43% → 80%)
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory

from tenxyte.models import User, Application, Permission
from tenxyte.views.otp_views import RequestOTPView, VerifyEmailOTPView, VerifyPhoneOTPView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(name="OTPApp"):
    app, _ = Application.create_application(name=name)
    return app


def _user(email, phone_cc=None, phone_num=None):
    u = User.objects.create(email=email, is_active=True)
    u.set_password("Pass123!")
    if phone_cc:
        u.phone_country_code = phone_cc
        u.phone_number = phone_num
    u.save()
    return u


def _jwt_token(user, app):
    from tenxyte.services.jwt_service import JWTService
    return JWTService().generate_token_pair(
        user_id=str(user.id),
        application_id=str(app.id),
        refresh_token_str="testrefresh",
    )["access_token"]


def _authed_post(view_cls, path, user, app, data):
    token = _jwt_token(user, app)
    factory = APIRequestFactory()
    req = factory.post(path, data=data, format="json",
                       HTTP_AUTHORIZATION=f"Bearer {token}")
    req.application = app
    req.user = user
    with patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True):
        return view_cls.as_view()(req)


# ===========================================================================
# RequestOTPView
# ===========================================================================

class TestRequestOTPView:

    @pytest.mark.django_db
    def test_request_email_otp_success(self):
        app = _app("ReqOTP1")
        user = _user("reqotp1@test.com")

        with patch("tenxyte.views.otp_views.OTPService") as MockOTP:
            mock_inst = MagicMock()
            MockOTP.return_value = mock_inst
            mock_inst.generate_email_verification_otp.return_value = (MagicMock(), "123456")
            resp = _authed_post(RequestOTPView, "/auth/otp/request/", user, app,
                                {"otp_type": "email"})

        assert resp.status_code == 200
        assert "OTP sent" in resp.data["message"]
        mock_inst.generate_email_verification_otp.assert_called_once_with(user)
        mock_inst.send_email_otp.assert_called_once()

    @pytest.mark.django_db
    def test_request_phone_otp_success(self):
        app = _app("ReqOTP2")
        user = _user("reqotp2@test.com", phone_cc="33", phone_num="600000010")

        with patch("tenxyte.views.otp_views.OTPService") as MockOTP:
            mock_inst = MagicMock()
            MockOTP.return_value = mock_inst
            mock_inst.generate_phone_verification_otp.return_value = (MagicMock(), "654321")
            resp = _authed_post(RequestOTPView, "/auth/otp/request/", user, app,
                                {"otp_type": "phone"})

        assert resp.status_code == 200
        mock_inst.generate_phone_verification_otp.assert_called_once_with(user)
        mock_inst.send_phone_otp.assert_called_once()

    @pytest.mark.django_db
    def test_request_email_otp_no_email_returns_400(self):
        app = _app("ReqOTP3")
        user = User.objects.create(
            phone_country_code="33", phone_number="600000011", is_active=True
        )
        user.set_password("Pass123!")
        user.save()

        resp = _authed_post(RequestOTPView, "/auth/otp/request/", user, app,
                            {"otp_type": "email"})
        assert resp.status_code == 400
        assert resp.data["code"] == "NO_EMAIL"

    @pytest.mark.django_db
    def test_request_phone_otp_no_phone_returns_400(self):
        app = _app("ReqOTP4")
        user = _user("reqotp4@test.com")

        resp = _authed_post(RequestOTPView, "/auth/otp/request/", user, app,
                            {"otp_type": "phone"})
        assert resp.status_code == 400
        assert resp.data["code"] == "NO_PHONE"

    @pytest.mark.django_db
    def test_request_otp_invalid_data_returns_400(self):
        app = _app("ReqOTP5")
        user = _user("reqotp5@test.com")

        resp = _authed_post(RequestOTPView, "/auth/otp/request/", user, app, {})
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_request_otp_requires_jwt(self):
        app = _app("ReqOTP6")
        factory = APIRequestFactory()
        req = factory.post("/auth/otp/request/", data={"otp_type": "email"}, format="json")
        req.application = app
        resp = RequestOTPView.as_view()(req)
        assert resp.status_code == 401


# ===========================================================================
# VerifyEmailOTPView
# ===========================================================================

class TestVerifyEmailOTPView:

    @pytest.mark.django_db
    def test_verify_email_otp_success(self):
        app = _app("VerifyEmailOTP1")
        user = _user("verifyemail1@test.com")

        with patch("tenxyte.views.otp_views.OTPService") as MockOTP:
            mock_inst = MagicMock()
            MockOTP.return_value = mock_inst
            mock_inst.verify_email_otp.return_value = (True, "")
            resp = _authed_post(VerifyEmailOTPView, "/auth/otp/verify/email/", user, app,
                                {"code": "123456"})

        assert resp.status_code == 200
        assert "verified" in resp.data["message"].lower()

    @pytest.mark.django_db
    def test_verify_email_otp_invalid_code_returns_400(self):
        app = _app("VerifyEmailOTP2")
        user = _user("verifyemail2@test.com")

        with patch("tenxyte.views.otp_views.OTPService") as MockOTP:
            mock_inst = MagicMock()
            MockOTP.return_value = mock_inst
            mock_inst.verify_email_otp.return_value = (False, "Invalid or expired OTP")
            resp = _authed_post(VerifyEmailOTPView, "/auth/otp/verify/email/", user, app,
                                {"code": "000000"})

        assert resp.status_code == 400
        assert resp.data["code"] == "OTP_VERIFICATION_FAILED"

    @pytest.mark.django_db
    def test_verify_email_otp_invalid_data_returns_400(self):
        app = _app("VerifyEmailOTP3")
        user = _user("verifyemail3@test.com")

        resp = _authed_post(VerifyEmailOTPView, "/auth/otp/verify/email/", user, app, {})
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_verify_email_otp_requires_jwt(self):
        app = _app("VerifyEmailOTP4")
        factory = APIRequestFactory()
        req = factory.post("/auth/otp/verify/email/", data={"code": "123456"}, format="json")
        req.application = app
        resp = VerifyEmailOTPView.as_view()(req)
        assert resp.status_code == 401


# ===========================================================================
# VerifyPhoneOTPView
# ===========================================================================

class TestVerifyPhoneOTPView:

    @pytest.mark.django_db
    def test_verify_phone_otp_success(self):
        app = _app("VerifyPhoneOTP1")
        user = _user("verifyphone1@test.com", phone_cc="33", phone_num="600000020")

        with patch("tenxyte.views.otp_views.OTPService") as MockOTP:
            mock_inst = MagicMock()
            MockOTP.return_value = mock_inst
            mock_inst.verify_phone_otp.return_value = (True, "")
            resp = _authed_post(VerifyPhoneOTPView, "/auth/otp/verify/phone/", user, app,
                                {"code": "654321"})

        assert resp.status_code == 200
        assert "verified" in resp.data["message"].lower()

    @pytest.mark.django_db
    def test_verify_phone_otp_invalid_code_returns_400(self):
        app = _app("VerifyPhoneOTP2")
        user = _user("verifyphone2@test.com", phone_cc="33", phone_num="600000021")

        with patch("tenxyte.views.otp_views.OTPService") as MockOTP:
            mock_inst = MagicMock()
            MockOTP.return_value = mock_inst
            mock_inst.verify_phone_otp.return_value = (False, "Invalid OTP")
            resp = _authed_post(VerifyPhoneOTPView, "/auth/otp/verify/phone/", user, app,
                                {"code": "000000"})

        assert resp.status_code == 400
        assert resp.data["code"] == "OTP_VERIFICATION_FAILED"

    @pytest.mark.django_db
    def test_verify_phone_otp_invalid_data_returns_400(self):
        app = _app("VerifyPhoneOTP3")
        user = _user("verifyphone3@test.com")

        resp = _authed_post(VerifyPhoneOTPView, "/auth/otp/verify/phone/", user, app, {})
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_verify_phone_otp_requires_jwt(self):
        app = _app("VerifyPhoneOTP4")
        factory = APIRequestFactory()
        req = factory.post("/auth/otp/verify/phone/", data={"code": "123456"}, format="json")
        req.application = app
        resp = VerifyPhoneOTPView.as_view()(req)
        assert resp.status_code == 401
