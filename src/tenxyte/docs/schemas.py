"""
DRF Spectacular Documentation Schemas and Patterns

Reusable components for OpenAPI documentation across all Tenxyte views.
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

# =============================================================================
# STANDARD RESPONSES
# =============================================================================

STANDARD_ERROR_RESPONSES = {
    400: OpenApiTypes.OBJECT,
    401: OpenApiTypes.OBJECT,
    403: OpenApiTypes.OBJECT,
    404: OpenApiTypes.OBJECT,
    409: OpenApiTypes.OBJECT,
    423: OpenApiTypes.OBJECT,
    429: OpenApiTypes.OBJECT,
    500: OpenApiTypes.OBJECT,
}

SUCCESS_RESPONSES = {
    200: OpenApiTypes.OBJECT,
    201: OpenApiTypes.OBJECT,
    204: OpenApiTypes.NONE,
}

# =============================================================================
# STANDARD PARAMETERS
# =============================================================================

ORG_HEADER = OpenApiParameter(
    name="X-Org-Slug",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.HEADER,
    description="Organization slug for multi-tenant endpoints",
    required=False,
    examples={"acme": {"value": "acme-corp"}, "regional": {"value": "acme-france"}, "personal": {"value": "john-doe"}},
)

PAGINATION_PARAMS = [
    OpenApiParameter(
        name="page",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Page number (default: 1)",
        required=False,
    ),
    OpenApiParameter(
        name="page_size",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Items per page (max: 100, default: 20)",
        required=False,
    ),
]

SEARCH_PARAMS = [
    OpenApiParameter(
        name="search",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Search in name and code fields",
        required=False,
    ),
]

ORDERING_PARAMS = [
    OpenApiParameter(
        name="ordering",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Ordering field (prefix - for DESC)",
        required=False,
        examples={"name_asc": {"value": "name"}, "name_desc": {"value": "-name"}, "created": {"value": "-created_at"}},
    ),
]

# =============================================================================
# STANDARD EXAMPLES
# =============================================================================

LOGIN_SUCCESS_EXAMPLE = OpenApiExample(
    name="login_success",
    summary="Successful login with JWT tokens",
    value={
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "user": {
            "id": 42,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "is_active": True,
            "date_joined": "2024-01-15T10:30:00Z",
        },
    },
)

LOGIN_RATE_LIMITED_EXAMPLE = OpenApiExample(
    name="login_rate_limited",
    summary="Rate limited login attempt",
    value={"error": "Too many login attempts", "details": "Please try again later", "retry_after": 300},
)

VALIDATION_ERROR_EXAMPLE = OpenApiExample(
    name="validation_error",
    summary="Validation error example",
    value={
        "error": "Validation error",
        "details": {
            "email": ["Enter a valid email address."],
            "password": ["Password must be at least 8 characters long."],
        },
    },
)

UNAUTHORIZED_EXAMPLE = OpenApiExample(
    name="unauthorized",
    summary="Unauthorized access",
    value={"error": "Authentication required", "details": "Please provide valid authentication credentials"},
)

FORBIDDEN_EXAMPLE = OpenApiExample(
    name="forbidden",
    summary="Permission denied",
    value={"error": "Permission denied", "details": "You do not have permission to perform this action"},
)

SESSION_LIMIT_EXAMPLE = OpenApiExample(
    name="session_limit_exceeded",
    summary="Session limit exceeded",
    value={
        "error": "Session limit exceeded",
        "details": "Maximum concurrent sessions (1) already reached. Please logout from other devices.",
        "code": "SESSION_LIMIT_EXCEEDED",
    },
)

DEVICE_LIMIT_EXAMPLE = OpenApiExample(
    name="device_limit_exceeded",
    summary="Device limit exceeded",
    value={
        "error": "Device limit exceeded",
        "details": "Maximum registered devices (1) already reached. Please remove a device first.",
        "code": "DEVICE_LIMIT_EXCEEDED",
    },
)

ACCOUNT_LOCKED_EXAMPLE = OpenApiExample(
    name="account_locked",
    summary="Account locked",
    value={
        "error": "Account locked",
        "details": "Account has been locked due to too many failed login attempts. Please try again later.",
        "retry_after": 1800,
    },
)

BREACH_PASSWORD_EXAMPLE = OpenApiExample(
    name="breach_password",
    summary="Password breach detected",
    value={
        "error": "Password breach detected",
        "details": "This password has been found in known data breaches. Please choose a different password.",
        "code": "PASSWORD_BREACH",
    },
)

# =============================================================================
# TAGS
# =============================================================================

TAGS = {
    "auth": "Authentication",
    "user": "User Management",
    "rbac": "RBAC (Roles & Permissions)",
    "organizations": "Organizations",
    "security": "Security & Audit",
    "applications": "Applications",
    "otp": "OTP Verification",
    "twofa": "Two-Factor Authentication",
    "password": "Password Management",
    "magic_link": "Magic Links",
    "social": "Social Authentication",
    "webauthn": "WebAuthn / Passkeys",
    "gdpr": "GDPR & Privacy",
    "dashboard": "Dashboard",
}

# =============================================================================
# DECORATOR HELPERS
# =============================================================================


def standard_extend_schema(
    tags=None,
    summary=None,
    description=None,
    request=None,
    responses=None,
    parameters=None,
    examples=None,
    auth=None,
    deprecated=False,
    operation_id=None,
):
    """
    Standard extend_schema with common defaults.
    """
    if responses is None:
        responses = SUCCESS_RESPONSES.copy()
        responses.update(STANDARD_ERROR_RESPONSES)

    if parameters is None:
        parameters = []

    return extend_schema(
        tags=tags,
        summary=summary,
        description=description,
        request=request,
        responses=responses,
        parameters=parameters,
        examples=examples,
        auth=auth,
        deprecated=deprecated,
        operation_id=operation_id,
    )


def org_extend_schema(**kwargs):
    """
    Extend schema with organization header added automatically.
    """
    parameters = kwargs.get("parameters", [])
    parameters.append(ORG_HEADER)
    kwargs["parameters"] = parameters
    return standard_extend_schema(**kwargs)


def paginated_extend_schema(**kwargs):
    """
    Extend schema with pagination parameters added automatically.
    """
    parameters = kwargs.get("parameters", [])
    parameters.extend(PAGINATION_PARAMS)
    kwargs["parameters"] = parameters
    return standard_extend_schema(**kwargs)


def searchable_extend_schema(**kwargs):
    """
    Extend schema with search parameters added automatically.
    """
    parameters = kwargs.get("parameters", [])
    parameters.extend(SEARCH_PARAMS)
    kwargs["parameters"] = parameters
    return standard_extend_schema(**kwargs)


# =============================================================================
# CUSTOM SCHEMAS
# =============================================================================

JWT_TOKEN_SCHEMA = {
    "type": "object",
    "properties": {
        "access": {"type": "string", "description": "JWT access token (short-lived)"},
        "refresh": {"type": "string", "description": "JWT refresh token (long-lived)"},
        "user": {"$ref": "#/components/schemas/User"},
    },
    "required": ["access", "refresh", "user"],
}

OTP_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "description": "Success message"},
        "otp_id": {"type": "string", "description": "OTP verification ID (for verify endpoint)"},
        "expires_at": {"type": "string", "format": "date-time", "description": "OTP expiry time"},
    },
    "required": ["message"],
}

PAGINATED_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer", "description": "Total number of items"},
        "next": {"type": "string", "nullable": True, "description": "URL of next page"},
        "previous": {"type": "string", "nullable": True, "description": "URL of previous page"},
        "results": {"type": "array", "items": {}, "description": "Page results"},
    },
    "required": ["count", "next", "previous", "results"],
}

ERROR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "error": {"type": "string", "description": "Error type/message"},
        "details": {"oneOf": [{"type": "string"}, {"type": "object"}], "description": "Detailed error information"},
        "code": {"type": "string", "description": "Machine-readable error code"},
        "retry_after": {
            "type": "integer",
            "description": "Seconds to wait before retry (for rate limiting)",
            "nullable": True,
        },
    },
    "required": ["error"],
}


# =============================================================================
# REUSABLE EXAMPLES
# =============================================================================

# Authentication Examples
LOGIN_SUCCESS_EXAMPLE = OpenApiExample(
    name="login_success",
    summary="Login successful",
    description="Successful authentication with JWT tokens and user data",
    value={
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "user": {
            "id": 12345,
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "is_active": True,
            "is_verified": True,
            "last_login": "2024-01-20T14:22:00Z",
        },
    },
)

LOGIN_RATE_LIMITED_EXAMPLE = OpenApiExample(
    name="login_rate_limited",
    summary="Login rate limited",
    description="Too many login attempts - rate limiting active",
    value={
        "error": "Too many login attempts",
        "code": "RATE_LIMITED",
        "retry_after": 300,
        "details": "Please wait 5 minutes before trying again",
    },
)

VALIDATION_ERROR_EXAMPLE = OpenApiExample(
    name="validation_error",
    summary="Validation error",
    description="Request data validation failed",
    value={
        "error": "Validation failed",
        "code": "VALIDATION_ERROR",
        "details": {"email": ["Enter a valid email address."], "password": ["Password must be at least 8 characters."]},
    },
)

NOT_FOUND_ERROR_EXAMPLE = OpenApiExample(
    name="not_found",
    summary="Resource not found",
    description="Requested resource does not exist",
    value={"error": "Resource not found", "code": "NOT_FOUND", "details": "User with ID 99999 does not exist"},
)

PERMISSION_DENIED_EXAMPLE = OpenApiExample(
    name="permission_denied",
    summary="Permission denied",
    description="User lacks required permission",
    value={
        "error": "Permission denied",
        "code": "PERMISSION_DENIED",
        "details": "You need org.members.manage permission to perform this action",
    },
)

# Organization Examples
ORG_CONTEXT_EXAMPLE = OpenApiExample(
    name="org_context",
    summary="Organization context",
    description="Request with organization context",
    value={"X-Org-Slug": "acme-corp"},
)

# Multi-tenant Examples
MULTI_TENANT_SUCCESS_EXAMPLE = OpenApiExample(
    name="multi_tenant_success",
    summary="Multi-tenant response",
    description="Response with organization-specific data",
    value={
        "id": 123,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "organization": {"id": 456, "slug": "acme-corp", "name": "Acme Corporation", "role": "admin"},
    },
)

# Security Examples
SECURITY_HEADERS_EXAMPLE = OpenApiExample(
    name="security_headers",
    summary="Security response headers",
    description="Response with security headers",
    value={
        "X-RateLimit-Limit": "1000",
        "X-RateLimit-Remaining": "999",
        "X-RateLimit-Reset": "1642694400",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
    },
)

# File Upload Examples
FILE_UPLOAD_SUCCESS_EXAMPLE = OpenApiExample(
    name="file_upload_success",
    summary="File upload successful",
    description="File uploaded and processed successfully",
    value={
        "message": "File uploaded successfully",
        "file_url": "https://cdn.example.com/uploads/avatar_12345.jpg",
        "file_size": 1024000,
        "mime_type": "image/jpeg",
        "dimensions": {"width": 400, "height": 400},
    },
)

FILE_TOO_LARGE_EXAMPLE = OpenApiExample(
    name="file_too_large",
    summary="File too large",
    description="File exceeds maximum size limit",
    value={
        "error": "File size exceeds maximum limit",
        "code": "FILE_TOO_LARGE",
        "details": "Maximum file size is 5MB",
        "max_size": "5MB",
    },
)

# GDPR Examples
GDPR_DELETION_CONFIRMED_EXAMPLE = OpenApiExample(
    name="gdpr_deletion_confirmed",
    summary="GDPR deletion confirmed",
    description="Account deletion request confirmed via email",
    value={
        "message": "Account deletion confirmed",
        "deletion_confirmed": True,
        "grace_period_ends": "2024-02-20T10:30:00Z",
        "cancellation_instructions": "Use the cancellation link sent to your email within 30 days",
    },
)

# Pagination Examples
PAGINATED_RESPONSE_EXAMPLE = OpenApiExample(
    name="paginated_response",
    summary="Paginated response",
    description="Response with pagination metadata",
    value={
        "count": 150,
        "next": "https://api.example.com/users/?page=2",
        "previous": None,
        "results": [
            {"id": 1, "email": "user1@example.com", "first_name": "Alice"},
            {"id": 2, "email": "user2@example.com", "first_name": "Bob"},
        ],
    },
)

# Collections of examples for easy import
AUTH_EXAMPLES = [LOGIN_SUCCESS_EXAMPLE, LOGIN_RATE_LIMITED_EXAMPLE, VALIDATION_ERROR_EXAMPLE]

ERROR_EXAMPLES = [
    VALIDATION_ERROR_EXAMPLE,
    NOT_FOUND_ERROR_EXAMPLE,
    PERMISSION_DENIED_EXAMPLE,
    LOGIN_RATE_LIMITED_EXAMPLE,
]

SUCCESS_EXAMPLES = [
    LOGIN_SUCCESS_EXAMPLE,
    MULTI_TENANT_SUCCESS_EXAMPLE,
    FILE_UPLOAD_SUCCESS_EXAMPLE,
    PAGINATED_RESPONSE_EXAMPLE,
]

SECURITY_EXAMPLES = [SECURITY_HEADERS_EXAMPLE, LOGIN_RATE_LIMITED_EXAMPLE, GDPR_DELETION_CONFIRMED_EXAMPLE]
