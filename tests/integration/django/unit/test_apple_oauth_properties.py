"""
Property-based tests for Sign in with Apple (AppleOAuthProvider).

Spec: specs/z_aud_1 (Phase 1 "Crédibilité"), Requirement 5, design.md "Correctness Properties".
Network calls to Apple (token endpoint, JWKS) are always mocked — these tests never hit the
network. Referenced as: Feature: z_aud_1, Property N: <text>.
"""

import time

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from django.test import override_settings
from hypothesis import given, settings as hyp_settings, strategies as st
from unittest.mock import patch, MagicMock

from tenxyte.services.social_auth_service import AppleOAuthProvider

# Alphabet restricted to characters valid in Apple's team/client/key identifiers for test purposes.
_ID_ALPHABET = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.", min_size=1, max_size=40
)


def _generate_ec_keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return private_key, private_pem


def _generate_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


# ===========================================================================
# Property 5: Le client secret Apple est un JWT ES256 bien formé et éphémère
# ===========================================================================


@hyp_settings(max_examples=100, deadline=None)
@given(team_id=_ID_ALPHABET, client_id=_ID_ALPHABET, key_id=_ID_ALPHABET)
def test_property_5_apple_client_secret_well_formed_and_ephemeral(team_id, client_id, key_id):
    """Feature: z_aud_1, Property 5: Le client secret Apple est un JWT ES256 bien formé et éphémère."""
    private_key, private_pem = _generate_ec_keypair()
    public_key = private_key.public_key()
    provider = AppleOAuthProvider()

    with override_settings(
        APPLE_CLIENT_ID=client_id, APPLE_TEAM_ID=team_id, APPLE_KEY_ID=key_id, APPLE_PRIVATE_KEY=private_pem
    ):
        secret1 = provider._generate_client_secret()
        secret2 = provider._generate_client_secret()

    assert secret1 is not None

    header = pyjwt.get_unverified_header(secret1)
    assert header["alg"] == "ES256"
    assert header["kid"] == key_id

    claims = pyjwt.decode(secret1, public_key, algorithms=["ES256"], audience="https://appleid.apple.com")
    assert claims["iss"] == team_id
    assert claims["sub"] == client_id
    assert claims["aud"] == "https://appleid.apple.com"
    assert 0 < claims["exp"] - claims["iat"] <= 15777000

    # Ephemeral: never persisted anywhere Tenxyte controls (no DB/cache write in this code path);
    # two calls are independently valid JWTs (equality is not asserted — iat may coincide within
    # the same second, but each is independently well-formed and verifiable).
    assert secret2 is not None
    claims2 = pyjwt.decode(secret2, public_key, algorithms=["ES256"], audience="https://appleid.apple.com")
    assert claims2["sub"] == client_id


# ===========================================================================
# Property 6: Validation fail-closed de l'Apple_ID_Token
# ===========================================================================


@hyp_settings(max_examples=100, deadline=None)
@given(
    bad_iss=st.text(min_size=1, max_size=30).filter(lambda s: s != "https://appleid.apple.com"),
    bad_aud=st.text(min_size=1, max_size=30).filter(lambda s: s != "com.example.app.signin"),
)
def test_property_6_fail_closed_bad_iss_or_aud(bad_iss, bad_aud):
    """Feature: z_aud_1, Property 6: Validation fail-closed de l'Apple_ID_Token (iss/aud incorrects)."""
    signing_key, public_key = _generate_rsa_keypair()
    provider = AppleOAuthProvider()

    token = pyjwt.encode(
        {"sub": "victim", "iss": bad_iss, "aud": bad_aud, "email": "x@example.com", "exp": int(time.time()) + 3600},
        signing_key,
        algorithm="RS256",
    )

    with (
        override_settings(APPLE_CLIENT_ID="com.example.app.signin"),
        patch("jwt.PyJWKClient.get_signing_key_from_jwt", return_value=MagicMock(key=public_key)),
    ):
        result = provider.verify_id_token(token)

    assert result is None


@hyp_settings(max_examples=50, deadline=None)
@given(offset_seconds=st.integers(min_value=1, max_value=10_000_000))
def test_property_6_fail_closed_expired_token(offset_seconds):
    """Feature: z_aud_1, Property 6: Validation fail-closed de l'Apple_ID_Token (expiré)."""
    signing_key, public_key = _generate_rsa_keypair()
    provider = AppleOAuthProvider()

    token = pyjwt.encode(
        {
            "sub": "user",
            "iss": "https://appleid.apple.com",
            "aud": "com.example.app.signin",
            "email": "x@example.com",
            "exp": int(time.time()) - offset_seconds,
        },
        signing_key,
        algorithm="RS256",
    )

    with (
        override_settings(APPLE_CLIENT_ID="com.example.app.signin"),
        patch("jwt.PyJWKClient.get_signing_key_from_jwt", return_value=MagicMock(key=public_key)),
    ):
        result = provider.verify_id_token(token)

    assert result is None


def test_property_6_fail_closed_bad_signature():
    """Feature: z_aud_1, Property 6: signature altérée → refus, aucun effet de bord."""
    signing_key, _ = _generate_rsa_keypair()
    _, wrong_public_key = _generate_rsa_keypair()  # mismatched key pair simulates a forged signature
    provider = AppleOAuthProvider()

    token = pyjwt.encode(
        {
            "sub": "user",
            "iss": "https://appleid.apple.com",
            "aud": "com.example.app.signin",
            "email": "x@example.com",
            "exp": int(time.time()) + 3600,
        },
        signing_key,
        algorithm="RS256",
    )

    with (
        override_settings(APPLE_CLIENT_ID="com.example.app.signin"),
        patch("jwt.PyJWKClient.get_signing_key_from_jwt", return_value=MagicMock(key=wrong_public_key)),
    ):
        result = provider.verify_id_token(token)

    assert result is None


def test_property_6_fail_closed_unknown_kid():
    """Feature: z_aud_1, Property 6: kid inconnu (JWKS ne peut résoudre la clé) → refus."""
    provider = AppleOAuthProvider()
    with patch(
        "jwt.PyJWKClient.get_signing_key_from_jwt",
        side_effect=pyjwt.PyJWKClientError("Unable to find a signing key that matches"),
    ):
        assert provider.verify_id_token("token.with.unknown.kid") is None


def test_property_6_fail_closed_jwks_unreachable():
    """Feature: z_aud_1, Property 6: JWKS injoignable (timeout/5xx) → refus, jamais de skip de signature."""
    import requests

    provider = AppleOAuthProvider()
    with patch("jwt.PyJWKClient.get_signing_key_from_jwt", side_effect=requests.exceptions.ConnectTimeout()):
        assert provider.verify_id_token("any.token.here") is None


# ===========================================================================
# Property 7: Normalisation du dict utilisateur Apple
# ===========================================================================


@hyp_settings(max_examples=100, deadline=None)
@given(
    sub=st.text(min_size=1, max_size=50),
    email_local=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20),
    use_relay=st.booleans(),
    email_verified_raw=st.sampled_from(["true", "false", "True", "False", True, False]),
)
def test_property_7_normalized_user_dict_shape(sub, email_local, use_relay, email_verified_raw):
    """Feature: z_aud_1, Property 7: Normalisation du dict utilisateur Apple."""
    domain = "privaterelay.appleid.com" if use_relay else "example.com"
    email = f"{email_local}@{domain}"
    provider = AppleOAuthProvider()

    result = provider._normalize({"sub": sub, "email": email, "email_verified": email_verified_raw})

    assert set(result.keys()) == {
        "provider_user_id",
        "email",
        "email_verified",
        "first_name",
        "last_name",
        "avatar_url",
    }
    assert result["provider_user_id"] == sub
    assert result["email"] == email
    assert isinstance(result["email_verified"], bool)
    if isinstance(email_verified_raw, str):
        assert result["email_verified"] == (email_verified_raw.strip().lower() == "true")
    else:
        assert result["email_verified"] == bool(email_verified_raw)


def test_property_7_missing_email_verified_defaults_false():
    """Feature: z_aud_1, Property 7: email_verified absent → False (fail-closed)."""
    provider = AppleOAuthProvider()
    result = provider._normalize({"sub": "abc", "email": "x@example.com"})
    assert result["email_verified"] is False


# ===========================================================================
# Property 8: Le payload de première autorisation est optionnel
# ===========================================================================


@pytest.mark.django_db
@hyp_settings(max_examples=50, deadline=None, suppress_health_check=[])
@given(
    first_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=30),
    last_name=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=30),
    include_payload=st.booleans(),
)
def test_property_8_first_auth_user_payload_optional(first_name, last_name, include_payload):
    """Feature: z_aud_1, Property 8: Le payload de première autorisation est optionnel.

    Présence de `user` → first_name/last_name peuplés ; absence → noms vides, authentification
    aboutit dans les deux cas (jamais d'échec dû à l'absence du payload).
    """
    from rest_framework.test import APIRequestFactory
    from tenxyte.models import Application
    from tenxyte.views.social_auth_views import SocialAuthView

    app, _ = Application.create_application(name=f"PropTest8-{first_name[:5]}")
    body = {"id_token": "valid_apple_id_token"}
    if include_payload:
        body["user"] = {"name": {"firstName": first_name, "lastName": last_name}}

    apple_claims = {
        "provider_user_id": f"apple_prop8_{hash((first_name, last_name, include_payload)) & 0xFFFFFFF}",
        "email": None,
        "email_verified": False,
        "first_name": "",
        "last_name": "",
        "avatar_url": "",
    }

    factory = APIRequestFactory()
    with (
        patch("rest_framework.throttling.SimpleRateThrottle.allow_request", return_value=True),
        patch(
            "tenxyte.services.social_auth_service.AppleOAuthProvider.verify_id_token", return_value=dict(apple_claims)
        ),
    ):
        req = factory.post("/social/apple/", body, format="json")
        req.application = app
        resp = SocialAuthView.as_view()(req, provider="apple")

    assert resp.status_code == 200
    if include_payload:
        assert resp.data["user"]["first_name"] == first_name
        assert resp.data["user"]["last_name"] == last_name
    else:
        assert resp.data["user"]["first_name"] == ""
        assert resp.data["user"]["last_name"] == ""
