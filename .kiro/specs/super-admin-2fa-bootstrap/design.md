# Super Admin 2FA Bootstrap Bugfix Design

## Overview

This design addresses the circular dependency bug where super admins cannot log in without 2FA enabled, but cannot enable 2FA without logging in first. The fix introduces a temporary restricted-scope JWT token (`2fa_setup_only`) that grants access exclusively to the 2FA setup and confirmation endpoints (`/2fa/setup/` and `/2fa/confirm/`). This token is issued during login when an admin user lacks 2FA, allowing them to complete the 2FA bootstrap process. Once 2FA is confirmed, the system issues a full-scope token, breaking the circular dependency while maintaining security.

The approach is minimal and surgical: it modifies the login flow to detect the bootstrap condition, introduces a new token scope with strict validation, and preserves all existing authentication behaviors for users with 2FA already enabled.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when an admin or super admin user attempts to log in without 2FA enabled
- **Property (P)**: The desired behavior when the bug condition holds - issue a restricted token allowing only 2FA setup/confirmation
- **Preservation**: All existing authentication behaviors must remain unchanged, including 2FA enforcement for admins with 2FA enabled, non-admin login without 2FA, and token refresh mechanics
- **LoginEmailView**: The Django REST Framework view in `src/tenxyte/views/auth_views.py` that handles email-based authentication
- **LoginPhoneView**: The Django REST Framework view in `src/tenxyte/views/auth_views.py` that handles phone-based authentication
- **TwoFactorSetupView**: The view in `src/tenxyte/views/twofa_views.py` that initializes 2FA configuration
- **TwoFactorConfirmView**: The view in `src/tenxyte/views/twofa_views.py` that confirms and activates 2FA
- **require_jwt decorator**: The authentication decorator in `src/tenxyte/decorators.py` that validates JWT tokens
- **JWTService**: The core token generation service in `src/tenxyte/core/jwt_service.py`
- **is_admin**: A user is considered admin if `user.is_superuser == True` or `user.is_staff == True`
- **Token scope**: A claim in the JWT payload that restricts which endpoints the token can access
- **2fa_setup_only**: The restricted token scope that permits access only to `/2fa/setup/` and `/2fa/confirm/`

## Bug Details

### Bug Condition

The bug manifests when an admin or super admin user attempts to log in without having 2FA enabled on their account. The `LoginEmailView` and `LoginPhoneView` functions detect that the user is an admin (`is_superuser` or `is_staff`) and that their MFA type is "none" (no 2FA configured), then immediately reject the login with a 403 error code `ADMIN_2FA_SETUP_REQUIRED`. However, the 2FA setup endpoints (`TwoFactorSetupView` and `TwoFactorConfirmView`) are protected by the `@require_jwt` decorator, which requires a valid authenticated token. This creates an impossible bootstrap scenario.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type LoginRequest
  OUTPUT: boolean
  
  RETURN (input.user.is_superuser = true OR input.user.is_staff = true)
         AND input.user.mfa_type = "none"
         AND input.attempting_login = true
         AND NOT has_valid_jwt_token(input)
END FUNCTION
```

### Examples

- **Super admin via createsuperuser**: An admin creates a super admin using `python manage.py createsuperuser`. The super admin attempts to log in with email and password. Expected: receive a restricted token to set up 2FA. Actual: receives 403 with `ADMIN_2FA_SETUP_REQUIRED` and cannot proceed.

- **Role elevation scenario**: A regular user with 2FA disabled is elevated to super_admin role via the admin panel. The user attempts to log in. Expected: receive a restricted token to set up 2FA. Actual: receives 403 with `ADMIN_2FA_SETUP_REQUIRED` and is locked out.

- **Staff user without 2FA**: A staff user (`is_staff=True`) with no 2FA configured attempts to log in. Expected: receive a restricted token to set up 2FA. Actual: receives 403 with `ADMIN_2FA_SETUP_REQUIRED`.

- **Edge case - Token expiration**: A super admin receives the restricted token but waits 16+ minutes before attempting to set up 2FA. Expected: the restricted token expires (15-minute limit) and the user must log in again to receive a fresh token.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Admin users with 2FA already enabled must continue to be required to provide a valid TOTP code during login
- Non-admin users (standard role) must continue to be able to log in without 2FA requirements
- Token refresh operations must continue to validate that admins have 2FA enabled
- The 2FA disable endpoint must continue to be restricted (admins cannot disable 2FA once enabled)
- Backup code authentication must continue to work for admins with 2FA enabled
- Session limit enforcement, device fingerprinting, and all other authentication security features must remain unchanged

**Scope:**
All inputs that do NOT involve admin users attempting to log in without 2FA should be completely unaffected by this fix. This includes:
- Regular users logging in without 2FA
- Admin users logging in with 2FA enabled (providing TOTP code)
- Token refresh operations for any user type
- Magic link authentication
- Social authentication flows
- OTP-based authentication

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Premature Login Rejection**: The login views (`LoginEmailView` and `LoginPhoneView`) perform an eager check at lines 796-800 and 962-966 that immediately returns a 403 error when an admin lacks 2FA, before considering whether a bootstrap flow is needed. The check occurs after successful password authentication but before any token is issued.

2. **No Bootstrap Token Mechanism**: The `JWTService.generate_access_token` method in `src/tenxyte/core/jwt_service.py` does not support restricted token scopes. The `extra_claims` parameter exists but there is no built-in concept of a "scope" claim that would restrict endpoint access.

3. **Decorator Does Not Validate Scope**: The `@require_jwt` decorator in `src/tenxyte/decorators.py` validates token presence and signature but does not check or enforce token scope restrictions. Even if a scope claim were added to the token, the decorator would not prevent access to restricted endpoints.

4. **No Endpoint Scope Enforcement**: The 2FA views (`TwoFactorSetupView`, `TwoFactorConfirmView`) and other protected endpoints have no mechanism to specify which token scopes are permitted. All views either require full authentication (`@require_jwt`) or allow anonymous access (`permission_classes = [AllowAny]`).

## Correctness Properties

Property 1: Bug Condition - Bootstrap Token Issued for Admin Without 2FA

_For any_ login request where the user is an admin (is_superuser or is_staff) and the user does not have 2FA enabled (mfa_type is "none"), the fixed login function SHALL issue a restricted-scope JWT token with scope "2fa_setup_only", set requires_2fa_setup to true in the response, and set token expiration to 15 minutes (900 seconds).

**Validates: Requirements 2.1, 2.2, 2.5**

Property 2: Preservation - Existing Authentication Flows Unchanged

_For any_ login request where the user is NOT in the bug condition (either non-admin user, or admin with 2FA already enabled), the fixed login function SHALL produce exactly the same result as the original function, preserving all existing authentication behaviors including 2FA code validation, session limits, device fingerprinting, and token lifetimes.

**Validates: Requirements 3.1, 3.2, 3.4, 3.5, 3.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/tenxyte/views/auth_views.py`

**Functions**: `LoginEmailView.post()` (line 754) and `LoginPhoneView.post()` (line 845)

**Specific Changes**:
1. **Replace 403 Rejection with Bootstrap Token Issuance**: At lines 796-800 (LoginEmailView) and 962-966 (LoginPhoneView), replace the immediate 403 error response with logic that generates a restricted-scope token with `scope: "2fa_setup_only"` and lifetime of 15 minutes (900 seconds).

2. **Add Scope to Extra Claims**: When calling the JWT generation logic for the bootstrap case, pass `extra_claims={"scope": "2fa_setup_only"}` to `JWTService.generate_token_pair` or equivalent method.

3. **Include Bootstrap Metadata in Response**: Return a 200 response with the token, and add the flag `requires_2fa_setup: true` to signal to the client that this is a restricted token requiring immediate 2FA setup.

4. **Set Short Token Lifetime**: Override the default access token lifetime to 900 seconds (15 minutes) for the bootstrap token by passing a custom `expires_at` or modifying the token generation call.

**File**: `src/tenxyte/decorators.py`

**Function**: `require_jwt` (decorator)

**Specific Changes**:
1. **Extract Scope Claim**: After validating the JWT token, extract the `scope` claim from the decoded token payload (if present).

2. **Store Scope on Request Object**: Attach the scope to `request.jwt_scope` or similar attribute so views can access it.

3. **Add Scope Validation Hook**: Provide a mechanism for views to declare required scopes (e.g., via decorator parameter or view attribute) and reject tokens with insufficient scope.

**File**: `src/tenxyte/views/twofa_views.py`

**Functions**: `TwoFactorSetupView.post()` (line 110) and `TwoFactorConfirmView.post()` (line 182)

**Specific Changes**:
1. **Allow 2fa_setup_only Scope**: Modify the `@require_jwt` decorator usage to accept tokens with scope "2fa_setup_only" in addition to full-scope tokens for these two endpoints only.

2. **Reject Bootstrap Tokens Elsewhere**: Ensure that all other endpoints (e.g., `TwoFactorDisableView`, user management endpoints) reject tokens with scope "2fa_setup_only".

3. **Issue Full Token After Confirmation**: In `TwoFactorConfirmView.post()`, after successfully enabling 2FA (line ~250), generate and return a new full-scope token pair so the user can proceed with normal authenticated operations without re-logging in.

**File**: `src/tenxyte/core/jwt_service.py`

**Function**: `JWTService.generate_access_token()` (line ~270)

**Specific Changes**:
1. **Support Custom Expiration**: Add an optional parameter `custom_lifetime: Optional[timedelta] = None` to allow overriding the default access token lifetime for special cases like the bootstrap token.

2. **Document Scope Claim**: Update docstring and comments to clarify that the `extra_claims` parameter can include a "scope" claim for restricting token access.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write integration tests that simulate the bootstrap scenario on the UNFIXED codebase. Attempt to create a super admin via `createsuperuser`, log in with valid credentials, and observe the 403 error. Then attempt to call `/2fa/setup/` without any token and observe the 401 error. Document the exact error responses and status codes.

**Test Cases**:
1. **Superuser Login Without 2FA**: Create a superuser with `createsuperuser`, attempt POST to `/api/v1/auth/login/email/` with valid email and password. Assert response is 403 with code `ADMIN_2FA_SETUP_REQUIRED`. (will fail on unfixed code - this is the bug)

2. **Staff User Login Without 2FA**: Create a staff user (`is_staff=True`, `is_2fa_enabled=False`), attempt login. Assert response is 403 with code `ADMIN_2FA_SETUP_REQUIRED`. (will fail on unfixed code)

3. **Attempt 2FA Setup Without Token**: Without any authentication, attempt POST to `/api/v1/auth/2fa/setup/`. Assert response is 401 Unauthorized with no access granted. (will fail on unfixed code)

4. **Role Elevation Scenario**: Create a regular user, elevate to super_admin role, attempt login. Assert response is 403 with code `ADMIN_2FA_SETUP_REQUIRED`. (will fail on unfixed code)

**Expected Counterexamples**:
- 403 errors when admins without 2FA attempt login (demonstrates the rejection)
- 401 errors when attempting to access 2FA setup endpoints without authentication (demonstrates the circular dependency)
- Possible causes: eager rejection in login views (lines 796-800, 962-966), no bootstrap token mechanism, lack of scope enforcement

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := login_fixed(input)
  ASSERT result.success = true
         AND result.token_scope = "2fa_setup_only"
         AND result.requires_2fa_setup = true
         AND result.access_token IS NOT NULL
         AND result.token_lifetime <= 900
         AND can_call_endpoint(result.access_token, "/2fa/setup/") = true
         AND can_call_endpoint(result.access_token, "/2fa/confirm/") = true
         AND can_call_endpoint(result.access_token, "/2fa/status/") = false
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT login_original(input) = login_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain (various user roles, 2FA states, authentication methods)
- It catches edge cases that manual unit tests might miss (e.g., token refresh with expired 2FA, backup codes, magic links)
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for non-admin logins, admin logins with 2FA enabled, token refresh, and other authentication flows. Capture expected responses, status codes, and token structures. Then write property-based tests that generate diverse inputs and assert that the FIXED code produces identical outputs for all non-bootstrap scenarios.

**Test Cases**:
1. **Regular User Login Preservation**: Create regular users (non-admin) with various 2FA states (enabled, disabled), log in on unfixed code and capture responses. Run the same tests on fixed code and assert identical responses (status codes, token structure, fields).

2. **Admin with 2FA Enabled Preservation**: Create admin users with 2FA enabled, log in with valid TOTP codes on unfixed code. Run the same tests on fixed code and assert that 2FA validation still occurs, tokens are full-scope, and no `requires_2fa_setup` flag appears.

3. **Token Refresh Preservation**: Create various users, log them in, use their refresh tokens to get new access tokens on unfixed code. Repeat on fixed code and assert identical token refresh behavior (same claims, same lifetime, same validation).

4. **Magic Link and Social Auth Preservation**: Test magic link authentication and social auth flows on unfixed code. Repeat on fixed code and assert no changes to these flows.

5. **2FA Disable Restriction Preservation**: Verify that admins with 2FA enabled cannot disable 2FA on both unfixed and fixed code (ensure the restriction remains).

6. **Backup Code Authentication Preservation**: Create admin with 2FA enabled and backup codes, authenticate with a backup code on unfixed code. Repeat on fixed code and assert identical behavior (code marked as used, full-scope token issued).

### Unit Tests

- Test login view response when admin has no 2FA (should return 200 with restricted token and `requires_2fa_setup: true`)
- Test that restricted token includes `scope: "2fa_setup_only"` claim
- Test that restricted token has 15-minute expiration (900 seconds)
- Test that `/2fa/setup/` endpoint accepts restricted token
- Test that `/2fa/confirm/` endpoint accepts restricted token
- Test that other endpoints (e.g., `/2fa/status/`, user endpoints) reject restricted token with 403
- Test that after successful 2FA confirmation, a full-scope token is returned
- Test edge case: restricted token expiration (attempt to use after 15 minutes)
- Test edge case: restricted token used for unauthorized endpoint (should get 403 INSUFFICIENT_SCOPE)

### Property-Based Tests

- Generate random user configurations (admin/non-admin, 2FA enabled/disabled) and verify that only admin users without 2FA receive the restricted token
- Generate random login attempts with valid credentials and verify that token scopes are correctly assigned based on user state
- Generate random token lifetimes and verify that bootstrap tokens never exceed 15 minutes while full tokens use the configured lifetime
- Generate random endpoint access attempts with various token scopes and verify that scope enforcement is consistent across all endpoints
- Generate random sequences of authentication events (login → setup → confirm) and verify that the token transitions from restricted to full scope correctly

### Integration Tests

- Test full bootstrap flow: create super admin via `createsuperuser` → log in → receive restricted token → call `/2fa/setup/` → receive QR code → call `/2fa/confirm/` with valid TOTP code → receive full-scope token → access protected endpoints successfully
- Test bootstrap flow timeout: create super admin → log in → receive restricted token → wait 16 minutes → attempt `/2fa/setup/` (should fail with 401 expired token) → log in again → complete setup
- Test that after completing 2FA setup, subsequent logins require TOTP code (no more bootstrap tokens)
- Test role elevation: create regular user → elevate to admin → log in → complete bootstrap flow → verify 2FA is enforced on next login
- Test that restricted tokens cannot be refreshed (refresh endpoint should reject `2fa_setup_only` scope)
- Test mixed authentication methods: verify bootstrap flow works for both email and phone login paths
