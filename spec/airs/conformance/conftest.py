"""
AIRS Conformance Suite — shared fixtures (spec z_aud_2, task 4.1).

Black-box HTTP test harness for AIRS/1.0 (spec/airs/AIRS-1.0.md). Runnable against ANY
implementation, not just Tenxyte: every fixture here speaks only the wire protocol defined by
the spec (via the Discovery Endpoint, [AIRS-DISC-1]) and never imports server-side code.
Everything implementation-specific is parameterized through CLI options.

Usage:
    pytest spec/airs/conformance \\
        --airs-base-url http://localhost:8000/api/v1/auth \\
        --airs-user-jwt eyJ... \\
        --airs-test-permission conformance.test \\
        [--airs-app-key ... --airs-app-secret ...]
"""

import time
import uuid

import httpx
import pytest


def pytest_addoption(parser):
    group = parser.getgroup("airs-conformance")
    group.addoption(
        "--airs-base-url",
        action="store",
        default=None,
        help="Base URL of the AIRS-hosting API (e.g. http://localhost:8000/api/v1/auth). Required.",
    )
    group.addoption(
        "--airs-user-jwt",
        action="store",
        default=None,
        help="Bearer JWT for the Delegating User the suite acts as. Required.",
    )
    group.addoption(
        "--airs-app-key",
        action="store",
        default="",
        help="X-Access-Key application credential, if the target requires one.",
    )
    group.addoption(
        "--airs-app-secret",
        action="store",
        default="",
        help="X-Access-Secret application credential, if the target requires one.",
    )
    group.addoption(
        "--airs-test-permission",
        action="store",
        default="conformance.test",
        help="Permission code the --airs-user-jwt user is known to hold; granted to issued "
        "Agent Tokens by default. Default: conformance.test.",
    )
    group.addoption(
        "--airs-other-permission",
        action="store",
        default="",
        help="A second, different permission code the --airs-user-jwt user also holds, used only "
        "to test a token scoped away from --airs-test-permission (Double Validation's grant-scope "
        "check needs a genuinely held permission, not an empty grant). Defaults to 'security.view'.",
    )
    group.addoption(
        "--airs-discovery-path",
        action="store",
        default="/ai/.well-known/airs/",
        help="Path of the Discovery Endpoint relative to --airs-base-url.",
    )
    group.addoption(
        "--airs-conformance-probe-path",
        action="store",
        default="",
        help="Path (relative to --airs-base-url) of a demo endpoint gated by the target's "
        "equivalent of @require_agent_clearance(permission_code=<--airs-test-permission>), "
        "returning 200 on success. AIRS's core value (permission-gated business actions) is "
        "provided by integrator code, not a fixed protocol endpoint, so Double Validation and "
        "generic AgentBearer authentication can only be exercised against a real gated route. "
        "Tests needing it skip cleanly when this option is omitted.",
    )
    group.addoption(
        "--airs-hitl-probe-path",
        action="store",
        default="",
        help="Path (relative to --airs-base-url) of a demo endpoint gated by the target's "
        "equivalent of @require_agent_clearance(permission_code=..., human_in_the_loop_required=True). "
        "HITL tests skip cleanly when this option is omitted.",
    )
    group.addoption(
        "--airs-audit-log-path",
        action="store",
        default="",
        help="Path (relative to --airs-base-url), human-authenticated, listing recent audit "
        "entries as JSON containing a 'prompt_trace_id' (or similarly named) field, used to "
        "verify [AIRS-TRACE-3] persistence. Trace-persistence retrieval test skips without it.",
    )


def _app_headers(config):
    headers = {}
    key = config.getoption("--airs-app-key")
    secret = config.getoption("--airs-app-secret")
    if key:
        headers["X-Access-Key"] = key
    if secret:
        headers["X-Access-Secret"] = secret
    return headers


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "airs_level(name): this test exercises the given AIRS Conformance Level ('core', 'hitl', "
        "'guards', 'budget', 'trace'); skipped automatically when the target's discovery "
        "document does not announce that level ([AIRS-DISC-1]).",
    )

    base_url = config.getoption("--airs-base-url")
    if not base_url:
        # Collection proceeds; individual tests fail loudly via the `discovery`/`base_url`
        # fixtures if they actually need a target. This lets `pytest --collect-only` work with
        # no options at all.
        config._airs_discovery = None
        config._airs_discovery_error = "no --airs-base-url given"
        return

    url = base_url.rstrip("/") + config.getoption("--airs-discovery-path")
    try:
        response = httpx.get(url, headers=_app_headers(config), timeout=10)
        response.raise_for_status()
        config._airs_discovery = response.json()
        config._airs_discovery_error = None
    except Exception as exc:  # noqa: BLE001 — any failure here degrades to "discovery unavailable"
        config._airs_discovery = None
        config._airs_discovery_error = repr(exc)


def pytest_collection_modifyitems(config, items):
    discovery = config._airs_discovery
    announced = set(discovery["conformance"]) if discovery else set()

    for item in items:
        levels = [m.args[0] for m in item.iter_markers(name="airs_level")]
        if not levels:
            continue
        if discovery is None:
            item.add_marker(pytest.mark.skip(reason=f"AIRS discovery unreachable: {config._airs_discovery_error}"))
            continue
        missing = [level for level in levels if level not in announced]
        if missing:
            item.add_marker(
                pytest.mark.skip(reason=f"Implementation does not announce conformance level(s): {missing}")
            )


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    url = pytestconfig.getoption("--airs-base-url")
    if not url:
        pytest.fail("--airs-base-url is required")
    return url.rstrip("/")


@pytest.fixture(scope="session")
def user_jwt(pytestconfig):
    token = pytestconfig.getoption("--airs-user-jwt")
    if not token:
        pytest.fail("--airs-user-jwt is required")
    return token


@pytest.fixture(scope="session")
def test_permission(pytestconfig):
    return pytestconfig.getoption("--airs-test-permission")


@pytest.fixture(scope="session")
def app_headers(pytestconfig):
    return _app_headers(pytestconfig)


@pytest.fixture(scope="session")
def discovery(pytestconfig):
    """The Discovery document ([AIRS-DISC-1]), fetched once at collection time."""
    doc = pytestconfig._airs_discovery
    if doc is None:
        pytest.fail(f"AIRS discovery unavailable: {pytestconfig._airs_discovery_error}")
    return doc


@pytest.fixture()
def client(base_url, app_headers):
    with httpx.Client(base_url=base_url, headers=dict(app_headers), timeout=10) as c:
        yield c


@pytest.fixture()
def human_client(client, user_jwt):
    """An httpx client authenticated as the Delegating User (`Authorization: Bearer <jwt>`)."""
    client.headers["Authorization"] = f"Bearer {user_jwt}"
    return client


def agent_headers(raw_token: str, trace_id: str | None = None) -> dict:
    """Build the `AgentBearer` + optional `X-Prompt-Trace-ID` headers ([§4](../AIRS-1.0.md#4-wire-protocol))."""
    headers = {"Authorization": f"AgentBearer {raw_token}"}
    if trace_id:
        headers["X-Prompt-Trace-ID"] = trace_id
    return headers


@pytest.fixture()
def make_agent_headers():
    return agent_headers


@pytest.fixture()
def issue_token(human_client, discovery, test_permission):
    """
    Factory fixture: issue_token(permissions=..., **extra) -> dict (the parsed 201 body).

    Issues a fresh Agent Token as the Delegating User via the discovered `tokens` endpoint
    ([AIRS-CORE-14]). Defaults to granting exactly `--airs-test-permission`.
    """

    def _issue(permissions=None, agent_id=None, **extra):
        payload = {
            "agent_id": agent_id or f"conformance-{uuid.uuid4().hex[:12]}",
            "permissions": [test_permission] if permissions is None else permissions,
            **extra,
        }
        response = human_client.post(discovery["endpoints"]["tokens"], json=payload)
        assert response.status_code == 201, f"token issuance failed: {response.status_code} {response.text}"
        return response.json()

    return _issue


@pytest.fixture()
def unique_agent_id():
    return f"conformance-{uuid.uuid4().hex[:12]}"


@pytest.fixture()
def conformance_probe_path(pytestconfig):
    path = pytestconfig.getoption("--airs-conformance-probe-path")
    if not path:
        pytest.skip("--airs-conformance-probe-path not supplied for this target")
    return path


@pytest.fixture()
def hitl_probe_path(pytestconfig):
    path = pytestconfig.getoption("--airs-hitl-probe-path")
    if not path:
        pytest.skip("--airs-hitl-probe-path not supplied for this target")
    return path


@pytest.fixture()
def audit_log_path(pytestconfig):
    path = pytestconfig.getoption("--airs-audit-log-path")
    if not path:
        pytest.skip("--airs-audit-log-path not supplied for this target")
    return path


def wait_until(predicate, timeout=5.0, interval=0.2):
    """Poll `predicate()` until truthy or timeout; returns the last (possibly falsy) result."""
    deadline = time.monotonic() + timeout
    result = predicate()
    while not result and time.monotonic() < deadline:
        time.sleep(interval)
        result = predicate()
    return result
