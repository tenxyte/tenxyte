"""
AIRS Conformance Suite — `trace` level (spec z_aud_2, task 4.2).

Covers Requirement 3.3's `trace` sub-clause: `X-Prompt-Trace-ID` propagation and persistence
([§4.3](../AIRS-1.0.md#43-header-x-prompt-trace-id)).
"""

import uuid

import pytest

pytestmark = pytest.mark.airs_level("trace")


def test_wellformed_trace_id_does_not_affect_success(client, discovery, issue_token, make_agent_headers):
    """[AIRS-TRACE-2]: a well-formed trace ID must not change the outcome of an otherwise-valid request."""
    issued = issue_token()
    heartbeat_path = discovery["endpoints"]["heartbeat"].replace("{id}", str(issued["id"]))

    trace_id = f"conformance-trace-{uuid.uuid4().hex}"
    response = client.post(heartbeat_path, headers=make_agent_headers(issued["token"], trace_id=trace_id))

    assert response.status_code == 200


def test_malformed_trace_id_is_ignored_not_rejected(client, discovery, issue_token, make_agent_headers):
    """[AIRS-TRACE-2]: a malformed trace ID (disallowed characters) must be dropped, not rejected."""
    issued = issue_token()
    heartbeat_path = discovery["endpoints"]["heartbeat"].replace("{id}", str(issued["id"]))

    headers = make_agent_headers(issued["token"])
    headers["X-Prompt-Trace-ID"] = "not a valid trace id! contains spaces & punctuation"
    response = client.post(heartbeat_path, headers=headers)

    assert response.status_code == 200


def test_trace_id_persisted_and_retrievable(
    human_client, client, discovery, issue_token, make_agent_headers, audit_log_path
):
    """
    [AIRS-TRACE-3]: a well-formed trace ID on a successful mutating request is retrievable
    through some audit/introspection surface. Requires --airs-audit-log-path (optional; see
    conftest.py) since this specification deliberately does not mandate which record it attaches
    to (Tenxyte's choice: the AuditLog entry — see spec/airs/AIRS-1.0.md Annex A).
    """
    issued = issue_token()
    heartbeat_path = discovery["endpoints"]["heartbeat"].replace("{id}", str(issued["id"]))

    trace_id = f"conformance-retrieval-{uuid.uuid4().hex}"
    response = client.post(heartbeat_path, headers=make_agent_headers(issued["token"], trace_id=trace_id))
    assert response.status_code == 200

    logs_response = human_client.get(audit_log_path)
    assert logs_response.status_code == 200
    assert trace_id in logs_response.text
