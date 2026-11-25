"""
Default RBAC seed data — shared, framework-agnostic source of truth for both adapters'
quickstart/seed tooling (`management/commands/tenxyte_seed.py` for Django,
`adapters/fastapi/quickstart.py` for FastAPI).

Previously each adapter defined its own literal copy of this data (`tenxyte_seed.py` first,
`quickstart.py` copied it verbatim when it was added). Extracted here so the two can never
silently drift apart — a project comparing RBAC data across both adapters sees identical codes,
hierarchy, and role assignments by construction, not by two humans remembering to keep two lists
in sync.
"""

from __future__ import annotations

# =============================================================================
# DEFAULT PERMISSIONS
# =============================================================================

DEFAULT_PERMISSIONS = [
    # -- Parent groups (hierarchical: having a parent grants all its children) --
    {"code": "users", "name": "Users", "description": "All user permissions"},
    {"code": "users.roles", "name": "User Roles", "description": "All user role permissions", "parent": "users"},
    {
        "code": "users.permissions",
        "name": "User Permissions",
        "description": "All user direct permission management",
        "parent": "users",
    },
    {"code": "roles", "name": "Roles", "description": "All role permissions"},
    {"code": "permissions", "name": "Permissions", "description": "All permission permissions"},
    {"code": "applications", "name": "Applications", "description": "All application permissions"},
    {"code": "content", "name": "Content", "description": "All content permissions"},
    {"code": "system", "name": "System", "description": "All system permissions"},
    # User permissions
    {"code": "users.view", "name": "View Users", "description": "Can view user list and details", "parent": "users"},
    {"code": "users.create", "name": "Create Users", "description": "Can create new users", "parent": "users"},
    {"code": "users.update", "name": "Update Users", "description": "Can update user information", "parent": "users"},
    {"code": "users.delete", "name": "Delete Users", "description": "Can delete users", "parent": "users"},
    {"code": "users.ban", "name": "Ban Users", "description": "Can ban/unban users", "parent": "users"},
    {"code": "users.lock", "name": "Lock Users", "description": "Can lock/unlock user accounts", "parent": "users"},
    {
        "code": "users.roles.view",
        "name": "View User Roles",
        "description": "Can view user roles",
        "parent": "users.roles",
    },
    {
        "code": "users.roles.assign",
        "name": "Assign User Roles",
        "description": "Can assign roles to users",
        "parent": "users.roles",
    },
    {
        "code": "users.roles.remove",
        "name": "Remove User Roles",
        "description": "Can remove roles from users",
        "parent": "users.roles",
    },
    {
        "code": "users.permissions.view",
        "name": "View User Permissions",
        "description": "Can view user direct permissions",
        "parent": "users.permissions",
    },
    {
        "code": "users.permissions.assign",
        "name": "Assign User Permissions",
        "description": "Can assign direct permissions to users",
        "parent": "users.permissions",
    },
    {
        "code": "users.permissions.remove",
        "name": "Remove User Permissions",
        "description": "Can remove direct permissions from users",
        "parent": "users.permissions",
    },
    # Role permissions
    {"code": "roles.view", "name": "View Roles", "description": "Can view role list and details", "parent": "roles"},
    {"code": "roles.create", "name": "Create Roles", "description": "Can create new roles", "parent": "roles"},
    {"code": "roles.update", "name": "Update Roles", "description": "Can update role information", "parent": "roles"},
    {"code": "roles.delete", "name": "Delete Roles", "description": "Can delete roles", "parent": "roles"},
    {
        "code": "roles.manage_permissions",
        "name": "Manage Role Permissions",
        "description": "Can assign/remove permissions from roles",
        "parent": "roles",
    },
    # Permission permissions
    {
        "code": "permissions.view",
        "name": "View Permissions",
        "description": "Can view permission list",
        "parent": "permissions",
    },
    {
        "code": "permissions.create",
        "name": "Create Permissions",
        "description": "Can create new permissions",
        "parent": "permissions",
    },
    {
        "code": "permissions.update",
        "name": "Update Permissions",
        "description": "Can update permission information",
        "parent": "permissions",
    },
    {
        "code": "permissions.delete",
        "name": "Delete Permissions",
        "description": "Can delete permissions",
        "parent": "permissions",
    },
    # Application permissions
    {
        "code": "applications.view",
        "name": "View Applications",
        "description": "Can view application list and details",
        "parent": "applications",
    },
    {
        "code": "applications.create",
        "name": "Create Applications",
        "description": "Can create new applications",
        "parent": "applications",
    },
    {
        "code": "applications.update",
        "name": "Update Applications",
        "description": "Can update application information",
        "parent": "applications",
    },
    {
        "code": "applications.delete",
        "name": "Delete Applications",
        "description": "Can delete applications",
        "parent": "applications",
    },
    {
        "code": "applications.regenerate",
        "name": "Regenerate Credentials",
        "description": "Can regenerate application credentials",
        "parent": "applications",
    },
    # Content permissions (generic)
    {"code": "content.view", "name": "View Content", "description": "Can view content", "parent": "content"},
    {"code": "content.create", "name": "Create Content", "description": "Can create content", "parent": "content"},
    {"code": "content.edit", "name": "Edit Content", "description": "Can edit content", "parent": "content"},
    {"code": "content.delete", "name": "Delete Content", "description": "Can delete content", "parent": "content"},
    {"code": "content.publish", "name": "Publish Content", "description": "Can publish content", "parent": "content"},
    # System permissions
    {
        "code": "system.admin",
        "name": "System Administration",
        "description": "Full system administration access",
        "parent": "system",
    },
    {
        "code": "system.settings",
        "name": "Manage Settings",
        "description": "Can manage system settings",
        "parent": "system",
    },
    {"code": "system.logs", "name": "View Logs", "description": "Can view system logs", "parent": "system"},
    {"code": "system.audit", "name": "View Audit Trail", "description": "Can view audit trail", "parent": "system"},
    # Dashboard & Security permissions
    {"code": "dashboard.view", "name": "View Dashboard", "description": "Can access dashboard statistics"},
    {"code": "security.view", "name": "View Security", "description": "Can view audit logs, login attempts, tokens"},
    {"code": "gdpr.admin", "name": "GDPR Admin", "description": "Can view deletion requests"},
    {"code": "gdpr.process", "name": "GDPR Process", "description": "Can process deletion requests"},
]

# =============================================================================
# DEFAULT ROLES WITH THEIR PERMISSIONS
# =============================================================================

DEFAULT_ROLES = [
    {
        "code": "viewer",
        "name": "Viewer",
        "description": "Read-only access to content",
        "is_default": True,  # Default role for new users
        "permissions": ["content.view"],
    },
    {
        "code": "editor",
        "name": "Editor",
        "description": "Can create and edit content",
        "is_default": False,
        "permissions": ["content.view", "content.create", "content.edit"],
    },
    {
        "code": "admin",
        "name": "Administrator",
        "description": "Administrative access to users and content",
        "is_default": False,
        "permissions": [
            # Content
            "content.view",
            "content.create",
            "content.edit",
            "content.delete",
            "content.publish",
            # Users
            "users.view",
            "users.create",
            "users.update",
            "users.roles.view",
            "users.roles.assign",
            "users.roles.remove",
            # Roles
            "roles.view",
            # Permissions
            "permissions.view",
        ],
    },
    {
        "code": "super_admin",
        "name": "Super Administrator",
        "description": "Full access to all system features",
        "is_default": False,
        "permissions": [
            # All permissions - resolved dynamically to every permission that exists at seed time,
            # not just the codes listed in DEFAULT_PERMISSIONS above (see each adapter's own
            # seeding code) -- a custom project permission gets included too.
            "__all__",
        ],
    },
]
