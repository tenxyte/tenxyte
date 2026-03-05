"""
Tenant context management via contextvars.
This allows accessing the current organization anywhere in the request lifecycle
without having to pass the request object around.
"""

from contextvars import ContextVar
from typing import Optional, Any

# Context variable to store the current active organization.
# Default to None to indicate no organization context.
_current_organization: ContextVar[Optional[Any]] = ContextVar("current_organization", default=None)

# Context variable to bypass tenant filtering temporarily if needed
# (e.g., for admin tasks or system-level queries)
_INTERNAL_bypass_tenant_filtering: ContextVar[bool] = ContextVar("bypass_tenant_filtering", default=False)


def set_current_organization(organization: Optional[Any]) -> None:
    """
    Set the current organization in the context.

    Args:
        organization: The Organization instance or None
    """
    _current_organization.set(organization)


def get_current_organization() -> Optional[Any]:
    """
    Get the current organization from the context.

    Returns:
        The current Organization instance or None
    """
    return _current_organization.get()


def set_INTERNAL_bypass_tenant_filtering(bypass: bool) -> None:
    """
    Temporarily bypass tenant filtering for the current context.

    WARNING: This breaks tenant isolation. It should ONLY be used in
    secure internal commands/tasks.

    Args:
        bypass: True to disable filtering, False to re-enable
    """
    if bypass:
        import inspect
        import logging

        logger = logging.getLogger("tenxyte.security")

        # Security check F-06: Check call stack to ensure it's not from a view
        stack = inspect.stack()
        for frame_info in stack[1:6]:  # Check recent frames
            frame_name = frame_info.function
            frame_filename = frame_info.filename

            # Warn if bypassing tenant filtering from a view or middleware
            if "views/" in frame_filename or "middleware.py" in frame_filename or frame_name.startswith("view_"):
                logger.error(
                    "CRITICAL SECURITY WARNING: Tenant filtering bypass activated from an unsafe context %s:%s. "
                    "This breaks multi-tenant isolation!",
                    frame_filename,
                    frame_name,
                )
                break
        else:
            logger.info("Tenant filtering bypass activated internally.")

    _INTERNAL_bypass_tenant_filtering.set(bypass)


def get_INTERNAL_bypass_tenant_filtering() -> bool:
    """
    Check if tenant filtering is currently bypassed.

    Returns:
        True if filtering should be bypassed
    """
    return _INTERNAL_bypass_tenant_filtering.get()
