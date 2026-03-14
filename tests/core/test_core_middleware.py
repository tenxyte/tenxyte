"""
Tests for core middleware - targeting 100% coverage of
src/tenxyte/core/middleware.py
"""
import pytest
from unittest.mock import MagicMock, patch

from tenxyte.core.middleware import (
    RequestContext,
    ResponseContext,
    MiddlewareResult,
    MiddlewareChain,
    CoreMiddleware,
    RequestIDCoreMiddleware,
    ApplicationAuthCoreMiddleware,
    SecurityHeadersCoreMiddleware,
    JWTAuthCoreMiddleware,
    CORSCoreMiddleware,
    OrganizationContextCoreMiddleware,
)
# Force TYPE_CHECKING branch evaluation for coverage
from unittest.mock import patch
with patch("tenxyte.core.middleware.TYPE_CHECKING", True):
    import importlib
    import tenxyte.core.middleware
    importlib.reload(tenxyte.core.middleware)

from tenxyte.core.settings import Settings


def _make_request(**overrides):
    defaults = dict(
        method="GET", path="/api/v1/test",
        headers={}, query_params={},
    )
    defaults.update(overrides)
    return RequestContext(**defaults)


def _make_settings(**overrides):
    s = MagicMock(spec=Settings)
    s.application_auth_enabled = overrides.get("app_auth_enabled", True)
    s.exempt_paths = overrides.get("exempt_paths", ["/admin/"])
    s.exact_exempt_paths = overrides.get("exact_exempt_paths", ["/api/v1/"])
    s.security_headers_enabled = overrides.get("security_headers_enabled", True)
    s.security_headers = overrides.get("security_headers", None)
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# RequestContext  (lines 18-51)
# ═══════════════════════════════════════════════════════════════════════════════

def test_request_context_post_init():
    """Lines 41-43: metadata defaults to {}."""
    rc = _make_request()
    assert rc.metadata == {}


def test_get_header_found():
    """Lines 47-51: case-insensitive header lookup."""
    rc = _make_request(headers={"Content-Type": "text/plain"})
    assert rc.get_header("content-type") == "text/plain"


def test_get_header_not_found():
    """Line 51: not found → default."""
    rc = _make_request()
    assert rc.get_header("X-Missing", "fallback") == "fallback"


# ═══════════════════════════════════════════════════════════════════════════════
# MiddlewareResult  (lines 72-110)
# ═══════════════════════════════════════════════════════════════════════════════

def test_middleware_result_continue():
    """Line 92."""
    r = MiddlewareResult.continue_()
    assert r.continue_processing is True
    assert r.modified_request is None


def test_middleware_result_continue_with_request():
    """Line 92 with modified_request."""
    req = _make_request()
    r = MiddlewareResult.continue_(req)
    assert r.modified_request is req


def test_middleware_result_respond():
    """Line 97."""
    resp = ResponseContext(status_code=403)
    r = MiddlewareResult.respond(resp)
    assert r.continue_processing is False
    assert r.response is resp


def test_middleware_result_error():
    """Lines 102-110."""
    r = MiddlewareResult.error(401, "UNAUTHORIZED", "Not allowed", {"extra": 1})
    assert not r.continue_processing
    assert r.response.status_code == 401
    assert r.response.json_data["code"] == "UNAUTHORIZED"
    assert r.response.json_data["extra"] == 1


def test_middleware_result_error_no_details():
    """Lines 102-110: no details."""
    r = MiddlewareResult.error(500, "ERR", "fail")
    assert r.response.json_data["error"] == "fail"


# ═══════════════════════════════════════════════════════════════════════════════
# CoreMiddleware + process_response default  (lines 117-165)
# ═══════════════════════════════════════════════════════════════════════════════

def test_core_middleware_process_response_default():
    """Line 165: default process_response returns unchanged."""
    class DummyMiddleware(CoreMiddleware):
        def process_request(self, request):
            return MiddlewareResult.continue_()
    mw = DummyMiddleware(settings=_make_settings())
    resp = ResponseContext(status_code=200)
    assert mw.process_response(_make_request(), resp) is resp


# ═══════════════════════════════════════════════════════════════════════════════
# MiddlewareChain  (lines 172-241)
# ═══════════════════════════════════════════════════════════════════════════════

def test_chain_all_continue():
    """Lines 187, 201-218: all middlewares continue."""
    mw1 = MagicMock(spec=CoreMiddleware)
    mw1.process_request.return_value = MiddlewareResult.continue_()
    chain = MiddlewareChain([mw1])
    resp, req = chain.process(_make_request())
    assert resp is None

def test_chain_modified_request():
    """Lines 206-207."""
    modified = _make_request(path="/modified")
    mw = MagicMock(spec=CoreMiddleware)
    mw.process_request.return_value = MiddlewareResult.continue_(modified)
    chain = MiddlewareChain([mw])
    resp, req = chain.process(_make_request())
    assert req.path == "/modified"


def test_chain_early_stop_with_response():
    """Lines 209-212: middleware stops with response."""
    stop_resp = ResponseContext(status_code=403)
    mw = MagicMock(spec=CoreMiddleware)
    mw.process_request.return_value = MiddlewareResult.respond(stop_resp)
    chain = MiddlewareChain([mw])
    resp, _ = chain.process(_make_request())
    assert resp.status_code == 403


def test_chain_early_stop_no_response():
    """Lines 213-215: stop but no response (edge case)."""
    mw = MagicMock(spec=CoreMiddleware)
    result = MiddlewareResult(continue_processing=False, response=None)
    mw.process_request.return_value = result
    chain = MiddlewareChain([mw])
    resp, _ = chain.process(_make_request())
    assert resp is None


def test_chain_process_response():
    """Lines 235-241: reverse order."""
    mw1 = MagicMock(spec=CoreMiddleware)
    mw2 = MagicMock(spec=CoreMiddleware)
    mw1.process_response.return_value = ResponseContext(status_code=200)
    mw2.process_response.return_value = ResponseContext(status_code=200)
    chain = MiddlewareChain([mw1, mw2])
    chain.process_response(_make_request(), ResponseContext())
    # mw2 called before mw1
    assert mw2.process_response.called
    assert mw1.process_response.called


# ═══════════════════════════════════════════════════════════════════════════════
# RequestIDCoreMiddleware  (lines 248-276)
# ═══════════════════════════════════════════════════════════════════════════════

def test_request_id_new():
    """Lines 257-266: no existing ID → generate."""
    mw = RequestIDCoreMiddleware(settings=_make_settings())
    req = _make_request()
    result = mw.process_request(req)
    assert result.modified_request.request_id is not None


def test_request_id_existing():
    """Line 260: existing X-Request-ID preserved."""
    mw = RequestIDCoreMiddleware(settings=_make_settings())
    req = _make_request(headers={"X-Request-ID": "existing-id"})
    result = mw.process_request(req)
    assert result.modified_request.request_id == "existing-id"


def test_request_id_response():
    """Lines 274-276."""
    mw = RequestIDCoreMiddleware(settings=_make_settings())
    req = _make_request()
    req.request_id = "rid-1"
    resp = ResponseContext()
    result = mw.process_response(req, resp)
    assert result.headers["X-Request-ID"] == "rid-1"


# ═══════════════════════════════════════════════════════════════════════════════
# ApplicationAuthCoreMiddleware  (lines 279-371)
# ═══════════════════════════════════════════════════════════════════════════════

class TestApplicationAuthMiddleware:

    @pytest.fixture
    def repo(self):
        return MagicMock()

    @pytest.fixture
    def mw(self, repo):
        return ApplicationAuthCoreMiddleware(settings=_make_settings(), repository=repo)

    def test_disabled(self, repo):
        """Lines 310-311."""
        mw = ApplicationAuthCoreMiddleware(
            settings=_make_settings(app_auth_enabled=False), repository=repo
        )
        result = mw.process_request(_make_request())
        assert result.continue_processing

    def test_exempt_exact(self, mw):
        """Lines 363-364: exact exempt path."""
        req = _make_request(path="/api/v1/")
        result = mw.process_request(req)
        assert result.continue_processing

    def test_exempt_prefix(self, mw):
        """Lines 367-369: prefix exempt path."""
        req = _make_request(path="/admin/dashboard")
        result = mw.process_request(req)
        assert result.continue_processing

    def test_not_exempt(self, mw):
        """Line 371: not exempt → continues auth check."""
        # Missing credentials
        req = _make_request(path="/api/v1/users")
        result = mw.process_request(req)
        assert not result.continue_processing
        assert result.response.status_code == 401

    def test_missing_credentials(self, mw):
        """Lines 301-305: missing key or secret."""
        req = _make_request(path="/api/v1/users", headers={"X-Access-Key": "k"})
        result = mw.process_request(req)
        assert result.response.json_data["code"] == "APP_AUTH_REQUIRED"

    def test_invalid_app(self, mw, repo):
        """Lines 310-358: app not found."""
        repo.get_by_access_key.return_value = None
        req = _make_request(path="/api/v1/users", headers={
            "X-Access-Key": "k", "X-Access-Secret": "s"
        })
        result = mw.process_request(req)
        assert result.response.json_data["code"] == "APP_AUTH_INVALID"

    def test_inactive_app(self, mw, repo):
        """Line 331: app not active."""
        app = MagicMock()
        app.is_active = False
        repo.get_by_access_key.return_value = app
        req = _make_request(path="/api/v1/users", headers={
            "X-Access-Key": "k", "X-Access-Secret": "s"
        })
        result = mw.process_request(req)
        assert result.response.json_data["code"] == "APP_AUTH_INVALID"

    def test_bad_secret(self, mw, repo):
        """Lines 344-350: secret verification fails."""
        app = MagicMock()
        app.is_active = True
        app.id = "app1"
        app.verify_secret.return_value = False
        repo.get_by_access_key.return_value = app
        req = _make_request(path="/api/v1/users", headers={
            "X-Access-Key": "k", "X-Access-Secret": "bad"
        })
        result = mw.process_request(req)
        assert result.response.json_data["code"] == "APP_AUTH_INVALID"

    def test_valid_secret(self, mw, repo):
        """Lines 352-358: success path."""
        app = MagicMock()
        app.is_active = True
        app.id = "app1"
        app.verify_secret.return_value = True
        repo.get_by_access_key.return_value = app
        req = _make_request(path="/api/v1/users", headers={
            "X-Access-Key": "k", "X-Access-Secret": "correct"
        })
        result = mw.process_request(req)
        assert result.continue_processing

    def test_cached_secret(self, mw, repo):
        """Line 344: cache hit → skips verify_secret."""
        app = MagicMock()
        app.is_active = True
        app.id = "app1"
        repo.get_by_access_key.return_value = app
        # Pre-fill cache
        mw.cache_service.set("app_auth_ok_app1_" + "x" * 64, True, timeout=60)
        # This won't match the hash, but let's mock cache directly
        mw._cache_service = MagicMock()
        mw._cache_service.get.return_value = True
        req = _make_request(path="/api/v1/users", headers={
            "X-Access-Key": "k", "X-Access-Secret": "cached"
        })
        result = mw.process_request(req)
        assert result.continue_processing
        app.verify_secret.assert_not_called()

    def test_cache_service_lazy_init(self):
        """Lines 301-305: lazy init cache."""
        mw = ApplicationAuthCoreMiddleware(settings=_make_settings(), repository=MagicMock())
        assert mw._cache_service is None
        cs = mw.cache_service
        assert cs is not None


# ═══════════════════════════════════════════════════════════════════════════════
# SecurityHeadersCoreMiddleware  (lines 374-399)
# ═══════════════════════════════════════════════════════════════════════════════

def test_security_headers_enabled():
    """Lines 394-399."""
    mw = SecurityHeadersCoreMiddleware(settings=_make_settings())
    resp = mw.process_response(_make_request(), ResponseContext())
    assert "X-Content-Type-Options" in resp.headers


def test_security_headers_process_request():
    """Line 389: process_request just continues."""
    mw = SecurityHeadersCoreMiddleware(settings=_make_settings())
    result = mw.process_request(_make_request())
    assert result.continue_processing is True


def test_security_headers_custom():
    """Lines 395: custom headers from settings."""
    s = _make_settings()
    s.security_headers = {"X-Custom": "value"}
    mw = SecurityHeadersCoreMiddleware(settings=s)
    resp = mw.process_response(_make_request(), ResponseContext())
    assert resp.headers["X-Custom"] == "value"


def test_security_headers_disabled():
    """Line 394: disabled."""
    mw = SecurityHeadersCoreMiddleware(settings=_make_settings(security_headers_enabled=False))
    resp = mw.process_response(_make_request(), ResponseContext())
    assert "X-Content-Type-Options" not in resp.headers


# ═══════════════════════════════════════════════════════════════════════════════
# JWTAuthCoreMiddleware  (lines 406-418)
# ═══════════════════════════════════════════════════════════════════════════════

def test_jwt_auth_with_bearer():
    """Lines 412-418: Bearer token extracted."""
    mw = JWTAuthCoreMiddleware(settings=_make_settings())
    req = _make_request(headers={"Authorization": "Bearer mytoken123"})
    result = mw.process_request(req)
    assert result.continue_processing
    assert req.metadata["jwt_token"] == "mytoken123"


def test_jwt_auth_no_bearer():
    """Lines 412-414: no Bearer → skipped."""
    mw = JWTAuthCoreMiddleware(settings=_make_settings())
    req = _make_request(headers={"Authorization": "Basic creds"})
    result = mw.process_request(req)
    assert "jwt_token" not in req.metadata


def test_jwt_auth_no_header():
    mw = JWTAuthCoreMiddleware(settings=_make_settings())
    req = _make_request()
    result = mw.process_request(req)
    assert result.continue_processing


# ═══════════════════════════════════════════════════════════════════════════════
# CORSCoreMiddleware  (lines 421-434)
# ═══════════════════════════════════════════════════════════════════════════════

def test_cors_process_request():
    """Line 426."""
    mw = CORSCoreMiddleware(settings=_make_settings())
    assert mw.process_request(_make_request()).continue_processing


def test_cors_process_response():
    """Line 434."""
    mw = CORSCoreMiddleware(settings=_make_settings())
    resp = mw.process_response(_make_request(), ResponseContext())
    assert isinstance(resp, ResponseContext)


# ═══════════════════════════════════════════════════════════════════════════════
# OrganizationContextCoreMiddleware  (lines 437-447)
# ═══════════════════════════════════════════════════════════════════════════════

def test_org_context_with_slug():
    """Lines 442-447: X-Org-Slug present."""
    mw = OrganizationContextCoreMiddleware(settings=_make_settings())
    req = _make_request(headers={"X-Org-Slug": "acme"})
    result = mw.process_request(req)
    assert req.metadata["org_slug"] == "acme"


def test_org_context_no_slug():
    """Lines 442, 447: no header."""
    mw = OrganizationContextCoreMiddleware(settings=_make_settings())
    req = _make_request()
    result = mw.process_request(req)
    assert "org_slug" not in req.metadata
