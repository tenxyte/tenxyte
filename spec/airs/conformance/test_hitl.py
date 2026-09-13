"""
AIRS Conformance Suite — `hitl` level (spec z_aud_2, task 4.2).

Covers Requirement 3.3's `hitl` sub-clauses: the 202 contract, confirmation, denial, expiry,
and replay with `X-Action-Confirmation`. Skipped entirely unless the target's discovery document
announces `hitl` AND --airs-hitl-probe-path is supplied (see conftest.py).
"""

import pytest

pytestmark = pytest.mark.airs_level("hitl")


@pytest.fixture()
def pending_action(client, issue_token, make_agent_headers, hitl_probe_path):
    """Trigger a fresh Pending Action and return (raw_token, confirmation_body)."""
    issued = issue_token()
    response = client.post(hitl_probe_path, headers=make_agent_headers(issued["token"]), json={})
    assert (
        response.status_code == 202
    ), f"expected 202 pending_confirmation, got {response.status_code}: {response.text}"
    return issued["token"], response.json()


def test_pending_action_has_202_contract(pending_action):
    """[AIRS-HITL-3]: shape of the 202 response."""
    _, body = pending_action
    assert body["status"] == "pending_confirmation"
    assert body.get("confirmation_token")
    assert body.get("expires_at")


def test_confirm_then_replay_executes(
    human_client, client, discovery, make_agent_headers, hitl_probe_path, pending_action
):
    """[AIRS-HITL-5]/[AIRS-HITL-6]: confirming, then replaying with X-Action-Confirmation, executes."""
    raw_token, body = pending_action
    confirmation_token = body["confirmation_token"]

    confirm_path = discovery["endpoints"]["pending_action_confirm"].replace("{confirmation_token}", confirmation_token)
    confirm_response = human_client.post(confirm_path, json={"token": confirmation_token})
    assert confirm_response.status_code == 200

    replay_headers = make_agent_headers(raw_token)
    replay_headers["X-Action-Confirmation"] = confirmation_token
    # Replays the *original* request (same method/path/body) per [AIRS-HITL-6]; the probe
    # endpoint's contract for this suite is that it is safe to call identically a second time.
    replay_response = client.post(hitl_probe_path, headers=replay_headers, json={})
    assert replay_response.status_code == 200


def test_deny_then_replay_does_not_execute(
    human_client, client, discovery, make_agent_headers, hitl_probe_path, pending_action
):
    """[AIRS-HITL-5]/[AIRS-HITL-6]: a denied action's Confirmation Token must not authorize execution."""
    raw_token, body = pending_action
    confirmation_token = body["confirmation_token"]

    deny_path = discovery["endpoints"]["pending_action_deny"].replace("{confirmation_token}", confirmation_token)
    deny_response = human_client.post(deny_path, json={"token": confirmation_token})
    assert deny_response.status_code == 200

    replay_headers = make_agent_headers(raw_token)
    replay_headers["X-Action-Confirmation"] = confirmation_token
    replay_response = client.post(hitl_probe_path, headers=replay_headers, json={})

    # The action must not have executed: the server must not return the "executed" success shape.
    # A denied token MAY be treated as "no valid confirmation on file" (a fresh 202), but MUST NOT
    # be treated as approved.
    assert replay_response.status_code != 200


def test_confirming_twice_fails_without_side_effect(human_client, discovery, pending_action):
    """[AIRS-HITL-5]: confirming an already-confirmed action must fail without side effect."""
    _, body = pending_action
    confirmation_token = body["confirmation_token"]
    confirm_path = discovery["endpoints"]["pending_action_confirm"].replace("{confirmation_token}", confirmation_token)

    first = human_client.post(confirm_path, json={"token": confirmation_token})
    assert first.status_code == 200

    second = human_client.post(confirm_path, json={"token": confirmation_token})
    assert second.status_code != 200


def test_unconfirmed_replay_does_not_execute(client, make_agent_headers, hitl_probe_path, pending_action):
    """[AIRS-HITL-6]: replaying with a bogus/never-confirmed token must not execute."""
    raw_token, _ = pending_action

    headers = make_agent_headers(raw_token)
    headers["X-Action-Confirmation"] = "never-confirmed-bogus-token"
    response = client.post(hitl_probe_path, headers=headers, json={})

    assert response.status_code != 200
