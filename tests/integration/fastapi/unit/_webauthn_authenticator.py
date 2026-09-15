"""
A minimal, real FIDO2 "virtual authenticator" (spec z_aud_3, Wave G, task 12.1) — genuine ECDSA
P-256 key generation, CBOR-encoded attestation/authenticator data, and real signatures, so
`test_webauthn_router.py` exercises the actual `webauthn` (py_webauthn) verification functions
end-to-end. No mocks: `webauthn.verify_registration_response`/`verify_authentication_response`
run for real against credentials this module produces, the same way they'd run against a real
browser/authenticator's output. Not a test double for py_webauthn itself — a real, if synthetic,
authenticator implementing just enough of the FIDO2 wire format (`fmt="none"` attestation, ES256/
P-256 only) to be a valid verification target.
"""

from __future__ import annotations

import hashlib
import json
import secrets

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import bytes_to_base64url


class VirtualAuthenticator:
    """One simulated passkey — a real P-256 keypair plus a random 32-byte credential id."""

    def __init__(self) -> None:
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = secrets.token_bytes(32)

    def _cose_public_key(self) -> bytes:
        numbers = self.private_key.public_key().public_numbers()
        cose_key = {
            1: 2,  # kty: EC2
            3: -7,  # alg: ES256
            -1: 1,  # crv: P-256
            -2: numbers.x.to_bytes(32, "big"),
            -3: numbers.y.to_bytes(32, "big"),
        }
        return cbor2.dumps(cose_key)

    def _auth_data(self, rp_id: str, sign_count: int, *, attested: bool) -> bytes:
        rp_id_hash = hashlib.sha256(rp_id.encode()).digest()
        flags = 0b00000001  # UP (user present)
        body = b""
        if attested:
            flags |= 0b01000000  # AT (attested credential data included)
            aaguid = b"\x00" * 16
            cose_key = self._cose_public_key()
            body = aaguid + len(self.credential_id).to_bytes(2, "big") + self.credential_id + cose_key
        return rp_id_hash + bytes([flags]) + sign_count.to_bytes(4, "big") + body

    def registration_credential(self, *, challenge: bytes, rp_id: str, origin: str) -> dict:
        """A real `PublicKeyCredential` JSON dict for a `navigator.credentials.create()` call —
        `fmt="none"` attestation (no attestation statement to sign), matching how most real
        browsers respond by default."""
        client_data_json = json.dumps(
            {"type": "webauthn.create", "challenge": bytes_to_base64url(challenge), "origin": origin}
        ).encode()
        attestation_object = cbor2.dumps(
            {"fmt": "none", "attStmt": {}, "authData": self._auth_data(rp_id, 0, attested=True)}
        )
        return {
            "id": bytes_to_base64url(self.credential_id),
            "rawId": bytes_to_base64url(self.credential_id),
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data_json),
                "attestationObject": bytes_to_base64url(attestation_object),
            },
            "type": "public-key",
        }

    def authentication_credential(self, *, challenge: bytes, rp_id: str, origin: str, sign_count: int = 1) -> dict:
        """A real `PublicKeyCredential` JSON dict for a `navigator.credentials.get()` call — the
        `authenticatorData || SHA-256(clientDataJSON)` payload is genuinely ECDSA-signed with this
        authenticator's private key."""
        client_data_json = json.dumps(
            {"type": "webauthn.get", "challenge": bytes_to_base64url(challenge), "origin": origin}
        ).encode()
        auth_data = self._auth_data(rp_id, sign_count, attested=False)
        signed_payload = auth_data + hashlib.sha256(client_data_json).digest()
        signature = self.private_key.sign(signed_payload, ec.ECDSA(hashes.SHA256()))
        return {
            "id": bytes_to_base64url(self.credential_id),
            "rawId": bytes_to_base64url(self.credential_id),
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data_json),
                "authenticatorData": bytes_to_base64url(auth_data),
                "signature": bytes_to_base64url(signature),
            },
            "type": "public-key",
        }
