"""
Password strength validation for the FastAPI_Adapter (spec z_aud_3, Wave B) — a framework-agnostic
reimplementation of `tenxyte.validators.PasswordValidator`, not a reuse of it: that module does
`from .conf import auth_settings`, which imports `django.conf.settings` at module load time,
making it unimportable from a Django-less FastAPI process. Driven by `core/settings.py`'s
`password_min_length`/`password_require_*` properties instead.

Deliberately not byte-identical to the Django_Adapter's error strings: Django's validator emits
French sentences (some accented, some not — an existing inconsistency, not a contract to
replicate) for what is everywhere else in this codebase an English-language error surface
(`register`'s "Invalid email or password", etc.). The *shape* (score/strength/is_valid/errors/
requirements) matches; the *wording* is this adapter's own. Also not replicated: Django's
common-password dictionary check and predictable-sequence detection — dictionary-based checks are
a content/data concern (the word list itself), not a structural contract worth porting without a
shared source list, and are one of the few genuinely optional layers on top of the structural
rules this module does enforce.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tenxyte.core.settings import Settings

_SPECIAL_CHARS_PATTERN = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\/;'`~]")


@dataclass
class PasswordValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    score: int = 0
    strength: str = "weak"


def get_requirements(settings: Settings) -> list[str]:
    requirements = [f"At least {settings.password_min_length} characters"]
    if settings.password_require_uppercase:
        requirements.append("At least one uppercase letter (A-Z)")
    if settings.password_require_lowercase:
        requirements.append("At least one lowercase letter (a-z)")
    if settings.password_require_digit:
        requirements.append("At least one digit (0-9)")
    if settings.password_require_special:
        requirements.append("At least one special character (!@#$%^&* etc.)")
    return requirements


def validate(password: str, settings: Settings) -> PasswordValidationResult:
    if not password:
        return PasswordValidationResult(is_valid=False, errors=["Password is required"], score=0, strength="weak")

    errors: list[str] = []
    max_length = 128

    if len(password) < settings.password_min_length:
        errors.append(f"Password must be at least {settings.password_min_length} characters")
    if len(password) > max_length:
        errors.append(f"Password must not exceed {max_length} characters")
    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if settings.password_require_lowercase and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if settings.password_require_digit and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    if settings.password_require_special and not _SPECIAL_CHARS_PATTERN.search(password):
        errors.append("Password must contain at least one special character")

    score = _score(password)
    strength = _strength_label(score)

    return PasswordValidationResult(is_valid=len(errors) == 0, errors=errors, score=score, strength=strength)


def _score(password: str) -> int:
    """0-100, informational only — not a pass/fail gate (errors is what gates `is_valid`)."""
    length_score = min(40, len(password) * 3)
    variety = sum(
        [
            any(c.isupper() for c in password),
            any(c.islower() for c in password),
            any(c.isdigit() for c in password),
            bool(_SPECIAL_CHARS_PATTERN.search(password)),
        ]
    )
    variety_score = variety * 15
    unique_ratio_score = int(20 * (len(set(password)) / max(1, len(password))))
    return min(100, length_score + variety_score + unique_ratio_score)


def _strength_label(score: int) -> str:
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "strong"
    if score >= 40:
        return "good"
    if score >= 20:
        return "fair"
    return "weak"
