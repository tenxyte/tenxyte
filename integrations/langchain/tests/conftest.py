import pytest
import respx


@pytest.fixture()
def mock_airs(respx_mock=None):
    """A respx router pre-seeded with a working discovery document."""
    with respx.mock(assert_all_called=False) as router:
        router.get("https://airs.test/ai/.well-known/airs/", name="discovery").respond(
            200,
            json={
                "airs_version": "1.0",
                "conformance": ["core", "hitl", "guards", "budget", "trace"],
                "endpoints": {
                    "tokens": "/ai/tokens/",
                    "token_detail": "/ai/tokens/{id}/",
                    "token_revoke": "/ai/tokens/{id}/revoke/",
                    "token_suspend": "/ai/tokens/{id}/suspend/",
                    "token_revoke_all": "/ai/tokens/revoke-all/",
                    "heartbeat": "/ai/tokens/{id}/heartbeat/",
                    "report_usage": "/ai/tokens/{id}/report-usage/",
                    "pending_actions": "/ai/pending-actions/",
                    "pending_action_confirm": "/ai/pending-actions/{confirmation_token}/confirm/",
                    "pending_action_deny": "/ai/pending-actions/{confirmation_token}/deny/",
                    "discovery": "/ai/.well-known/airs/",
                },
                "limits": {"token_max_lifetime": 86400, "default_expiry": 3600},
            },
        )
        yield router


BASE_URL = "https://airs.test"
