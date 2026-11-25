"""
AIRS Conformance Suite — `guards` level (spec z_aud_2, task 4.2).

Covers Requirement 3.3's `guards` sub-clauses: rate/circuit-breaker suspension and
heartbeat-missing suspension ([§6.1](../AIRS-1.0.md#61-circuit-breaker),
[§6.2](../AIRS-1.0.md#62-dead-mans-switch)).

These use the `heartbeat` endpoint itself both as the agent-callable action to repeat/delay, and
as the thing whose rejection we observe — no separate probe endpoint is needed, since heartbeat
is a normative, unconditionally agent-callable endpoint once `guards` is announced.
"""

import time

import pytest

pytestmark = pytest.mark.airs_level("guards")


def _heartbeat(client, discovery, token_id, raw_token, make_agent_headers):
    path = discovery["endpoints"]["heartbeat"].replace("{id}", str(token_id))
    return client.post(path, headers=make_agent_headers(raw_token))


def test_rate_limit_threshold_suspends_token(client, discovery, issue_token, make_agent_headers):
    """[AIRS-GUARDS-1]/[AIRS-GUARDS-2]: exceeding max_requests_per_minute suspends the token."""
    issued = issue_token(circuit_breaker={"max_requests_per_minute": 2})

    statuses = [
        _heartbeat(client, discovery, issued["id"], issued["token"], make_agent_headers).status_code for _ in range(6)
    ]

    assert 403 in statuses, f"expected a 403 suspension once the RPM threshold was exceeded, got {statuses}"


def test_heartbeat_missing_suspends_token(client, discovery, issue_token, make_agent_headers):
    """[AIRS-GUARDS-3]/[AIRS-GUARDS-4]: a missed heartbeat window suspends the token."""
    issued = issue_token(dead_mans_switch={"heartbeat_required_every": 1})

    time.sleep(2.5)

    response = _heartbeat(client, discovery, issued["id"], issued["token"], make_agent_headers)
    assert response.status_code == 403


def test_suspension_persists_across_subsequent_requests(client, discovery, issue_token, make_agent_headers):
    """[AIRS-CORE-9]: once suspended by a Guardrail, the token stays rejected on further use."""
    issued = issue_token(circuit_breaker={"max_requests_per_minute": 1})

    for _ in range(4):
        _heartbeat(client, discovery, issued["id"], issued["token"], make_agent_headers)

    # By now the token should be suspended; confirm it stays that way on the next attempt too.
    response = _heartbeat(client, discovery, issued["id"], issued["token"], make_agent_headers)
    assert response.status_code == 403
