"""
Feature: z_aud_2, Property 5: Le connecteur LangChain authentifie chaque requête
Feature: z_aud_2, Property 8: Le heartbeat respecte la contrainte déclarée

Validates: Requirements 4.3, 4.4, 4.7
"""

import time

import httpx
import respx
from hypothesis import HealthCheck, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from tenxyte_langchain.auth import TenxyteAgentAuth, heartbeat_interval_seconds


@hyp_settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    paths=st.lists(st.sampled_from(["/a/", "/b/c/", "/x/y/z/"]), min_size=1, max_size=20),
    run_id=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
)
def test_property_5_every_request_carries_auth_and_trace(paths, run_id):
    """Every outgoing request through TenxyteAgentAuth carries AgentBearer + non-empty trace ID."""
    auth = TenxyteAgentAuth("raw-token-value", run_id_provider=lambda: run_id)

    with respx.mock(assert_all_called=False) as router:
        for path in set(paths):
            router.get(f"https://airs.test{path}").respond(200, json={})

        with httpx.Client(base_url="https://airs.test", auth=auth) as client:
            for path in paths:
                client.get(path)

        for call in router.calls:
            assert call.request.headers["Authorization"] == "AgentBearer raw-token-value"
            assert call.request.headers.get("X-Prompt-Trace-ID")


@given(required=st.integers(min_value=2, max_value=3600))
def test_property_8_heartbeat_interval_strictly_below_requirement(required):
    """heartbeat_interval_seconds() always returns a value strictly below the declared constraint."""
    interval = heartbeat_interval_seconds(required)
    assert 1 <= interval < required


def test_property_8_background_thread_sends_multiple_heartbeats_and_stops_cleanly():
    """Integration-style check with a very short real interval: the thread fires repeatedly and
    `close()` stops it without raising."""

    calls = []

    class _FakeClient:
        def heartbeat(self, token_id):
            calls.append(token_id)
            return {"status": "ok"}

    auth = TenxyteAgentAuth(
        "raw-token", client=_FakeClient(), token_id="tok-1", heartbeat_required_every=2
    )  # interval = max(1, 2//2) = 1s
    time.sleep(3.5)
    auth.close()

    assert len(calls) >= 2
    assert auth.heartbeat_failed is False


def test_property_8_heartbeat_failure_never_propagates():
    class _FailingClient:
        def heartbeat(self, token_id):
            raise RuntimeError("network blip")

    auth = TenxyteAgentAuth("raw-token", client=_FailingClient(), token_id="tok-1", heartbeat_required_every=2)
    time.sleep(1.5)
    auth.close()  # must not raise

    assert auth.heartbeat_failed is True
