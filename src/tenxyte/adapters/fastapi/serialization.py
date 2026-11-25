"""
Shared `User` → response-dict serialization for the Reference_Stack (spec z_aud_3) — used by every
router that returns a full user object in its response (`routers/auth.py`'s login/register/me,
and Wave C's `routers/magic_link.py`/`routers/login_otp.py`), so the shape stays identical across
every path that issues one, the same way the Django_Adapter's single `UserSerializer` backs all of
its equivalents.
"""

from __future__ import annotations

from tenxyte.ports.repositories import User


def serialize_user(user: User) -> dict:
    """Same field names as the Django_Adapter's `UserSerializer` — several (username, phone,
    avatar, bio, timezone, language, custom_fields, roles, permissions) have no Reference_Stack
    storage yet and are stubbed to their empty value rather than omitted, so the response shape
    matches even where the content doesn't yet."""
    return {
        "id": user.id,
        "email": user.email,
        "username": None,
        "phone": None,
        "avatar": None,
        "bio": "",
        "timezone": "",
        "language": "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "is_active": user.is_active,
        "is_email_verified": user.email_verified,
        "is_phone_verified": False,
        "is_2fa_enabled": user.mfa_type.value != "none",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "custom_fields": {},
        "preferences": {"email_notifications": True, "sms_notifications": False, "marketing_emails": False},
        "roles": [],
        "permissions": [],
    }
