"""
Tenxyte - Query filters for list endpoints.

Provides reusable filter helpers that work with standard Django querysets.
Each filter function takes a queryset and request, and returns a filtered queryset.

Usage in views:
    from ..filters import apply_permission_filters, apply_ordering
    
    queryset = Permission.objects.all()
    queryset = apply_permission_filters(queryset, request)
    queryset = apply_ordering(queryset, request, default='-created_at')
"""
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta


# =============================================================================
# Generic helpers
# =============================================================================

def apply_ordering(queryset, request, default='-created_at', allowed_fields=None):
    """
    Apply ordering from ?ordering= query param.

    Args:
        queryset: The queryset to order
        request: The HTTP request
        default: Default ordering if none specified
        allowed_fields: List of allowed field names (without - prefix).
                       If None, allows all model fields.

    Examples:
        ?ordering=name           → ORDER BY name ASC
        ?ordering=-created_at    → ORDER BY created_at DESC
        ?ordering=name,-created_at → ORDER BY name ASC, created_at DESC
    """
    ordering_param = request.query_params.get('ordering', '').strip()
    if not ordering_param:
        return queryset.order_by(default) if default else queryset

    fields = [f.strip() for f in ordering_param.split(',') if f.strip()]

    if allowed_fields:
        valid_fields = []
        for field in fields:
            clean_field = field.lstrip('-')
            if clean_field in allowed_fields:
                valid_fields.append(field)
        fields = valid_fields

    if fields:
        return queryset.order_by(*fields)
    return queryset.order_by(default) if default else queryset


def apply_search(queryset, request, search_fields):
    """
    Apply text search from ?search= query param across multiple fields.

    Args:
        queryset: The queryset to filter
        request: The HTTP request
        search_fields: List of field names to search (supports __icontains lookup)

    Example:
        apply_search(qs, request, ['email', 'first_name', 'last_name'])
        → ?search=john → WHERE email ILIKE '%john%' OR first_name ILIKE '%john%' OR ...
    """
    search = request.query_params.get('search', '').strip()
    if not search:
        return queryset

    q = Q()
    for field in search_fields:
        q |= Q(**{f'{field}__icontains': search})
    return queryset.filter(q)


def apply_date_range(queryset, request, field_name='created_at'):
    """
    Apply date range filter from ?date_from= and ?date_to= query params.

    Args:
        queryset: The queryset to filter
        request: The HTTP request
        field_name: The date field to filter on
    """
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    if date_from:
        queryset = queryset.filter(**{f'{field_name}__gte': date_from})
    if date_to:
        queryset = queryset.filter(**{f'{field_name}__lte': date_to})

    return queryset


def apply_boolean_filter(queryset, request, param_name, field_name=None):
    """
    Apply boolean filter from a query param.

    Args:
        queryset: The queryset to filter
        request: The HTTP request
        param_name: Query parameter name (e.g. 'is_active')
        field_name: Model field name (defaults to param_name)
    """
    value = request.query_params.get(param_name)
    if value is None:
        return queryset

    field = field_name or param_name
    if value.lower() in ('true', '1', 'yes'):
        return queryset.filter(**{field: True})
    elif value.lower() in ('false', '0', 'no'):
        return queryset.filter(**{field: False})
    return queryset


# =============================================================================
# Permission filters
# =============================================================================

def apply_permission_filters(queryset, request):
    """
    Filter permissions queryset.

    Query params:
        ?search=      → Search in code, name
        ?parent=null  → Root permissions only (no parent)
        ?parent=<id>  → Children of specific parent
        ?ordering=    → Order by code, name, created_at (default: code)
    """
    queryset = apply_search(queryset, request, ['code', 'name'])

    parent = request.query_params.get('parent')
    if parent is not None:
        if parent.lower() == 'null' or parent == '':
            queryset = queryset.filter(parent__isnull=True)
        else:
            queryset = queryset.filter(parent_id=parent)

    queryset = apply_ordering(
        queryset, request, default='code',
        allowed_fields=['code', 'name', 'created_at']
    )
    return queryset


# =============================================================================
# Role filters
# =============================================================================

def apply_role_filters(queryset, request):
    """
    Filter roles queryset.

    Query params:
        ?search=      → Search in code, name
        ?is_default=  → Filter by is_default (true/false)
        ?ordering=    → Order by code, name, created_at (default: name)
    """
    queryset = apply_search(queryset, request, ['code', 'name'])
    queryset = apply_boolean_filter(queryset, request, 'is_default')
    queryset = apply_ordering(
        queryset, request, default='name',
        allowed_fields=['code', 'name', 'is_default', 'created_at']
    )
    return queryset


# =============================================================================
# Application filters
# =============================================================================

def apply_application_filters(queryset, request):
    """
    Filter applications queryset.

    Query params:
        ?search=      → Search in name, description
        ?is_active=   → Filter by active status (true/false)
        ?ordering=    → Order by name, created_at (default: name)
    """
    queryset = apply_search(queryset, request, ['name', 'description'])
    queryset = apply_boolean_filter(queryset, request, 'is_active')
    queryset = apply_ordering(
        queryset, request, default='name',
        allowed_fields=['name', 'is_active', 'created_at', 'updated_at']
    )
    return queryset


# =============================================================================
# User filters  (for future admin views)
# =============================================================================

def apply_user_filters(queryset, request):
    """
    Filter users queryset.

    Query params:
        ?search=             → Search in email, first_name, last_name
        ?is_active=          → Filter by active status
        ?is_locked=          → Filter by locked status
        ?is_banned=          → Filter by ban status
        ?is_deleted=         → Filter by soft-deleted status
        ?is_email_verified=  → Filter by email verified
        ?is_2fa_enabled=     → Filter by 2FA enabled
        ?role=               → Filter by role code
        ?date_from=          → Created after date
        ?date_to=            → Created before date
        ?ordering=           → Order by email, created_at, last_login (default: -created_at)
    """
    queryset = apply_search(queryset, request, ['email', 'first_name', 'last_name'])

    for field in ['is_active', 'is_locked', 'is_banned', 'is_deleted',
                  'is_email_verified', 'is_2fa_enabled']:
        queryset = apply_boolean_filter(queryset, request, field)

    role = request.query_params.get('role')
    if role:
        queryset = queryset.filter(roles__code=role).distinct()

    queryset = apply_date_range(queryset, request)
    queryset = apply_ordering(
        queryset, request, default='-created_at',
        allowed_fields=['email', 'first_name', 'last_name', 'created_at',
                        'last_login', 'is_active', 'is_locked']
    )
    return queryset


# =============================================================================
# Organization filters
# =============================================================================

def apply_organization_filters(queryset, request):
    """
    Filter organizations queryset.

    Query params:
        ?search=      → Search in name, slug
        ?is_active=   → Filter by active status
        ?parent=null  → Root organizations only (no parent)
        ?parent=<id>  → Children of specific parent
        ?ordering=    → Order by name, created_at (default: name)
    """
    queryset = apply_search(queryset, request, ['name', 'slug'])
    queryset = apply_boolean_filter(queryset, request, 'is_active')

    parent = request.query_params.get('parent')
    if parent is not None:
        if parent.lower() == 'null' or parent == '':
            queryset = queryset.filter(parent__isnull=True)
        else:
            queryset = queryset.filter(parent_id=parent)

    queryset = apply_ordering(
        queryset, request, default='name',
        allowed_fields=['name', 'slug', 'created_at', 'is_active']
    )
    return queryset


def apply_member_filters(queryset, request):
    """
    Filter organization members queryset.

    Query params:
        ?search=     → Search in user email, first_name, last_name
        ?role=       → Filter by role code
        ?status=     → Filter by membership status (active, suspended, etc.)
        ?ordering=   → Order by created_at, user__email (default: -created_at)
    """
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )

    role = request.query_params.get('role')
    if role:
        queryset = queryset.filter(role__code=role)

    status = request.query_params.get('status')
    if status:
        queryset = queryset.filter(status=status)

    queryset = apply_ordering(
        queryset, request, default='-created_at',
        allowed_fields=['created_at', 'user__email', 'role__code', 'status']
    )
    return queryset


# =============================================================================
# Audit Log filters (for future security views)
# =============================================================================

def apply_audit_log_filters(queryset, request):
    """
    Filter audit logs queryset.

    Query params:
        ?user_id=        → Filter by user
        ?action=         → Filter by action(s), comma-separated
        ?ip_address=     → Filter by IP
        ?application_id= → Filter by application
        ?date_from=      → Created after date
        ?date_to=        → Created before date
        ?ordering=       → Order by created_at, action (default: -created_at)
    """
    user_id = request.query_params.get('user_id')
    if user_id:
        queryset = queryset.filter(user_id=user_id)

    action = request.query_params.get('action')
    if action:
        actions = [a.strip() for a in action.split(',')]
        queryset = queryset.filter(action__in=actions)

    ip_address = request.query_params.get('ip_address')
    if ip_address:
        queryset = queryset.filter(ip_address=ip_address)

    application_id = request.query_params.get('application_id')
    if application_id:
        queryset = queryset.filter(application_id=application_id)

    queryset = apply_date_range(queryset, request)
    queryset = apply_ordering(
        queryset, request, default='-created_at',
        allowed_fields=['created_at', 'action', 'user_id', 'ip_address']
    )
    return queryset


# =============================================================================
# Login Attempt filters (for future security views)
# =============================================================================

def apply_login_attempt_filters(queryset, request):
    """
    Filter login attempts queryset.

    Query params:
        ?identifier=  → Filter by login identifier (email, phone)
        ?ip_address=  → Filter by IP
        ?success=     → Filter by success (true/false)
        ?date_from=   → Created after date
        ?date_to=     → Created before date
        ?ordering=    → Order by created_at (default: -created_at)
    """
    identifier = request.query_params.get('identifier')
    if identifier:
        queryset = queryset.filter(identifier__icontains=identifier)

    ip_address = request.query_params.get('ip_address')
    if ip_address:
        queryset = queryset.filter(ip_address=ip_address)

    queryset = apply_boolean_filter(queryset, request, 'success')
    queryset = apply_date_range(queryset, request)
    queryset = apply_ordering(
        queryset, request, default='-created_at',
        allowed_fields=['created_at', 'identifier', 'ip_address', 'success']
    )
    return queryset
