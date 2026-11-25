"""
AIRS Conformance Suite — `budget` level (spec z_aud_2, task 4.2).

Covers Requirement 3.3's `budget` sub-clauses: usage reporting, accumulation, and
`BUDGET_EXCEEDED` suspension ([§6.3](../AIRS-1.0.md#63-budget)).
"""

import pytest

pytestmark = pytest.mark.airs_level("budget")


def _report(client, discovery, token_id, raw_token, make_agent_headers, cost_usd):
    path = discovery["endpoints"]["report_usage"].replace("{id}", str(token_id))
    return client.post(
        path,
        headers=make_agent_headers(raw_token),
        json={"cost_usd": cost_usd, "prompt_tokens": 100, "completion_tokens": 50},
    )


def test_usage_report_accepted_under_budget(client, discovery, issue_token, make_agent_headers):
    """[AIRS-BUDGET-1]/[AIRS-BUDGET-2]: usage below the limit is accepted."""
    issued = issue_token(budget_limit_usd=10.0)

    response = _report(client, discovery, issued["id"], issued["token"], make_agent_headers, cost_usd=1.0)
    assert response.status_code == 200


def test_usage_accumulates_and_exceeding_it_suspends(client, discovery, issue_token, make_agent_headers):
    """[AIRS-BUDGET-2]/[AIRS-BUDGET-3]: reported cost accumulates; crossing the limit suspends."""
    issued = issue_token(budget_limit_usd=1.0)

    first = _report(client, discovery, issued["id"], issued["token"], make_agent_headers, cost_usd=0.6)
    assert first.status_code == 200

    second = _report(client, discovery, issued["id"], issued["token"], make_agent_headers, cost_usd=0.6)
    assert second.status_code == 403
    body = second.json()
    assert "suspend" in str(body).lower() or "budget" in str(body).lower()


def test_suspended_token_rejected_on_further_use(client, discovery, issue_token, make_agent_headers):
    """[AIRS-CORE-9]: once BUDGET_EXCEEDED-suspended, the token stays rejected."""
    issued = issue_token(budget_limit_usd=0.5)

    _report(client, discovery, issued["id"], issued["token"], make_agent_headers, cost_usd=0.6)

    response = _report(client, discovery, issued["id"], issued["token"], make_agent_headers, cost_usd=0.0)
    assert response.status_code == 403
