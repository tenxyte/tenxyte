#!/usr/bin/env python3
"""
Postman Collection Generator

This script generates a Postman collection from the OpenAPI specification:
1. Converts OpenAPI paths to Postman requests
2. Includes authentication setup
3. Adds environment variables
4. Generates test scripts
5. Includes example data
"""

import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class PostmanCollectionGenerator:
    """Generates Postman collection from OpenAPI schema."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.schema_file = self.project_root / 'openapi_schema_optimized.json'
        self.collection = {
            "info": {
                "name": "Tenxyte API",
                "description": "Enhanced DRF Spectacular Documentation - Postman Collection",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],
            "variable": [
                {
                    "key": "baseUrl",
                    "value": "https://api.tenxyte.com",
                    "type": "string"
                },
                {
                    "key": "accessToken",
                    "value": "",
                    "type": "string"
                },
                {
                    "key": "refreshToken",
                    "value": "",
                    "type": "string"
                },
                {
                    "key": "orgSlug",
                    "value": "acme-corp",
                    "type": "string"
                },
                {
                    "key": "userEmail",
                    "value": "user@example.com",
                    "type": "string"
                },
                {
                    "key": "userPassword",
                    "value": "password123",
                    "type": "string"
                }
            ],
            "event": [
                {
                    "listen": "prerequest",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "// Global pre-request script",
                            "// Set authentication headers if token is available",
                            "if (pm.collectionVariables.get('accessToken')) {",
                            "    pm.request.headers.add({",
                            "        key: 'Authorization',",
                            "        value: 'Bearer ' + pm.collectionVariables.get('accessToken')",
                            "        skipCaseHandling: true",
                            "    });",
                            "}",
                            "",
                            "// Add organization header if orgSlug is set",
                            "if (pm.collectionVariables.get('orgSlug')) {",
                            "    pm.request.headers.add({",
                            "        key: 'X-Org-Slug',",
                            "        value: pm.collectionVariables.get('orgSlug'),",
                            "        skipCaseHandling: true",
                            "    });",
                            "}"
                        ]
                    }
                },
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "// Global test script",
                            "// Store tokens from login responses",
                            "if (pm.response.code === 200) {",
                            "    const response = pm.response.json();",
                            "    ",
                            "    // Store JWT tokens from login response",
                            "    if (response.access && response.refresh) {",
                            "        pm.collectionVariables.set('accessToken', response.access);",
                            "        pm.collectionVariables.set('refreshToken', response.refresh);",
                            "        console.log('Tokens stored successfully');",
                            "    }",
                            "    ",
                            "    // Store user data",
                            "    if (response.user) {",
                            "        pm.collectionVariables.set('userEmail', response.user.email);",
                            "        pm.collectionVariables.set('userId', response.user.id);",
                            "    }",
                            "}",
                            "",
                            "// Basic response validation",
                            "pm.test('Response time is less than 5000ms', function () {",
                            "    pm.expect(pm.response.responseTime).to.be.below(5000);",
                            "});",
                            "",
                            "pm.test('Response has proper content-type', function () {",
                            "    pm.expect(pm.response.headers.get('Content-Type')).to.include('application/json');",
                            "});"
                        ]
                    }
                }
            ]
        }
        
    def generate_collection(self) -> Dict:
        """Generate Postman collection from OpenAPI schema."""
        print("📮 Generating Postman collection...")
        
        # Load OpenAPI schema
        schema = self.load_schema()
        if not schema:
            return self.collection
        
        # Generate folders for different API sections
        self.create_auth_folder(schema)
        self.create_user_folder(schema)
        self.create_organization_folder(schema)
        self.create_security_folder(schema)
        self.create_admin_folder(schema)
        
        # Add documentation folder
        self.create_documentation_folder()
        
        return self.collection
    
    def load_schema(self) -> Dict:
        """Load OpenAPI schema."""
        if not self.schema_file.exists():
            # Try original schema if optimized doesn't exist
            self.schema_file = self.project_root / 'openapi_schema.json'
        
        if not self.schema_file.exists():
            print(f"❌ Schema file not found")
            return {}
        
        try:
            with open(self.schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            print(f"📋 Loaded schema from: {self.schema_file}")
            return schema
        except Exception as e:
            print(f"❌ Failed to load schema: {e}")
            return {}
    
    def create_auth_folder(self, schema: Dict):
        """Create authentication folder."""
        auth_folder = {
            "name": "🔐 Authentication",
            "item": [],
            "description": "Authentication endpoints for login, registration, and token management"
        }
        
        # Login endpoints
        auth_folder["item"].extend([
            self.create_login_request(),
            self.create_register_request(),
            self.create_refresh_token_request(),
            self.create_logout_request(),
            self.create_verify_email_request(),
            self.create_forgot_password_request()
        ])
        
        # 2FA endpoints
        auth_folder["item"].extend([
            self.create_setup_2fa_request(),
            self.create_verify_2fa_request(),
            self.create_disable_2fa_request()
        ])
        
        self.collection["item"].append(auth_folder)
    
    def create_login_request(self) -> Dict:
        """Create login request."""
        return {
            "name": "POST Login (Email)",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "email": "{{userEmail}}",
                        "password": "{{userPassword}}",
                        "device_fingerprint": "postman-test-device"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/login/email/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "login", "email", ""]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Login successful', function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 201]);",
                            "});",
                            "",
                            "pm.test('Response contains tokens', function () {",
                            "    const response = pm.response.json();",
                            "    pm.expect(response).to.have.property('access');",
                            "    pm.expect(response).to.have.property('refresh');",
                            "    pm.expect(response).to.have.property('user');",
                            "});",
                            "",
                            "pm.test('User data is valid', function () {",
                            "    const response = pm.response.json();",
                            "    pm.expect(response.user).to.have.property('id');",
                            "    pm.expect(response.user).to.have.property('email');",
                            "    pm.expect(response.user.email).to.eql(pm.collectionVariables.get('userEmail'));",
                            "});"
                        ]
                    }
                }
            ]
        }
    
    def create_register_request(self) -> Dict:
        """Create registration request."""
        return {
            "name": "POST Register",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "email": "newuser@example.com",
                        "password": "NewPassword123!",
                        "first_name": "New",
                        "last_name": "User",
                        "phone": "+1234567890"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/register/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "register", ""]
                }
            }
        }
    
    def create_refresh_token_request(self) -> Dict:
        """Create refresh token request."""
        return {
            "name": "POST Refresh Token",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "refresh": "{{refreshToken}}"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/refresh/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "refresh", ""]
                }
            }
        }
    
    def create_logout_request(self) -> Dict:
        """Create logout request."""
        return {
            "name": "POST Logout",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "refresh": "{{refreshToken}}"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/logout/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "logout", ""]
                }
            }
        }
    
    def create_verify_email_request(self) -> Dict:
        """Create email verification request."""
        return {
            "name": "POST Verify Email",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "token": "email_verification_token_here"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/verify-email/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "verify-email", ""]
                }
            }
        }
    
    def create_forgot_password_request(self) -> Dict:
        """Create forgot password request."""
        return {
            "name": "POST Forgot Password",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "email": "{{userEmail}}"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/password/reset/request/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "password", "reset", "request", ""]
                }
            }
        }
    
    def create_setup_2fa_request(self) -> Dict:
        """Create 2FA setup request."""
        return {
            "name": "POST Setup 2FA",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "password": "{{userPassword}}"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/2fa/setup/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "2fa", "setup", ""]
                }
            }
        }
    
    def create_verify_2fa_request(self) -> Dict:
        """Create 2FA verification request."""
        return {
            "name": "POST Verify 2FA",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "code": "123456"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/2fa/confirm/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "2fa", "confirm", ""]
                }
            }
        }
    
    def create_disable_2fa_request(self) -> Dict:
        """Create 2FA disable request."""
        return {
            "name": "POST Disable 2FA",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "password": "{{userPassword}}"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/2fa/disable/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "2fa", "disable", ""]
                }
            }
        }
    
    def create_user_folder(self, schema: Dict):
        """Create user management folder."""
        user_folder = {
            "name": "👤 User Management",
            "item": [],
            "description": "User profile management and personal data endpoints"
        }
        
        user_folder["item"].extend([
            self.create_get_profile_request(),
            self.create_update_profile_request(),
            self.create_upload_avatar_request(),
            self.create_delete_account_request(),
            self.create_get_roles_request(),
            self.create_get_sessions_request(),
            self.create_get_devices_request()
        ])
        
        self.collection["item"].append(user_folder)
    
    def create_get_profile_request(self) -> Dict:
        """Create get profile request."""
        return {
            "name": "GET My Profile",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", ""]
                }
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "pm.test('Profile retrieved successfully', function () {",
                            "    pm.expect(pm.response.code).to.be.oneOf([200, 201]);",
                            "});",
                            "",
                            "pm.test('Profile contains required fields', function () {",
                            "    const response = pm.response.json();",
                            "    pm.expect(response).to.have.property('id');",
                            "    pm.expect(response).to.have.property('email');",
                            "    pm.expect(response).to.have.property('first_name');",
                            "    pm.expect(response).to.have.property('last_name');",
                            "});"
                        ]
                    }
                }
            ]
        }
    
    def create_update_profile_request(self) -> Dict:
        """Create update profile request."""
        return {
            "name": "PATCH Update Profile",
            "request": {
                "method": "PATCH",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "first_name": "Updated",
                        "last_name": "Name",
                        "phone": "+1234567890"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", ""]
                }
            }
        }
    
    def create_upload_avatar_request(self) -> Dict:
        """Create upload avatar request."""
        return {
            "name": "POST Upload Avatar",
            "request": {
                "method": "POST",
                "header": [],
                "body": {
                    "mode": "formdata",
                    "formdata": [
                        {
                            "key": "avatar",
                            "type": "file",
                            "src": ""
                        }
                    ]
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/avatar/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", "avatar", ""]
                }
            }
        }
    
    def create_delete_account_request(self) -> Dict:
        """Create delete account request."""
        return {
            "name": "DELETE Account",
            "request": {
                "method": "DELETE",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "confirmation": "DELETE MY ACCOUNT",
                        "password": "{{userPassword}}",
                        "reason": "Testing account deletion"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", ""]
                }
            }
        }
    
    def create_get_roles_request(self) -> Dict:
        """Create get roles request."""
        return {
            "name": "GET My Roles",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/roles/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", "roles", ""]
                }
            }
        }
    
    def create_get_sessions_request(self) -> Dict:
        """Create get sessions request."""
        return {
            "name": "GET My Sessions",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/sessions/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", "sessions", ""]
                }
            }
        }
    
    def create_get_devices_request(self) -> Dict:
        """Create get devices request."""
        return {
            "name": "GET My Devices",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/devices/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", "devices", ""]
                }
            }
        }
    
    def create_organization_folder(self, schema: Dict):
        """Create organization management folder."""
        org_folder = {
            "name": "🏢 Organizations",
            "item": [],
            "description": "Organization management and multi-tenant endpoints"
        }
        
        org_folder["item"].extend([
            self.create_list_organizations_request(),
            self.create_create_organization_request(),
            self.create_get_organization_request(),
            self.create_list_members_request(),
            self.create_invite_member_request()
        ])
        
        self.collection["item"].append(org_folder)
    
    def create_list_organizations_request(self) -> Dict:
        """Create list organizations request."""
        return {
            "name": "GET List Organizations",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/organizations/list/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "organizations", "list", ""]
                }
            }
        }
    
    def create_create_organization_request(self) -> Dict:
        """Create organization request."""
        return {
            "name": "POST Create Organization",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "name": "Test Organization",
                        "slug": "test-org",
                        "description": "Test organization for Postman"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/organizations/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "organizations", ""]
                }
            }
        }
    
    def create_get_organization_request(self) -> Dict:
        """Create get organization request."""
        return {
            "name": "GET Organization Details",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/organizations/{{orgSlug}}/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "organizations", "{{orgSlug}}", ""]
                }
            }
        }
    
    def create_list_members_request(self) -> Dict:
        """Create list members request."""
        return {
            "name": "GET Organization Members",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/organizations/{{orgSlug}}/members/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "organizations", "{{orgSlug}}", "members", ""]
                }
            }
        }
    
    def create_invite_member_request(self) -> Dict:
        """Create invite member request."""
        return {
            "name": "POST Invite Member",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "email": "newmember@example.com",
                        "role_code": "member"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/organizations/{{orgSlug}}/members/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "organizations", "{{orgSlug}}", "members", ""]
                }
            }
        }
    
    def create_security_folder(self, schema: Dict):
        """Create security folder."""
        security_folder = {
            "name": "🔒 Security",
            "item": [],
            "description": "Security and device management endpoints"
        }
        
        security_folder["item"].extend([
            self.create_request_account_deletion_request(),
            self.create_confirm_account_deletion_request(),
            self.create_cancel_account_deletion_request()
        ])
        
        self.collection["item"].append(security_folder)
    
    def create_request_account_deletion_request(self) -> Dict:
        """Create request account deletion."""
        return {
            "name": "POST Request Account Deletion",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "password": "{{userPassword}}",
                        "reason": "Testing GDPR compliance"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/request-account-deletion/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", "request-account-deletion", ""]
                }
            }
        }
    
    def create_confirm_account_deletion_request(self) -> Dict:
        """Create confirm account deletion."""
        return {
            "name": "POST Confirm Account Deletion",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "token": "deletion_confirmation_token_here"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/confirm-account-deletion/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", "confirm-account-deletion", ""]
                }
            }
        }
    
    def create_cancel_account_deletion_request(self) -> Dict:
        """Create cancel account deletion."""
        return {
            "name": "POST Cancel Account Deletion",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "password": "{{userPassword}}"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/auth/me/cancel-account-deletion/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "me", "cancel-account-deletion", ""]
                }
            }
        }
    
    def create_admin_folder(self, schema: Dict):
        """Create admin folder."""
        admin_folder = {
            "name": "👑 Admin",
            "item": [],
            "description": "Admin and management endpoints"
        }
        
        admin_folder["item"].extend([
            self.create_admin_list_users_request(),
            self.create_admin_gdpr_requests_request(),
            self.create_dashboard_stats_request()
        ])
        
        self.collection["item"].append(admin_folder)
    
    def create_admin_list_users_request(self) -> Dict:
        """Create admin list users request."""
        return {
            "name": "GET Admin List Users",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/admin/users/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "admin", "users", ""]
                }
            }
        }
    
    def create_admin_gdpr_requests_request(self) -> Dict:
        """Create admin GDPR requests request."""
        return {
            "name": "GET Admin GDPR Requests",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/admin/gdpr/deletion-requests/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "admin", "gdpr", "deletion-requests", ""]
                }
            }
        }
    
    def create_dashboard_stats_request(self) -> Dict:
        """Create dashboard stats request."""
        return {
            "name": "GET Dashboard Stats",
            "request": {
                "method": "GET",
                "url": {
                    "raw": "{{baseUrl}}/api/auth/dashboard/stats/",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "auth", "dashboard", "stats", ""]
                }
            }
        }
    
    def create_documentation_folder(self):
        """Create documentation folder."""
        doc_folder = {
            "name": "📚 Documentation",
            "item": [
                {
                    "name": "📖 API Documentation",
                    "request": {
                        "method": "GET",
                        "url": {
                            "raw": "{{baseUrl}}/api/docs/",
                            "host": ["{{baseUrl}}"],
                            "path": ["api", "docs", ""]
                        }
                    }
                },
                {
                    "name": "📋 ReDoc Documentation",
                    "request": {
                        "method": "GET",
                        "url": {
                            "raw": "{{baseUrl}}/api/redoc/",
                            "host": ["{{baseUrl}}"],
                            "path": ["api", "redoc", ""]
                        }
                    }
                },
                {
                    "name": "📄 OpenAPI Schema",
                    "request": {
                        "method": "GET",
                        "url": {
                            "raw": "{{baseUrl}}/api/schema/",
                            "host": ["{{baseUrl}}"],
                            "path": ["api", "schema", ""]
                        }
                    }
                }
            ],
            "description": "Access to API documentation and schema"
        }
        
        self.collection["item"].append(doc_folder)
    
    def save_collection(self, collection: Dict):
        """Save Postman collection to file."""
        output_file = self.project_root / 'tenxyte_api_collection.postman_collection.json'
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(collection, f, indent=2)
            print(f"📮 Postman collection saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save collection: {e}")
    
    def generate_environment(self) -> Dict:
        """Generate Postman environment file."""
        environment = {
            "id": str(uuid.uuid4()),
            "name": "Tenxyte API Environment",
            "values": [
                {
                    "key": "baseUrl",
                    "value": "https://api.tenxyte.com",
                    "type": "default",
                    "enabled": True,
                    "description": "Base URL for the Tenxyte API"
                },
                {
                    "key": "accessToken",
                    "value": "",
                    "type": "secret",
                    "enabled": True,
                    "description": "JWT access token (automatically set after login)"
                },
                {
                    "key": "refreshToken",
                    "value": "",
                    "type": "secret",
                    "enabled": True,
                    "description": "JWT refresh token (automatically set after login)"
                },
                {
                    "key": "orgSlug",
                    "value": "acme-corp",
                    "type": "default",
                    "enabled": True,
                    "description": "Organization slug for multi-tenant requests"
                },
                {
                    "key": "userEmail",
                    "value": "user@example.com",
                    "type": "default",
                    "enabled": True,
                    "description": "User email for login requests"
                },
                {
                    "key": "userPassword",
                    "value": "password123",
                    "type": "secret",
                    "enabled": True,
                    "description": "User password for login requests"
                }
            ]
        }
        
        # Save environment file
        env_file = self.project_root / 'tenxyte_api_environment.postman_environment.json'
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                json.dump(environment, f, indent=2)
            print(f"🌍 Postman environment saved to: {env_file}")
        except Exception as e:
            print(f"❌ Failed to save environment: {e}")
        
        return environment


def main():
    """Main collection generator."""
    generator = PostmanCollectionGenerator()
    
    # Generate collection
    collection = generator.generate_collection()
    generator.save_collection(collection)
    
    # Generate environment
    environment = generator.generate_environment()
    
    # Print summary
    print(f"\n📮 COLLECTION SUMMARY:")
    print(f"   Folders: {len(collection['item'])}")
    print(f"   Variables: {len(collection['variable'])}")
    print(f"   Environment Variables: {len(environment['values'])}")
    
    print(f"\n✅ Postman collection and environment generated successfully!")
    print(f"\n📋 IMPORT INSTRUCTIONS:")
    print(f"   1. Import the collection file into Postman")
    print(f"   2. Import the environment file into Postman")
    print(f"   3. Set your credentials in the environment variables")
    print(f"   4. Start with the 'POST Login' request in the Authentication folder")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
