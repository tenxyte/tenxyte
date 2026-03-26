#!/usr/bin/env python3
"""
Script de validation de la spécification canonique.

Vérifie que tous les schémas (Pydantic et DRF) sont alignés avec
la spécification canonique définie dans docs/en/schemas.md.

Usage:
    python scripts/validate_canonical_spec.py
    
Exit codes:
    0 - Tous les tests passent
    1 - Au moins un test échoue
"""

import sys
import os
from typing import Set, Dict, List, Tuple

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ---------- Django bootstrap (required for DRF serializer / pagination imports) ----------
# If DJANGO_SETTINGS_MODULE is already set (e.g. by the CI workflow), use it.
# Otherwise, configure minimal settings inline so the script works standalone.
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    import django
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            SECRET_KEY='validation-script-only',  # gitleaks:allow
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'rest_framework',
                'tenxyte',
            ],
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            AUTH_USER_MODEL='tenxyte.User',
            REST_FRAMEWORK={
                'DEFAULT_AUTHENTICATION_CLASSES': [
                    'tenxyte.authentication.JWTAuthentication',
                ],
            },
            USE_TZ=True,
        )
    django.setup()
else:
    import django
    django.setup()


class Colors:
    """Codes ANSI pour la colorisation de la sortie."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class CanonicalSpecValidator:
    """Validateur de conformité à la spécification canonique."""
    
    # Définition des schémas canoniques
    CANONICAL_SCHEMAS = {
        'User': {
            'id', 'email', 'username', 'phone', 'avatar', 'bio',
            'timezone', 'language', 'first_name', 'last_name',
            'is_active', 'is_email_verified', 'is_phone_verified',
            'is_2fa_enabled', 'created_at', 'updated_at', 'last_login',
            'custom_fields', 'preferences', 'roles', 'permissions'
        },
        'TokenPair': {
            'access_token', 'refresh_token', 'token_type',
            'expires_in', 'refresh_expires_in', 'device_summary'
        },
        'ErrorResponse': {
            'error', 'code', 'details'
        },
        'PaginatedResponse': {
            'count', 'page', 'page_size', 'total_pages',
            'next', 'previous', 'results'
        },
        'Role': {
            'id', 'code', 'name', 'description', 'permissions',
            'is_default', 'created_at', 'updated_at'
        },
        'Permission': {
            'id', 'code', 'name', 'description',
            'parent', 'children', 'created_at', 'updated_at'
        },
        'AuditLog': {
            'id', 'user', 'user_email', 'action', 'ip_address',
            'user_agent', 'application', 'application_name',
            'details', 'created_at'
        },
        'Organization': {
            'id', 'name', 'slug', 'description', 'parent', 'parent_name',
            'metadata', 'is_active', 'max_members', 'member_count',
            'created_at', 'updated_at', 'created_by_email', 'user_role'
        },
        'Session': {
            'id', 'user_id', 'device_info', 'ip_address', 'user_agent',
            'is_current', 'created_at', 'last_activity', 'expires_at'
        },
        'Device': {
            'id', 'user_id', 'device_fingerprint', 'device_name',
            'device_type', 'platform', 'browser', 'is_trusted',
            'last_seen', 'created_at'
        },
        'LoginAttempt': {
            'id', 'identifier', 'ip_address', 'application',
            'success', 'failure_reason', 'created_at'
        },
        'BlacklistedToken': {
            'id', 'token_jti', 'user', 'user_email',
            'blacklisted_at', 'expires_at', 'reason', 'is_expired'
        }
    }
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
    
    def validate_pydantic_schema(self, schema_name: str, pydantic_class) -> bool:
        """Valide un schéma Pydantic contre la spec canonique."""
        canonical_fields = self.CANONICAL_SCHEMAS.get(schema_name)
        if not canonical_fields:
            self.warnings.append(f"Schéma {schema_name} non défini dans la spec canonique")
            return True
        
        try:
            pydantic_fields = set(pydantic_class.model_fields.keys())
            
            # Vérifier les champs manquants
            missing = canonical_fields - pydantic_fields
            if missing:
                self.errors.append(
                    f"Pydantic {schema_name}: Champs manquants: {missing}"
                )
                return False
            
            # Les champs supplémentaires sont autorisés pour backward compatibility
            extra = pydantic_fields - canonical_fields
            if extra:
                self.warnings.append(
                    f"Pydantic {schema_name}: Champs supplémentaires (OK pour backward compat): {extra}"
                )
            
            self.passed.append(f"Pydantic {schema_name}: ✓")
            return True
            
        except Exception as e:
            self.errors.append(f"Pydantic {schema_name}: Erreur lors de la validation: {e}")
            return False
    
    def validate_drf_serializer(self, schema_name: str, serializer_class, exclude_fields: Set[str] = set()) -> bool:
        """Valide un serializer DRF contre la spec canonique."""
        canonical_fields = self.CANONICAL_SCHEMAS.get(schema_name)
        if not canonical_fields:
            self.warnings.append(f"Schéma {schema_name} non défini dans la spec canonique")
            return True
        
        try:
            serializer_fields = set(serializer_class.Meta.fields)
            
            # Exclure les champs write_only
            if exclude_fields:
                serializer_fields -= exclude_fields
            
            # Vérifier l'égalité stricte
            if serializer_fields != canonical_fields:
                missing = canonical_fields - serializer_fields
                extra = serializer_fields - canonical_fields
                
                if missing:
                    self.errors.append(
                        f"DRF {schema_name}: Champs manquants: {missing}"
                    )
                if extra:
                    self.errors.append(
                        f"DRF {schema_name}: Champs en trop: {extra}"
                    )
                return False
            
            self.passed.append(f"DRF {schema_name}: ✓")
            return True
            
        except Exception as e:
            self.errors.append(f"DRF {schema_name}: Erreur lors de la validation: {e}")
            return False
    
    def run_all_validations(self) -> bool:
        """Exécute toutes les validations."""
        print(f"{Colors.BOLD}=== Validation de la Spécification Canonique ==={Colors.END}\n")
        
        all_passed = True
        
        # Validation Pydantic
        print(f"{Colors.BLUE}Validation des schémas Pydantic...{Colors.END}")
        try:
            from tenxyte.core.schemas import (
                UserResponse, TokenResponse, ErrorResponse, PaginatedResponse,
                RoleResponse, PermissionResponse, AuditLogEntry,
                SessionResponse, DeviceResponse, LoginAttemptResponse,
                BlacklistedTokenResponse
            )
            
            all_passed &= self.validate_pydantic_schema('User', UserResponse)
            all_passed &= self.validate_pydantic_schema('TokenPair', TokenResponse)
            all_passed &= self.validate_pydantic_schema('ErrorResponse', ErrorResponse)
            all_passed &= self.validate_pydantic_schema('PaginatedResponse', PaginatedResponse)
            all_passed &= self.validate_pydantic_schema('Role', RoleResponse)
            all_passed &= self.validate_pydantic_schema('Permission', PermissionResponse)
            all_passed &= self.validate_pydantic_schema('AuditLog', AuditLogEntry)
            all_passed &= self.validate_pydantic_schema('Session', SessionResponse)
            all_passed &= self.validate_pydantic_schema('Device', DeviceResponse)
            all_passed &= self.validate_pydantic_schema('LoginAttempt', LoginAttemptResponse)
            all_passed &= self.validate_pydantic_schema('BlacklistedToken', BlacklistedTokenResponse)
            
        except ImportError as e:
            self.errors.append(f"Impossible d'importer les schémas Pydantic: {e}")
            all_passed = False
        
        print()
        
        # Validation DRF
        print(f"{Colors.BLUE}Validation des serializers DRF...{Colors.END}")
        try:
            from tenxyte.serializers.auth_serializers import UserSerializer
            from tenxyte.serializers.rbac_serializers import RoleSerializer, PermissionSerializer
            from tenxyte.serializers.security_serializers import (
                AuditLogSerializer, BlacklistedTokenSerializer
            )
            from tenxyte.serializers.organization_serializers import OrganizationSerializer
            
            all_passed &= self.validate_drf_serializer('User', UserSerializer)
            all_passed &= self.validate_drf_serializer('Role', RoleSerializer, exclude_fields={'permission_codes'})
            all_passed &= self.validate_drf_serializer('Permission', PermissionSerializer, exclude_fields={'parent_code'})
            all_passed &= self.validate_drf_serializer('AuditLog', AuditLogSerializer)
            all_passed &= self.validate_drf_serializer('BlacklistedToken', BlacklistedTokenSerializer)
            all_passed &= self.validate_drf_serializer('Organization', OrganizationSerializer)
            
        except ImportError as e:
            self.errors.append(f"Impossible d'importer les serializers DRF: {e}")
            all_passed = False
        
        print()
        
        # Validation de la pagination
        print(f"{Colors.BLUE}Validation de la pagination...{Colors.END}")
        try:
            from tenxyte.pagination import TenxytePagination
            
            pagination = TenxytePagination()
            schema = pagination.get_paginated_response_schema({'type': 'object'})
            pagination_fields = set(schema['properties'].keys())
            
            if pagination_fields == self.CANONICAL_SCHEMAS['PaginatedResponse']:
                self.passed.append("Pagination TenxytePagination: ✓")
            else:
                missing = self.CANONICAL_SCHEMAS['PaginatedResponse'] - pagination_fields
                extra = pagination_fields - self.CANONICAL_SCHEMAS['PaginatedResponse']
                if missing:
                    self.errors.append(f"Pagination: Champs manquants: {missing}")
                if extra:
                    self.errors.append(f"Pagination: Champs en trop: {extra}")
                all_passed = False
                
        except Exception as e:
            self.errors.append(f"Erreur lors de la validation de la pagination: {e}")
            all_passed = False
        
        print()
        return all_passed
    
    def print_results(self):
        """Affiche les résultats de la validation."""
        print(f"{Colors.BOLD}=== Résultats ==={Colors.END}\n")
        
        # Tests réussis
        if self.passed:
            print(f"{Colors.GREEN}✓ Tests réussis ({len(self.passed)}):{Colors.END}")
            for msg in self.passed:
                print(f"  {Colors.GREEN}✓{Colors.END} {msg}")
            print()
        
        # Avertissements
        if self.warnings:
            print(f"{Colors.YELLOW}⚠ Avertissements ({len(self.warnings)}):{Colors.END}")
            for msg in self.warnings:
                print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")
            print()
        
        # Erreurs
        if self.errors:
            print(f"{Colors.RED}✗ Erreurs ({len(self.errors)}):{Colors.END}")
            for msg in self.errors:
                print(f"  {Colors.RED}✗{Colors.END} {msg}")
            print()
        
        # Résumé
        total_tests = len(self.passed) + len(self.errors)
        success_rate = (len(self.passed) / total_tests * 100) if total_tests > 0 else 0
        
        print(f"{Colors.BOLD}Résumé:{Colors.END}")
        print(f"  Total: {total_tests} tests")
        print(f"  Réussis: {Colors.GREEN}{len(self.passed)}{Colors.END}")
        print(f"  Échoués: {Colors.RED}{len(self.errors)}{Colors.END}")
        print(f"  Avertissements: {Colors.YELLOW}{len(self.warnings)}{Colors.END}")
        print(f"  Taux de réussite: {success_rate:.1f}%")
        print()
        
        if not self.errors:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ Spécification canonique respectée à 100%{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ Des corrections sont nécessaires{Colors.END}")


def main():
    """Point d'entrée principal."""
    validator = CanonicalSpecValidator()
    
    try:
        all_passed = validator.run_all_validations()
        validator.print_results()
        
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"{Colors.RED}Erreur fatale: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
