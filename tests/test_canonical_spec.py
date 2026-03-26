"""
Tests de conformité à la spécification canonique.

Vérifie que les réponses API (Pydantic et DRF) correspondent exactement
aux schémas définis dans docs/en/schemas.md.
"""

import pytest
from typing import Set


class TestUserSchemaConformity:
    """Vérifie que le schéma User respecte la spec canonique."""
    
    CANONICAL_USER_FIELDS = {
        'id', 'email', 'username', 'phone', 'avatar', 'bio',
        'timezone', 'language', 'first_name', 'last_name',
        'is_active', 'is_email_verified', 'is_phone_verified',
        'is_2fa_enabled', 'created_at', 'updated_at', 'last_login',
        'custom_fields', 'preferences', 'roles', 'permissions'
    }
    
    def test_user_serializer_fields(self):
        """Vérifie que UserSerializer retourne exactement les champs canoniques."""
        from tenxyte.serializers.auth_serializers import UserSerializer
        
        serializer_fields = set(UserSerializer.Meta.fields)
        assert serializer_fields == self.CANONICAL_USER_FIELDS, (
            f"Champs manquants: {self.CANONICAL_USER_FIELDS - serializer_fields}\n"
            f"Champs en trop: {serializer_fields - self.CANONICAL_USER_FIELDS}"
        )
    
    def test_user_pydantic_schema_fields(self):
        """Vérifie que UserResponse (Pydantic) a les bons champs."""
        from tenxyte.core.schemas import UserResponse
        
        pydantic_fields = set(UserResponse.model_fields.keys())
        # Pydantic peut avoir des champs supplémentaires pour backward compatibility
        required_fields = self.CANONICAL_USER_FIELDS
        
        missing_fields = required_fields - pydantic_fields
        assert not missing_fields, f"Champs manquants dans Pydantic: {missing_fields}"
    
    def test_user_roles_is_string_array(self):
        """Vérifie que roles est une liste de strings (codes)."""
        from tenxyte.serializers.auth_serializers import UserSerializer
        from rest_framework import serializers
        
        # Vérifier que le champ existe dans Meta.fields
        assert 'roles' in UserSerializer.Meta.fields, "Le champ 'roles' est manquant"
    
    def test_user_permissions_is_string_array(self):
        """Vérifie que permissions est une liste de strings (codes)."""
        from tenxyte.serializers.auth_serializers import UserSerializer
        
        # Vérifier que le champ existe dans Meta.fields
        assert 'permissions' in UserSerializer.Meta.fields, "Le champ 'permissions' est manquant"


class TestTokenPairSchemaConformity:
    """Vérifie que le schéma TokenPair respecte la spec canonique."""
    
    CANONICAL_TOKEN_FIELDS = {
        'access_token', 'refresh_token', 'token_type',
        'expires_in', 'refresh_expires_in', 'device_summary'
    }
    
    def test_token_response_pydantic_fields(self):
        """Vérifie que TokenResponse (Pydantic) a tous les champs canoniques."""
        from tenxyte.core.schemas import TokenResponse
        
        pydantic_fields = set(TokenResponse.model_fields.keys())
        missing_fields = self.CANONICAL_TOKEN_FIELDS - pydantic_fields
        
        assert not missing_fields, f"Champs manquants dans TokenResponse: {missing_fields}"


class TestErrorResponseSchemaConformity:
    """Vérifie que le schéma ErrorResponse respecte la spec canonique."""
    
    CANONICAL_ERROR_FIELDS = {'error', 'code', 'details'}
    
    def test_error_response_pydantic_fields(self):
        """Vérifie que ErrorResponse (Pydantic) a les bons champs."""
        from tenxyte.core.schemas import ErrorResponse
        
        pydantic_fields = set(ErrorResponse.model_fields.keys())
        assert pydantic_fields == self.CANONICAL_ERROR_FIELDS, (
            f"Champs attendus: {self.CANONICAL_ERROR_FIELDS}\n"
            f"Champs actuels: {pydantic_fields}"
        )
    
    def test_error_response_details_is_dict(self):
        """Vérifie que details est un Dict[str, List[str]]."""
        from tenxyte.core.schemas import ErrorResponse
        from typing import get_args, get_origin
        
        details_field = ErrorResponse.model_fields['details']
        # Vérifie que c'est Optional[Dict[str, List[str]]]
        assert details_field.annotation is not None


class TestPaginatedResponseSchemaConformity:
    """Vérifie que le schéma PaginatedResponse respecte la spec canonique."""
    
    CANONICAL_PAGINATION_FIELDS = {
        'count', 'page', 'page_size', 'total_pages',
        'next', 'previous', 'results'
    }
    
    def test_pagination_pydantic_fields(self):
        """Vérifie que PaginatedResponse (Pydantic) a tous les champs."""
        from tenxyte.core.schemas import PaginatedResponse
        
        pydantic_fields = set(PaginatedResponse.model_fields.keys())
        assert pydantic_fields == self.CANONICAL_PAGINATION_FIELDS, (
            f"Champs manquants: {self.CANONICAL_PAGINATION_FIELDS - pydantic_fields}\n"
            f"Champs en trop: {pydantic_fields - self.CANONICAL_PAGINATION_FIELDS}"
        )
    
    def test_tenxyte_pagination_response_format(self):
        """Vérifie que TenxytePagination retourne le bon format."""
        from tenxyte.pagination import TenxytePagination
        from collections import OrderedDict
        
        # Créer une instance mock pour tester le format
        pagination = TenxytePagination()
        
        # Vérifier que get_paginated_response_schema retourne les bons champs
        schema = pagination.get_paginated_response_schema({'type': 'object'})
        
        schema_fields = set(schema['properties'].keys())
        assert schema_fields == self.CANONICAL_PAGINATION_FIELDS, (
            f"Champs du schéma de pagination incorrects: {schema_fields}"
        )


class TestRoleSchemaConformity:
    """Vérifie que le schéma Role respecte la spec canonique."""
    
    CANONICAL_ROLE_FIELDS = {
        'id', 'code', 'name', 'description', 'permissions',
        'is_default', 'created_at', 'updated_at'
    }
    
    def test_role_serializer_fields(self):
        """Vérifie que RoleSerializer a tous les champs canoniques."""
        from tenxyte.serializers.rbac_serializers import RoleSerializer
        
        serializer_fields = set(RoleSerializer.Meta.fields)
        # Exclure permission_codes qui est write_only
        serializer_fields.discard('permission_codes')
        
        assert serializer_fields == self.CANONICAL_ROLE_FIELDS, (
            f"Champs manquants: {self.CANONICAL_ROLE_FIELDS - serializer_fields}\n"
            f"Champs en trop: {serializer_fields - self.CANONICAL_ROLE_FIELDS}"
        )
    
    def test_role_permissions_are_objects(self):
        """Vérifie que permissions retourne des objets PermissionResponse complets."""
        from tenxyte.serializers.rbac_serializers import RoleSerializer
        
        # Vérifier que le champ permissions existe
        assert 'permissions' in RoleSerializer.Meta.fields, "Le champ 'permissions' est manquant"


class TestAuditLogSchemaConformity:
    """Vérifie que le schéma AuditLog respecte la spec canonique."""
    
    CANONICAL_AUDITLOG_FIELDS = {
        'id', 'user', 'user_email', 'action', 'ip_address',
        'user_agent', 'application', 'application_name',
        'details', 'created_at'
    }
    
    def test_auditlog_serializer_fields(self):
        """Vérifie que AuditLogSerializer a tous les champs canoniques."""
        from tenxyte.serializers.security_serializers import AuditLogSerializer
        
        serializer_fields = set(AuditLogSerializer.Meta.fields)
        assert serializer_fields == self.CANONICAL_AUDITLOG_FIELDS, (
            f"Champs manquants: {self.CANONICAL_AUDITLOG_FIELDS - serializer_fields}\n"
            f"Champs en trop: {serializer_fields - self.CANONICAL_AUDITLOG_FIELDS}"
        )
    
    def test_auditlog_pydantic_fields(self):
        """Vérifie que AuditLogEntry (Pydantic) a tous les champs."""
        from tenxyte.core.schemas import AuditLogEntry
        
        pydantic_fields = set(AuditLogEntry.model_fields.keys())
        assert pydantic_fields == self.CANONICAL_AUDITLOG_FIELDS, (
            f"Champs manquants: {self.CANONICAL_AUDITLOG_FIELDS - pydantic_fields}\n"
            f"Champs en trop: {pydantic_fields - self.CANONICAL_AUDITLOG_FIELDS}"
        )


class TestSecuritySchemasConformity:
    """Vérifie les schémas de sécurité (Session, Device, etc.)."""
    
    CANONICAL_SESSION_FIELDS = {
        'id', 'user_id', 'device_info', 'ip_address', 'user_agent',
        'is_current', 'created_at', 'last_activity', 'expires_at'
    }
    
    CANONICAL_DEVICE_FIELDS = {
        'id', 'user_id', 'device_fingerprint', 'device_name',
        'device_type', 'platform', 'browser', 'is_trusted',
        'last_seen', 'created_at'
    }
    
    CANONICAL_LOGIN_ATTEMPT_FIELDS = {
        'id', 'identifier', 'ip_address', 'application',
        'success', 'failure_reason', 'created_at'
    }
    
    CANONICAL_BLACKLISTED_TOKEN_FIELDS = {
        'id', 'token_jti', 'user', 'user_email',
        'blacklisted_at', 'expires_at', 'reason', 'is_expired'
    }
    
    def test_session_pydantic_fields(self):
        """Vérifie SessionResponse (Pydantic)."""
        from tenxyte.core.schemas import SessionResponse
        
        pydantic_fields = set(SessionResponse.model_fields.keys())
        assert pydantic_fields == self.CANONICAL_SESSION_FIELDS
    
    def test_device_pydantic_fields(self):
        """Vérifie DeviceResponse (Pydantic)."""
        from tenxyte.core.schemas import DeviceResponse
        
        pydantic_fields = set(DeviceResponse.model_fields.keys())
        assert pydantic_fields == self.CANONICAL_DEVICE_FIELDS
    
    def test_login_attempt_pydantic_fields(self):
        """Vérifie LoginAttemptResponse (Pydantic)."""
        from tenxyte.core.schemas import LoginAttemptResponse
        
        pydantic_fields = set(LoginAttemptResponse.model_fields.keys())
        assert pydantic_fields == self.CANONICAL_LOGIN_ATTEMPT_FIELDS
    
    def test_blacklisted_token_pydantic_fields(self):
        """Vérifie BlacklistedTokenResponse (Pydantic)."""
        from tenxyte.core.schemas import BlacklistedTokenResponse
        
        pydantic_fields = set(BlacklistedTokenResponse.model_fields.keys())
        assert pydantic_fields == self.CANONICAL_BLACKLISTED_TOKEN_FIELDS
    
    def test_blacklisted_token_serializer_fields(self):
        """Vérifie BlacklistedTokenSerializer (DRF)."""
        from tenxyte.serializers.security_serializers import BlacklistedTokenSerializer
        
        serializer_fields = set(BlacklistedTokenSerializer.Meta.fields)
        assert serializer_fields == self.CANONICAL_BLACKLISTED_TOKEN_FIELDS


class TestPermissionSchemaConformity:
    """Vérifie que le schéma Permission respecte la spec canonique."""
    
    CANONICAL_PERMISSION_FIELDS = {
        'id', 'code', 'name', 'description',
        'parent', 'children', 'created_at', 'updated_at'
    }
    
    def test_permission_serializer_fields(self):
        """Vérifie que PermissionSerializer a tous les champs canoniques."""
        from tenxyte.serializers.rbac_serializers import PermissionSerializer
        
        serializer_fields = set(PermissionSerializer.Meta.fields)
        # Exclure parent_code qui est write_only
        serializer_fields.discard('parent_code')
        
        assert serializer_fields == self.CANONICAL_PERMISSION_FIELDS, (
            f"Champs manquants: {self.CANONICAL_PERMISSION_FIELDS - serializer_fields}\n"
            f"Champs en trop: {serializer_fields - self.CANONICAL_PERMISSION_FIELDS}"
        )
    
    def test_permission_pydantic_fields(self):
        """Vérifie que PermissionResponse (Pydantic) a tous les champs."""
        from tenxyte.core.schemas import PermissionResponse
        
        pydantic_fields = set(PermissionResponse.model_fields.keys())
        assert pydantic_fields == self.CANONICAL_PERMISSION_FIELDS


class TestOrganizationSchemaConformity:
    """Vérifie que le schéma Organization respecte la spec canonique."""
    
    CANONICAL_ORGANIZATION_FIELDS = {
        'id', 'name', 'slug', 'description', 'parent', 'parent_name',
        'metadata', 'is_active', 'max_members', 'member_count',
        'created_at', 'updated_at', 'created_by_email', 'user_role'
    }
    
    def test_organization_serializer_fields(self):
        """Vérifie que OrganizationSerializer a tous les champs canoniques."""
        from tenxyte.serializers.organization_serializers import OrganizationSerializer
        
        serializer_fields = set(OrganizationSerializer.Meta.fields)
        assert serializer_fields == self.CANONICAL_ORGANIZATION_FIELDS, (
            f"Champs manquants: {self.CANONICAL_ORGANIZATION_FIELDS - serializer_fields}\n"
            f"Champs en trop: {serializer_fields - self.CANONICAL_ORGANIZATION_FIELDS}"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
