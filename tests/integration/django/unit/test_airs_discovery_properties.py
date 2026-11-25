"""
Property-based tests for the AIRS Discovery Endpoint (spec z_aud_2, task 2.2-2.4).

Spec: specs/z_aud_2, design.md "Correctness Properties" 1-3; spec/airs/AIRS-1.0.md §9
([AIRS-DISC-1], [AIRS-DISC-2], [AIRS-DISC-3]).

The view under test performs no I/O beyond `reverse()` against the already-loaded URLconf, so
these tests need no database access except Property 3, which deliberately creates random rows to
prove the response is independent of them.
"""

import json
import uuid
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from hypothesis import HealthCheck, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st
from rest_framework.test import APIRequestFactory

from tenxyte.models.agent import AgentToken
from tenxyte.models.base import get_application_model, get_permission_model, get_user_model
from tenxyte.views.agent_views import AIRSDiscoveryView

User = get_user_model()
Application = get_application_model()
Permission = get_permission_model()

factory = APIRequestFactory()


def _call_discovery():
    request = factory.get("/api/v1/auth/ai/.well-known/airs/")
    response = AIRSDiscoveryView.as_view()(request)
    response.render() if hasattr(response, "render") else None
    return response


# ===========================================================================
# Property 1: Forme et exactitude de la découverte
# ===========================================================================


@hyp_settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(circuit_breaker_enabled=st.booleans(), budget_tracking_enabled=st.booleans())
def test_property_1_discovery_shape_and_conformance_gating(circuit_breaker_enabled, budget_tracking_enabled):
    """
    Feature: z_aud_2, Property 1: Forme et exactitude de la découverte

    Pour toute combinaison de AIRS_CIRCUIT_BREAKER_ENABLED x AIRS_BUDGET_TRACKING_ENABLED
    (AIRS activé), la réponse contient exactement les clés du contrat, airs_version == "1.0",
    et conformance contient guards ssi le circuit breaker est activé et budget ssi le budget
    tracking est activé (core/hitl/trace toujours présents).

    Validates: Requirements 2.1, 2.2
    """
    with override_settings(
        TENXYTE_AIRS_ENABLED=True,
        TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED=circuit_breaker_enabled,
        TENXYTE_AIRS_BUDGET_TRACKING_ENABLED=budget_tracking_enabled,
    ):
        response = _call_discovery()

    assert response.status_code == 200
    body = json.loads(response.content)

    assert set(body.keys()) == {"airs_version", "conformance", "endpoints", "limits"}
    assert body["airs_version"] == "1.0"

    conformance = set(body["conformance"])
    assert {"core", "hitl", "trace"} <= conformance
    assert ("guards" in conformance) is circuit_breaker_enabled
    assert ("budget" in conformance) is budget_tracking_enabled
    assert conformance <= {"core", "hitl", "trace", "guards", "budget"}

    assert set(body["limits"].keys()) >= {"token_max_lifetime", "default_expiry"}
    assert isinstance(body["endpoints"], dict)
    assert body["endpoints"]  # non-empty


def test_endpoint_map_contains_expected_logical_names():
    with override_settings(TENXYTE_AIRS_ENABLED=True):
        response = _call_discovery()

    body = json.loads(response.content)
    assert set(body["endpoints"].keys()) == {
        "tokens",
        "token_detail",
        "token_revoke",
        "token_suspend",
        "token_revoke_all",
        "heartbeat",
        "report_usage",
        "pending_actions",
        "pending_action_confirm",
        "pending_action_deny",
        "discovery",
    }
    # Templated placeholders must be present in id-scoped paths, never a stray real ID.
    assert "{id}" in body["endpoints"]["token_detail"]
    assert "{id}" in body["endpoints"]["heartbeat"]
    assert "{confirmation_token}" in body["endpoints"]["pending_action_confirm"]


# ===========================================================================
# Property 2: Effet nul de la découverte quand AIRS est désactivé
# ===========================================================================


@hyp_settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(circuit_breaker_enabled=st.booleans(), budget_tracking_enabled=st.booleans())
def test_property_2_disabled_airs_yields_404_feature_disabled(circuit_breaker_enabled, budget_tracking_enabled):
    """
    Feature: z_aud_2, Property 2: Effet nul de la découverte quand AIRS est désactivé

    Lorsque AIRS_ENABLED est faux, la découverte répond 404 FEATURE_DISABLED sans effet de
    bord, pour toute forme de configuration des autres settings AIRS.

    Validates: Requirements 2.3
    """
    with override_settings(
        TENXYTE_AIRS_ENABLED=False,
        TENXYTE_AIRS_CIRCUIT_BREAKER_ENABLED=circuit_breaker_enabled,
        TENXYTE_AIRS_BUDGET_TRACKING_ENABLED=budget_tracking_enabled,
    ):
        response = _call_discovery()

    assert response.status_code == 404
    body = json.loads(response.content)
    assert body == {"error": "This feature is not enabled", "code": "FEATURE_DISABLED"}


# ===========================================================================
# Property 3: La découverte ne divulgue jamais de données
# ===========================================================================


@pytest.mark.django_db
@hyp_settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(n_users=st.integers(min_value=0, max_value=5), n_tokens=st.integers(min_value=0, max_value=5))
def test_property_3_discovery_never_discloses_persisted_data(n_users, n_tokens):
    """
    Feature: z_aud_2, Property 3: La découverte ne divulgue jamais de données

    Pour tout état de la base (tokens, users générés aléatoirement), le corps de la réponse de
    découverte est indépendant de cet état.

    Validates: Requirements 2.4
    """
    with override_settings(TENXYTE_AIRS_ENABLED=True):
        baseline = json.loads(_call_discovery().content)

        nonce = uuid.uuid4().hex
        app = Application.create_application(name=f"Prop3App-{nonce}")[0]
        perm = Permission.objects.create(code=f"prop3.perm.{nonce}", name="Prop3 Perm")
        users = []
        for i in range(n_users):
            user = User.objects.create_user(email=f"prop3-{nonce}-{i}@example.com", password="x" * 12)
            user.direct_permissions.add(perm)
            users.append(user)

        for i in range(n_tokens):
            user = (
                users[i % len(users)]
                if users
                else User.objects.create_user(email=f"prop3-fallback-{nonce}-{i}@example.com", password="x" * 12)
            )
            if not users:
                user.direct_permissions.add(perm)
            AgentToken.objects.create(
                token=AgentToken._hash_token(f"raw-{nonce}-{i}"),
                agent_id=f"agent-{i}",
                triggered_by=user,
                application=app,
                expires_at=timezone.now() + timedelta(hours=1),
            )

        after = json.loads(_call_discovery().content)

    assert after == baseline

    body_str = json.dumps(after)
    for user in users:
        assert user.email not in body_str
    for token in AgentToken.objects.all():
        assert token.token not in body_str
