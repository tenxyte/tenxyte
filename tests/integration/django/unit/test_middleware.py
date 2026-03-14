"""
Tests for Django middleware wrappers - targeting 100% coverage of
src/tenxyte/adapters/django/middleware.py
"""
import pytest
from unittest.mock import MagicMock, patch

from django.test import RequestFactory
from django.http import HttpResponse, JsonResponse

from tenxyte.adapters.django.middleware import (
    _django_request_to_context,
    _context_to_django_response,
    _update_django_request,
    BaseDjangoMiddleware,
    DjangoRequestIDMiddleware,
    DjangoApplicationAuthMiddleware,
    DjangoSecurityHeadersMiddleware,
    DjangoJWTAuthMiddleware,
    DjangoCORSMiddleware,
    DjangoOrganizationContextMiddleware,
    RequestIDMiddleware,
    ApplicationAuthMiddleware,
    SecurityHeadersMiddleware,
    JWTAuthMiddleware,
    CORSMiddleware,
    OrganizationContextMiddleware,
)
from tenxyte.core.middleware import (
    RequestContext,
    ResponseContext,
    MiddlewareResult,
    RequestIDCoreMiddleware,
    SecurityHeadersCoreMiddleware,
    JWTAuthCoreMiddleware,
    CORSCoreMiddleware,
    OrganizationContextCoreMiddleware,
    ApplicationAuthCoreMiddleware,
)


@pytest.fixture
def rf():
    return RequestFactory()


def _make_ctx(**overrides):
    """Helper: create a RequestContext with sensible defaults."""
    defaults = dict(method="GET", path="/", headers={}, query_params={})
    defaults.update(overrides)
    return RequestContext(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# _django_request_to_context  (lines 41-71)
# ══════════════════════════════════════════════════════════════════════════════

def test_request_to_context_basic(rf):
    """Plain request → context conversion (lines 41-59, 71)."""
    request = rf.get("/test/?a=1", HTTP_USER_AGENT="UA")
    ctx = _django_request_to_context(request)
    assert ctx.method == "GET"
    assert ctx.path == "/test/"
    assert ctx.user_agent == "UA"
    assert ctx.client_ip is not None


def test_request_to_context_x_forwarded_for(rf):
    """X-Forwarded-For first IP is picked (lines 46-48)."""
    request = rf.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8")
    ctx = _django_request_to_context(request)
    assert ctx.client_ip == "1.2.3.4"


def test_request_to_context_remote_addr(rf):
    """Falls back to REMOTE_ADDR when no X-Forwarded-For (lines 49-50)."""
    request = rf.get("/")
    ctx = _django_request_to_context(request)
    assert ctx.client_ip == "127.0.0.1"


def test_request_to_context_request_id(rf):
    """Propagates request_id (lines 62-63)."""
    request = rf.get("/")
    request.request_id = "rid-1"
    ctx = _django_request_to_context(request)
    assert ctx.request_id == "rid-1"


def test_request_to_context_user_id(rf):
    """Propagates user_id (lines 64-65)."""
    request = rf.get("/")
    request.user_id = "uid-1"
    ctx = _django_request_to_context(request)
    assert ctx.user_id == "uid-1"


def test_request_to_context_application_truthy(rf):
    """Propagates application object + sets application_id (lines 66-69)."""
    request = rf.get("/")
    app = MagicMock()
    app.id = 42
    request.application = app
    ctx = _django_request_to_context(request)
    assert ctx.metadata["application"] is app
    assert ctx.application_id == "42"


def test_request_to_context_application_none(rf):
    """Application=None → no application_id (lines 66-68, falsy branch)."""
    request = rf.get("/")
    request.application = None
    ctx = _django_request_to_context(request)
    assert ctx.metadata["application"] is None
    assert ctx.application_id is None


# ══════════════════════════════════════════════════════════════════════════════
# _context_to_django_response  (lines 85-101)
# ══════════════════════════════════════════════════════════════════════════════

def test_response_json():
    """json_data → JsonResponse (lines 85-86)."""
    ctx = ResponseContext(status_code=200, json_data={"ok": True})
    resp = _context_to_django_response(ctx)
    assert isinstance(resp, JsonResponse)
    assert resp.status_code == 200


def test_response_body():
    """body → HttpResponse with Content-Type (lines 87-92)."""
    ctx = ResponseContext(status_code=201, body=b"raw",
                          headers={"Content-Type": "text/plain"})
    resp = _context_to_django_response(ctx)
    assert resp.status_code == 201
    assert resp.content == b"raw"


def test_response_empty():
    """No json or body → empty HttpResponse (lines 93-94)."""
    ctx = ResponseContext(status_code=204)
    resp = _context_to_django_response(ctx)
    assert resp.status_code == 204


def test_response_extra_headers():
    """Extra headers copied, Content-Type skipped for Json (lines 97-99)."""
    ctx = ResponseContext(status_code=200, json_data={"x": 1},
                          headers={"X-Custom": "val", "Content-Type": "application/json"})
    resp = _context_to_django_response(ctx)
    assert resp["X-Custom"] == "val"


# ══════════════════════════════════════════════════════════════════════════════
# _update_django_request  (lines 113-123)
# ══════════════════════════════════════════════════════════════════════════════

def test_update_request_all_fields(rf):
    """All fields propagated (lines 113-123)."""
    request = rf.get("/")
    ctx = _make_ctx()
    ctx.request_id = "rid"
    ctx.user_id = "uid"
    ctx.application_id = "appid"
    ctx.metadata["application"] = "myapp"
    ctx.organization_id = "orgid"
    _update_django_request(request, ctx)
    assert request.request_id == "rid"
    assert request.user_id == "uid"
    assert request.application == "myapp"
    assert request.organization_id == "orgid"
    assert request.tenxyte_context is ctx


def test_update_request_empty(rf):
    """Empty context → only tenxyte_context set (lines 113-123 falsy branches)."""
    request = rf.get("/")
    ctx = _make_ctx()
    _update_django_request(request, ctx)
    assert not hasattr(request, "request_id")
    assert not hasattr(request, "user_id")
    assert not hasattr(request, "application")
    assert not hasattr(request, "organization_id")
    assert request.tenxyte_context is ctx


# ══════════════════════════════════════════════════════════════════════════════
# BaseDjangoMiddleware.__init__ + core_middleware property  (lines 141-151)
# ══════════════════════════════════════════════════════════════════════════════

def test_base_init_and_lazy_property():
    """Lazy init of core middleware (lines 141-143, 148-151)."""
    get_response = MagicMock()
    mw = BaseDjangoMiddleware(get_response, RequestIDCoreMiddleware)
    assert mw._core_middleware is None

    with patch("tenxyte.adapters.django.middleware.Settings") as MS, \
         patch("tenxyte.adapters.django.middleware.DjangoSettingsProvider"):
        MS.return_value = MagicMock()
        cm = mw.core_middleware
    assert cm is not None
    # Second access returns cached instance
    assert mw.core_middleware is cm


# ══════════════════════════════════════════════════════════════════════════════
# BaseDjangoMiddleware.__call__  (lines 156-195)
# ══════════════════════════════════════════════════════════════════════════════

def _build_mw(continue_processing=True, has_response=True, modified_request=None):
    """Helper: BaseDjangoMiddleware with fully mocked Core middleware."""
    inner_response = HttpResponse("ok", status=200)
    get_response = MagicMock(return_value=inner_response)

    mock_core = MagicMock()

    if continue_processing:
        result = MiddlewareResult(continue_processing=True, modified_request=modified_request)
    else:
        if has_response:
            result = MiddlewareResult(
                continue_processing=False,
                response=ResponseContext(status_code=403, json_data={"err": "no"}),
            )
        else:
            result = MiddlewareResult(continue_processing=False, response=None)

    mock_core.process_request.return_value = result
    mock_core.process_response.return_value = ResponseContext(
        status_code=200, headers={"X-Added": "y"}
    )

    mw = BaseDjangoMiddleware.__new__(BaseDjangoMiddleware)
    mw.get_response = get_response
    mw.core_middleware_class = RequestIDCoreMiddleware
    mw._core_middleware = mock_core
    return mw


def test_call_continue(rf):
    """Normal flow → response headers merged (lines 156-195)."""
    mw = _build_mw(continue_processing=True)
    resp = mw(rf.get("/"))
    assert resp.status_code == 200
    assert resp["X-Added"] == "y"


def test_call_stop_with_response(rf):
    """Early stop with ResponseContext (lines 167-169)."""
    mw = _build_mw(continue_processing=False, has_response=True)
    resp = mw(rf.get("/"))
    assert resp.status_code == 403


def test_call_stop_no_response(rf):
    """Edge case: stop + no response → 500 (lines 170-172)."""
    mw = _build_mw(continue_processing=False, has_response=False)
    resp = mw(rf.get("/"))
    assert resp.status_code == 500


def test_call_modified_request(rf):
    """Modified request applied back to Django request (lines 162-164)."""
    ctx = _make_ctx()
    ctx.request_id = "new-rid"
    mw = _build_mw(continue_processing=True, modified_request=ctx)
    request = rf.get("/")
    mw(request)
    assert request.request_id == "new-rid"


def test_call_response_existing_header_not_overwritten(rf):
    """Response header already present → not overwritten (line 192 branch)."""
    inner = HttpResponse("ok", status=200)
    inner["X-Added"] = "original"
    get_response = MagicMock(return_value=inner)

    mock_core = MagicMock()
    mock_core.process_request.return_value = MiddlewareResult(continue_processing=True)
    mock_core.process_response.return_value = ResponseContext(
        status_code=200, headers={"X-Added": "new-value"}
    )

    mw = BaseDjangoMiddleware.__new__(BaseDjangoMiddleware)
    mw.get_response = get_response
    mw.core_middleware_class = RequestIDCoreMiddleware
    mw._core_middleware = mock_core

    resp = mw(rf.get("/"))
    # Original value preserved
    assert resp["X-Added"] == "original"


# ══════════════════════════════════════════════════════════════════════════════
# Concrete middleware __init__  (lines 210, 223, 259, 270, 281, 292)
# ══════════════════════════════════════════════════════════════════════════════

def test_init_request_id():
    mw = DjangoRequestIDMiddleware(MagicMock())
    assert mw.core_middleware_class is RequestIDCoreMiddleware


def test_init_app_auth():
    mw = DjangoApplicationAuthMiddleware(MagicMock())
    assert mw.core_middleware_class is ApplicationAuthCoreMiddleware


def test_init_security_headers():
    mw = DjangoSecurityHeadersMiddleware(MagicMock())
    assert mw.core_middleware_class is SecurityHeadersCoreMiddleware


def test_init_jwt_auth():
    mw = DjangoJWTAuthMiddleware(MagicMock())
    assert mw.core_middleware_class is JWTAuthCoreMiddleware


def test_init_cors():
    mw = DjangoCORSMiddleware(MagicMock())
    assert mw.core_middleware_class is CORSCoreMiddleware


def test_init_org_context():
    mw = DjangoOrganizationContextMiddleware(MagicMock())
    assert mw.core_middleware_class is OrganizationContextCoreMiddleware


# ══════════════════════════════════════════════════════════════════════════════
# DjangoApplicationAuthMiddleware.core_middleware  (lines 228-248)
# ══════════════════════════════════════════════════════════════════════════════

def test_app_auth_core_middleware_property():
    """Exercises PlaceholderApplicationRepository creation (lines 228-248)."""
    mw = DjangoApplicationAuthMiddleware(MagicMock())
    assert mw._core_middleware is None

    with patch("tenxyte.adapters.django.middleware.Settings") as MS, \
         patch("tenxyte.adapters.django.middleware.DjangoSettingsProvider"):
        MS.return_value = MagicMock()
        cm = mw.core_middleware
    assert cm is not None
    assert mw._core_middleware is cm
    # second access → cached
    assert mw.core_middleware is cm


def test_placeholder_repo_get_by_access_key():
    """Exercises PlaceholderApplicationRepository.get_by_access_key (lines 238-242)."""
    mw = DjangoApplicationAuthMiddleware(MagicMock())

    with patch("tenxyte.adapters.django.middleware.Settings") as MS, \
         patch("tenxyte.adapters.django.middleware.DjangoSettingsProvider"):
        MS.return_value = MagicMock()
        cm = mw.core_middleware

    repo = cm.repository  # PlaceholderApplicationRepository instance

    # Mock the Application model to simulate a successful lookup
    mock_app = MagicMock()
    with patch("tenxyte.models.Application") as MockApp:
        MockApp.objects.get.return_value = mock_app
        result = repo.get_by_access_key("some-key")
    assert result is mock_app

    # Simulate DoesNotExist
    with patch("tenxyte.models.Application") as MockApp:
        MockApp.DoesNotExist = Exception
        MockApp.objects.get.side_effect = Exception("not found")
        result = repo.get_by_access_key("bad-key")
    assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# Backward-compat aliases  (lines 298-303)
# ══════════════════════════════════════════════════════════════════════════════

def test_aliases():
    assert RequestIDMiddleware is DjangoRequestIDMiddleware
    assert ApplicationAuthMiddleware is DjangoApplicationAuthMiddleware
    assert SecurityHeadersMiddleware is DjangoSecurityHeadersMiddleware
    assert JWTAuthMiddleware is DjangoJWTAuthMiddleware
    assert CORSMiddleware is DjangoCORSMiddleware
    assert OrganizationContextMiddleware is DjangoOrganizationContextMiddleware
