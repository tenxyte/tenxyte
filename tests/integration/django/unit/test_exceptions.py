"""
Tests for tenxyte.exceptions — custom_exception_handler.
Coverage target: 100% of src/tenxyte/exceptions.py
"""

from unittest.mock import MagicMock

from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.exceptions import (
    NotAuthenticated,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    ValidationError as DRFValidationError,
    NotFound,
)
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404

from tenxyte.exceptions import custom_exception_handler


def _ctx():
    factory = APIRequestFactory()
    request = factory.get("/fake/")
    return {"view": APIView(), "request": request}


class TestCustomExceptionHandler:

    def test_validation_error_dict_codes(self):
        """Dict validation error → VALIDATION_ERROR (L48-52)."""
        exc = DRFValidationError({"email": ["required"]})
        resp = custom_exception_handler(exc, _ctx())
        assert resp.data["code"] == "VALIDATION_ERROR"
        assert resp.data["error"] == "Invalid input."
        assert "email" in resp.data["details"]

    def test_validation_error_list_codes(self):
        """List validation error → uppercased first code (L53-56)."""
        exc = DRFValidationError(detail="Bad value")
        resp = custom_exception_handler(exc, _ctx())
        assert resp.data["code"] == "INVALID"

    def test_not_authenticated_401(self):
        """401 → UNAUTHORIZED (L63-66)."""
        exc = NotAuthenticated()
        resp = custom_exception_handler(exc, _ctx())
        assert resp.status_code == 401
        assert resp.data["code"] == "UNAUTHORIZED"

    def test_drf_permission_denied_403(self):
        """DRF 403 → PERMISSION_DENIED (L67-71)."""
        exc = DRFPermissionDenied()
        resp = custom_exception_handler(exc, _ctx())
        assert resp.status_code == 403
        assert resp.data["code"] == "PERMISSION_DENIED"

    def test_not_found_404(self):
        """404 → NOT_FOUND (L72-75)."""
        exc = NotFound()
        resp = custom_exception_handler(exc, _ctx())
        assert resp.status_code == 404
        assert resp.data["code"] == "NOT_FOUND"

    def test_throttled_429(self):
        """429 → RATE_LIMITED (L76-79)."""
        exc = Throttled(wait=60)
        resp = custom_exception_handler(exc, _ctx())
        assert resp.status_code == 429
        assert resp.data["code"] == "RATE_LIMITED"

    def test_django_http404(self):
        """Django Http404 → 404 (L32-34)."""
        exc = Http404("Page not found")
        resp = custom_exception_handler(exc, _ctx())
        assert resp is not None
        assert resp.status_code == 404
        assert resp.data["code"] == "NOT_FOUND"

    def test_django_permission_denied(self):
        """Django PermissionDenied → 403 (L35-37)."""
        exc = DjangoPermissionDenied("Access denied")
        resp = custom_exception_handler(exc, _ctx())
        assert resp is not None
        assert resp.status_code == 403

    def test_unhandled_returns_none(self):
        """Non-API exception → None (L86)."""
        resp = custom_exception_handler(ValueError("oops"), _ctx())
        assert resp is None

    def test_canonical_shape(self):
        """Response always has error, code, details keys (L82-84)."""
        exc = NotAuthenticated()
        resp = custom_exception_handler(exc, _ctx())
        assert set(resp.data.keys()) == {"error", "code", "details"}

    def test_custom_auth_code_401(self):
        """Custom auth_code attribute on 401 (L64)."""
        exc = NotAuthenticated()
        exc.auth_code = "TOKEN_EXPIRED"
        resp = custom_exception_handler(exc, _ctx())
        assert resp.data["code"] == "TOKEN_EXPIRED"

    def test_custom_auth_code_403(self):
        """Custom auth_code on 403 (L69)."""
        exc = DRFPermissionDenied("Denied")
        exc.auth_code = "INSUFFICIENT_ROLE"
        resp = custom_exception_handler(exc, _ctx())
        assert resp.data["code"] == "INSUFFICIENT_ROLE"

    def test_string_code_branch(self):
        """get_codes returns string → uppercased (L57-60)."""
        exc = NotFound(detail="Resource missing")
        resp = custom_exception_handler(exc, _ctx())
        assert resp.data["code"] == "NOT_FOUND"
        assert resp.data["error"] == "Resource missing"
