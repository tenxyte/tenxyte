#!/usr/bin/env python
"""
Script de migration automatique des imports legacy dans les tests.
Remplace les imports des services supprimés par le helper test.
"""
import os
import re
from pathlib import Path

# Patterns de remplacement
REPLACEMENTS = [
    # Import JWTService legacy -> helper
    (
        r'from tenxyte\.services\.jwt_service import JWTService\s*\n\s*return JWTService\(\)\.generate_token_pair\(',
        'from tests.integration.django.test_helpers import create_jwt_token\n    return create_jwt_token('
    ),
    (
        r'from tenxyte\.services\.jwt_service import JWTService\s*\n\s*token = JWTService\(\)\.generate_token_pair\(',
        'from tests.integration.django.test_helpers import create_jwt_token\n    token_pair = create_jwt_token('
    ),
    (
        r'from tenxyte\.services import JWTService',
        'from tests.integration.django.test_helpers import get_jwt_service as JWTService'
    ),
    (
        r'from tenxyte\.services\.jwt_service import JWTService',
        'from tests.integration.django.test_helpers import get_jwt_service\n# JWTService = get_jwt_service  # Use get_jwt_service() instead'
    ),
    
    # Import TOTPService legacy -> core
    (
        r'from tenxyte\.services import TOTPService',
        'from tenxyte.core.totp_service import TOTPService'
    ),
    (
        r'from tenxyte\.services\.totp_service import TOTPService',
        'from tenxyte.core.totp_service import TOTPService'
    ),
    
    # Import MagicLinkService legacy -> core
    (
        r'from tenxyte\.services\.magic_link_service import MagicLinkService',
        'from tenxyte.core.magic_link_service import MagicLinkService'
    ),
    
    # Import WebAuthnService legacy -> core
    (
        r'from tenxyte\.services\.webauthn_service import WebAuthnService',
        'from tenxyte.core.webauthn_service import WebAuthnService'
    ),
    
    # Import EmailService legacy -> adapter
    (
        r'from tenxyte\.services\.email_service import EmailService',
        'from tenxyte.adapters.django.email_service import DjangoEmailService as EmailService'
    ),
    
    # Import AuthService legacy -> commentaire
    (
        r'from tenxyte\.services\.auth_service import AuthService',
        '# AuthService removed - use core services instead\n# from tenxyte.core.jwt_service import JWTService'
    ),
]

def migrate_file(filepath):
    """Migre un fichier de test."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Appliquer tous les remplacements
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    
    # Sauvegarder si modifié
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Migre tous les fichiers de test."""
    test_dir = Path('tests/integration/django')
    
    if not test_dir.exists():
        print(f"❌ Directory not found: {test_dir}")
        return
    
    modified_count = 0
    total_count = 0
    
    # Parcourir tous les fichiers Python
    for filepath in test_dir.rglob('*.py'):
        total_count += 1
        if migrate_file(filepath):
            modified_count += 1
            print(f"✅ Migrated: {filepath}")
    
    print(f"\n📊 Summary:")
    print(f"   Total files: {total_count}")
    print(f"   Modified: {modified_count}")
    print(f"   Unchanged: {total_count - modified_count}")

if __name__ == '__main__':
    main()
