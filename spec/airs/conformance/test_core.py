"""
AIRS Conformance Suite — `core` level (spec z_aud_2, task 4.2).

Covers Requirement 3.3's `core` sub-clauses: token issuance, single raw-token transmission,
AgentBearer authentication, Double Validation (both directions), revocation, and expiry.

Several tests here need a live, permission-gated business endpoint to observe accept/reject
behavior against — AIRS's core guarantee (a permission-gated action) is provided by integrator
code via a decorator, not by a fixed protocol endpoint, so it cannot be exercised generically
without one. These tests use `conformance_probe_path` and skip cleanly when
--airs-conformance-probe-path is not supplied for the target (see conftest.py and README.md).
"""

import time

import pytest

pytestmark = pytest.mark.airs_level("core")


def test_issuance_returns_active_token_with_raw_value(issue_token):
    """[AIRS-CORE-14]: issuance returns id, raw token, status, and expiry."""
    body = issue_token()

    assert body["status"] == "ACTIVE"
    assert body.get("token"), "issuance response must include the raw token value"
    assert "id" in body
    assert "expires_at" in body


def test_raw_token_not_retransmitted_on_detail_fetch(human_client, discovery, issue_token):
    """[AIRS-CORE-12]: the raw token is transmitted exactly once, at issuance."""
    issued = issue_token()

    detail_path = discovery["endpoints"]["token_detail"].replace("{id}", str(issued["id"]))
    response = human_client.get(detail_path)

    assert response.status_code == 200
    body = response.json()
    # The detail response must not carry the raw secret again under any field.
    assert issued["token"] not in str(body)


def test_revocation_is_human_only_via_own_credential(human_client, discovery, issue_token):
    """[AIRS-CORE-15]: revocation is authenticated as the Delegating User, not the agent."""
    issued = issue_token()
    revoke_path = discovery["endpoints"]["token_revoke"].replace("{id}", str(issued["id"]))

    response = human_client.post(revoke_path)
    assert response.status_code == 200


class TestAgentBearerAndDoubleValidation:
    """Requires --airs-conformance-probe-path — see module docstring."""

    def test_valid_agent_bearer_authenticates(self, client, issue_token, make_agent_headers, conformance_probe_path):
        """[AIRS-CORE-11]/[AIRS-CORE-13]: a fresh, in-scope Agent Token authenticates successfully."""
        issued = issue_token()

        response = client.get(conformance_probe_path, headers=make_agent_headers(issued["token"]))
        assert response.status_code == 200

    def test_garbage_agent_bearer_rejected(self, client, make_agent_headers, conformance_probe_path):
        """[AIRS-CORE-16] condition 1: an unknown token is rejected, distinctly from other conditions."""
        response = client.get(conformance_probe_path, headers=make_agent_headers("not-a-real-token"))
        assert 400 <= response.status_code < 500

    def test_permission_absent_from_grant_rejected(
        self, client, issue_token, make_agent_headers, conformance_probe_path, pytestconfig
    ):
        """[AIRS-CORE-6](a): the token's Granted Permissions do not include the probed permission.

        Grants a *different* permission the Delegating User genuinely holds (issuance itself
        requires that — [AIRS-CORE-2]) rather than an empty list, so the rejection below is
        actually Double Validation's grant-scope check, not a bare "no permissions requested"
        validation error.
        """
        other_permission = pytestconfig.getoption("--airs-other-permission") or "security.view"
        issued = issue_token(permissions=[other_permission])

        response = client.get(conformance_probe_path, headers=make_agent_headers(issued["token"]))
        assert 400 <= response.status_code < 500

    def test_user_lost_permission_rejected(
        self, request, client, issue_token, make_agent_headers, conformance_probe_path, test_permission, user_jwt
    ):
        """
        [AIRS-CORE-6](b): the Delegating User no longer holds the permission, even though it is
        still present in the token's Granted Permissions.

        Requires the optional `revoke_delegating_user_permission(user_id, permission_code)` hook
        — see its contract in the module docstring of conftest.py's sibling fixtures. Tenxyte's
        own CI supplies a concrete implementation; a target without one skips this test.
        """
        try:
            revoke = request.getfixturevalue("revoke_delegating_user_permission")
        except pytest.FixtureLookupError:
            pytest.skip("No revoke_delegating_user_permission() hook supplied for this target")
        # Optional too, but strongly recommended alongside revoke: restores state afterward so
        # this test doesn't permanently break every other test's assumption that the Delegating
        # User holds --airs-test-permission.
        grant = request.getfixturevalue("grant_delegating_user_permission")

        issued = issue_token()
        # Sanity: works before revocation.
        assert client.get(conformance_probe_path, headers=make_agent_headers(issued["token"])).status_code == 200

        try:
            revoke(user_jwt=user_jwt, permission_code=test_permission)

            response = client.get(conformance_probe_path, headers=make_agent_headers(issued["token"]))
            assert 400 <= response.status_code < 500
        finally:
            grant(user_jwt=user_jwt, permission_code=test_permission)

    def test_revoked_token_rejected(
        self, human_client, client, discovery, issue_token, make_agent_headers, conformance_probe_path
    ):
        """[AIRS-CORE-9]/[AIRS-CORE-16] condition 3: a REVOKED token is rejected."""
        issued = issue_token()
        revoke_path = discovery["endpoints"]["token_revoke"].replace("{id}", str(issued["id"]))
        assert human_client.post(revoke_path).status_code == 200

        response = client.get(conformance_probe_path, headers=make_agent_headers(issued["token"]))
        assert 400 <= response.status_code < 500

    def test_expired_token_rejected(self, client, issue_token, make_agent_headers, conformance_probe_path):
        """[AIRS-CORE-10]/[AIRS-CORE-16] condition 4: an EXPIRED token is rejected."""
        issued = issue_token(expires_in=1)
        time.sleep(2)

        response = client.get(conformance_probe_path, headers=make_agent_headers(issued["token"]))
        assert 400 <= response.status_code < 500

    def test_terminal_conditions_yield_pairwise_distinct_codes(
        self, human_client, client, discovery, issue_token, make_agent_headers, conformance_probe_path
    ):
        """[AIRS-CORE-16]: not-found / suspended / revoked / expired must be pairwise distinguishable."""
        revoked = issue_token()
        revoke_path = discovery["endpoints"]["token_revoke"].replace("{id}", str(revoked["id"]))
        human_client.post(revoke_path)

        suspended = issue_token()
        suspend_path = discovery["endpoints"]["token_suspend"].replace("{id}", str(suspended["id"]))
        human_client.post(suspend_path)

        expired = issue_token(expires_in=1)
        time.sleep(2)

        def code_for(raw_token):
            resp = client.get(conformance_probe_path, headers=make_agent_headers(raw_token))
            assert 400 <= resp.status_code < 500
            body = resp.json()
            return body.get("code") or body.get("error")

        codes = {
            "not_found": code_for("not-a-real-token-at-all"),
            "revoked": code_for(revoked["token"]),
            "suspended": code_for(suspended["token"]),
            "expired": code_for(expired["token"]),
        }

        assert len(set(codes.values())) == len(codes), f"expected 4 pairwise-distinct codes, got: {codes}"
