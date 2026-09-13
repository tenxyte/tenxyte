"""
Documented response-shape constants for Tenxyte's public endpoints (spec z_aud_3, task 3.2,
Property 2) — the single source of truth both the Django_Adapter's own snapshot tests
(`tests/integration/django/unit/test_endpoint_response_shape_snapshots.py`) and the Contract_Suite
(`tests/contract/`) assert against, so the two can never silently drift apart.
"""

REGISTER_REQUIRED_FIELDS = {"message", "user", "verification_required"}

REGISTER_USER_FIELDS = {
    "id",
    "email",
    "is_email_verified",
    "is_phone_verified",
    "is_2fa_enabled",
}

LOGIN_EMAIL_REQUIRED_FIELDS = {
    "access_token",
    "refresh_token",
    "token_type",
    "expires_in",
    "refresh_expires_in",
    "user",
    "requires_2fa",
    "session_id",
    "device_id",
}

LOGIN_PHONE_REQUIRED_FIELDS = {
    "access_token",
    "refresh_token",
    "token_type",
    "expires_in",
    "refresh_expires_in",
    "user",
    "requires_2fa",
    "session_id",
    "device_id",
}
