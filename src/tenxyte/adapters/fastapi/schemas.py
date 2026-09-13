"""
Pydantic request bodies for the Wave A auth router (spec z_aud_3, task 5.1) — response bodies are
deliberately plain `dict`s built by hand in `routers/auth.py`, not `response_model`s: the Django
contract's response shape genuinely varies by branch (bootstrap token vs restricted-scope token
vs normal success), and forcing all three through one Pydantic response model would either lose
fields or require a union type that adds no real validation value over just building the dict
that matches the branch actually taken.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Email-only for now — phone registration is deferred (see routers/auth.py's module
    docstring), so `email` is required here rather than optional-with-a-phone-alternative like
    the Django serializer's `validate()` cross-field rule."""

    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = ""
    last_name: str = ""
    login: bool = False


class LoginEmailRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str = ""


class RefreshTokenRequest(BaseModel):
    refresh_token: str = ""


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
