# Tenxyte Agnostic Architecture Changes

## Architecture Overview

# Views (Django/DRF) → Core Services → Django Adapters → Django Models
┌─────────────────┐    ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│  RegisterView   │───→│ Core JWT    │───→│ DjangoUserRepo   │───→│ Django ORM  │
│  (APIView)      │    │ TOTPService │    │ DjangoCacheSvc   │    │ Models      │
└─────────────────┘    └─────────────┘    └──────────────────┘    └─────────────┘

## Phase 3.1: Auth Views Refactoring (auth_views.py)

### Date: 2024-03-10

### Views Refactored

| View | Legacy | New Implementation |
|------|--------|-------------------|
| **RegisterView** | `AuthService.register_user()` | `register_user_with_core()` + `DjangoUserRepository` |
| **LoginEmailView** | `AuthService.authenticate_by_email()` | `authenticate_by_email_with_core()` + `JWTService` |
| **LoginPhoneView** | `AuthService.authenticate_by_phone()` | `authenticate_by_phone_with_core()` + `JWTService` |
| **RefreshTokenView** | `AuthService.refresh_access_token()` | `JWTService.refresh_tokens()` |
| **LogoutView** | `AuthService.logout()` | `JWTService.blacklist_token()` |
| **LogoutAllView** | `AuthService.logout_all_devices()` | `JWTService.blacklist_token()` |

### Helper Functions Added

```python
def register_user_with_core(**kwargs):
    """Register user using DjangoUserRepository (Core)."""
    
def authenticate_by_email_with_core(email, password, ...):
    """Email auth using Core JWT + UserRepo."""
    
def authenticate_by_phone_with_core(country_code, phone_number, ...):
    """Phone auth using Core JWT + UserRepo."""
```

### Core Services Used

| Service | Purpose |
|---------|---------|
| `JWTService` | Token generation, refresh, blacklisting |
| `TOTPService` | 2FA verification with replay protection |
| `DjangoUserRepository` | User CRUD, password management |
| `DjangoCacheService` | Token blacklist storage |

### Backward Compatibility

- Same endpoints: `/auth/register/`, `/auth/login/email/`, etc.
- Same request/response payloads
- Same error codes and HTTP status codes
- Legacy backup: `auth_views_legacy.py`

### Files Modified

- `src/tenxyte/views/auth_views.py` - Refactored to use Core
- `src/tenxyte/views/auth_views_legacy.py` - Backup of original

## Next Steps

- [x] `user_views.py` - User CRUD, profile management
- [x] `password_views.py` - Password reset/change
- [x] `twofa_views.py` - TOTP setup, backup codes
- [x] `webauthn_views.py` - Passkeys registration/auth
- [x] `magic_link_views.py` - Magic link flows

---

## Phase 3.3: Deprecation Warnings

### Date: 2024-03-10

The following Django-specific services now emit `DeprecationWarning` on instantiation:

| Service | Replacement |
|---------|-------------|
| `tenxyte.services.jwt_service.JWTService` | `tenxyte.core.JWTService` |
| `tenxyte.services.auth_service.AuthService` | `tenxyte.core` services + adapters |
| `tenxyte.services.totp_service.TOTPService` | `tenxyte.core.TOTPService` |
| `tenxyte.services.webauthn_service.WebAuthnService` | `tenxyte.core.WebAuthnService` |
| `tenxyte.services.magic_link_service.MagicLinkService` | `tenxyte.core.MagicLinkService` |
| `tenxyte.services.email_service.EmailService` | `tenxyte.adapters.django.email_service.DjangoEmailService` |

### Example Warning
```python
import warnings
warnings.warn(
    "tenxyte.services.jwt_service.JWTService is deprecated. "
    "Use tenxyte.core.JWTService with Django adapters instead.",
    DeprecationWarning,
    stacklevel=2
)
```

### Files Modified
- `src/tenxyte/services/jwt_service.py`
- `src/tenxyte/services/auth_service.py`
- `src/tenxyte/services/totp_service.py`
- `src/tenxyte/services/webauthn_service.py`
- `src/tenxyte/services/magic_link_service.py`
- `src/tenxyte/services/email_service.py`



┌─────────────────────────┐    ┌──────────────────┐    ┌─────────────┐
│ TwoFactorSetupView      │───→│ Core TOTPService │───→│ Django ORM │
│ TwoFactorConfirmView    │    │ (framework-      │    │ Models      │
│ TwoFactorDisableView    │    │  agnostic)       │    └─────────────┘
│ TwoFactorBackupCodesView│    └──────────────────┘
└─────────────────────────┘           ↓
                            ┌──────────────────┐
                            │ DjangoUserRepo   │
                            │ (adapter)        │
                            └──────────────────┘









┌─────────────────────────┐    ┌─────────────────────┐    ┌─────────────┐
│ WebAuthnRegisterBegin   │───→│ Core WebAuthnService│───→│ Django ORM │
│ WebAuthnRegisterComplete│    │ (framework-agnostic) │    │ Models      │
│ WebAuthnAuthenticateBegin│   └─────────────────────┘    └─────────────┘
│ WebAuthnAuthenticateComplete│         ↓
│ WebAuthnCredentialList   │    ┌─────────────────────┐
│ WebAuthnCredentialDelete │    │ DjangoWebAuthnStorage│
└─────────────────────────┘    │ DjangoUserRepo       │
                               └─────────────────────┘






┌─────────────────────────┐    ┌─────────────────────┐    ┌─────────────┐
│ MagicLinkRequestView    │───→│ Core MagicLinkService│───→│ Django ORM │
│ MagicLinkVerifyView     │    │ (framework-agnostic) │    │ Models      │
└─────────────────────────┘    └─────────────────────┘    └─────────────┘
                                        ↓
                               ┌─────────────────────┐
                               │ DjangoCacheService   │
                               │ DjangoUserRepo       │
                               │ DjangoEmailService   │
                               └─────────────────────┘




┌─────────────────────────┐    ┌─────────────────────┐    ┌─────────────┐
│ Django Views (DRF)      │───→│ Core Services       │───→│ Django ORM  │
│ (Facades - 28 vues)     │    │ (Framework-agnostic)│    │ Models      │
└─────────────────────────┘    └─────────────────────┘    └─────────────┘
                                          ↓
                                 ┌─────────────────────┐
                                 │ Django Adapters     │
                                 │ - UserRepository    │
                                 │ - CacheService      │
                                 │ - EmailService      │
                                 │ - WebAuthnStorage   │
                                 └─────────────────────┘