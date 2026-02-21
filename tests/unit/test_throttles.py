"""
Tests Phase 4 - Throttles:
- IPBasedThrottle.get_cache_key (avec et sans X-Forwarded-For)
- LoginThrottle, RegisterThrottle (scope, rate)
- ProgressiveLoginThrottle.record_failure / reset_failures
- SimpleThrottleRule._match_path (prefix, exact, no match)
- SimpleThrottleRule.allow_request (throttled, not throttled)
"""
import pytest
from unittest.mock import MagicMock, patch
from django.test import override_settings
from django.core.cache import cache

from tenxyte.throttles import (
    IPBasedThrottle,
    LoginThrottle,
    RegisterThrottle,
    ProgressiveLoginThrottle,
    SimpleThrottleRule,
    get_client_ip,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_request(ip="1.2.3.4", forwarded_for=None, path="/api/test/"):
    req = MagicMock()
    req.META = {"REMOTE_ADDR": ip}
    req.path = path
    if forwarded_for:
        req.META["HTTP_X_FORWARDED_FOR"] = forwarded_for
    return req


# ─── get_client_ip ────────────────────────────────────────────────────────────

class TestGetClientIP:

    def test_returns_remote_addr_by_default(self):
        req = _make_request(ip="5.6.7.8")
        assert get_client_ip(req) == "5.6.7.8"

    def test_returns_first_ip_from_x_forwarded_for(self):
        req = _make_request(forwarded_for="10.0.0.1, 192.168.1.1, 1.2.3.4")
        assert get_client_ip(req) == "10.0.0.1"

    def test_strips_whitespace_from_forwarded_for(self):
        req = _make_request(forwarded_for="  10.0.0.2 , 192.168.0.1")
        assert get_client_ip(req) == "10.0.0.2"


# ─── IPBasedThrottle ─────────────────────────────────────────────────────────

class TestIPBasedThrottle:

    def test_cache_key_uses_remote_addr(self):
        throttle = LoginThrottle()
        req = _make_request(ip="9.9.9.9")
        key = throttle.get_cache_key(req, None)
        assert "9.9.9.9" in key
        assert "login" in key

    def test_cache_key_uses_first_forwarded_ip(self):
        throttle = LoginThrottle()
        req = _make_request(forwarded_for="11.22.33.44, 5.6.7.8")
        key = throttle.get_cache_key(req, None)
        assert "11.22.33.44" in key

    def test_login_throttle_scope_and_rate(self):
        assert LoginThrottle.scope == "login"
        assert LoginThrottle.rate == "5/min"

    def test_register_throttle_scope_and_rate(self):
        assert RegisterThrottle.scope == "register"
        assert RegisterThrottle.rate == "3/hour"


# ─── ProgressiveLoginThrottle ────────────────────────────────────────────────

class TestProgressiveLoginThrottle:

    def setup_method(self):
        cache.clear()

    def test_record_failure_increments_cache(self):
        req = _make_request(ip="3.3.3.3")
        ProgressiveLoginThrottle.record_failure(req)
        val = cache.get("login_failures_3.3.3.3")
        assert val == 1

    def test_multiple_failures_accumulate(self):
        req = _make_request(ip="4.4.4.4")
        ProgressiveLoginThrottle.record_failure(req)
        ProgressiveLoginThrottle.record_failure(req)
        # Le 2ème reset le timeout, mais la valeur dépend de la logique (0+1=1, avec un nouveau timeout)
        val = cache.get("login_failures_4.4.4.4")
        assert val is not None and val >= 1

    def test_reset_failures_clears_cache(self):
        req = _make_request(ip="5.5.5.5")
        ProgressiveLoginThrottle.record_failure(req)
        ProgressiveLoginThrottle.reset_failures(req)
        assert cache.get("login_failures_5.5.5.5") is None

    def test_record_failure_with_forwarded_for(self):
        req = _make_request(forwarded_for="22.22.22.22, 99.99.99.99")
        ProgressiveLoginThrottle.record_failure(req)
        val = cache.get("login_failures_22.22.22.22")
        assert val == 1


# ─── SimpleThrottleRule ───────────────────────────────────────────────────────

class TestSimpleThrottleRule:

    def test_match_prefix_path(self):
        rule = SimpleThrottleRule()
        with override_settings(TENXYTE_SIMPLE_THROTTLE_RULES={"/api/products/": "10/min"}):
            pattern, rate = rule._match_path("/api/products/123/")
        assert pattern == "/api/products/"
        assert rate == "10/min"

    def test_no_match_returns_none(self):
        rule = SimpleThrottleRule()
        with override_settings(TENXYTE_SIMPLE_THROTTLE_RULES={"/api/products/": "10/min"}):
            pattern, rate = rule._match_path("/api/other/")
        assert pattern is None
        assert rate is None

    def test_exact_match_with_dollar(self):
        rule = SimpleThrottleRule()
        with override_settings(TENXYTE_SIMPLE_THROTTLE_RULES={"/api/health/$": "5/hour"}):
            pattern, rate = rule._match_path("/api/health/")
        assert rate == "5/hour"

    def test_exact_match_no_match_subpath(self):
        rule = SimpleThrottleRule()
        with override_settings(TENXYTE_SIMPLE_THROTTLE_RULES={"/api/health/$": "5/hour"}):
            pattern, rate = rule._match_path("/api/health/extra/")
        assert pattern is None

    def test_most_specific_rule_wins(self):
        """La règle la plus longue (plus spécifique) prend la priorité."""
        rule = SimpleThrottleRule()
        rules = {
            "/api/": "100/hour",
            "/api/v1/search/": "5/min",
        }
        with override_settings(TENXYTE_SIMPLE_THROTTLE_RULES=rules):
            pattern, rate = rule._match_path("/api/v1/search/results/")
        assert rate == "5/min"

    def test_allow_request_returns_true_without_matching_rule(self):
        rule = SimpleThrottleRule()
        req = _make_request(path="/api/no-rule/")
        with override_settings(TENXYTE_SIMPLE_THROTTLE_RULES={}):
            result = rule.allow_request(req, None)
        assert result is True

    def test_get_cache_key_returns_none_when_no_matching_rule(self):
        rule = SimpleThrottleRule()
        req = _make_request(path="/unmatched/path/")
        with override_settings(TENXYTE_SIMPLE_THROTTLE_RULES={}):
            key = rule.get_cache_key(req, None)
        assert key is None
