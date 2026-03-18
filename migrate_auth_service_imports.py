"""
Script pour migrer automatiquement tous les imports d'AuthService
vers le nouveau module de compatibilité.

Usage:
    python migrate_auth_service_imports.py
"""

import os
import re
from pathlib import Path

# Patterns à remplacer
PATTERNS = [
    (
        r'from tenxyte\.services import AuthService',
        'from tests.integration.django.auth_service_compat import AuthService'
    ),
    (
        r'from tenxyte\.services import .*AuthService',
        'from tests.integration.django.auth_service_compat import AuthService'
    ),
]

def migrate_file(filepath):
    """Migrer un fichier de test."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    modified = False
    
    for pattern, replacement in PATTERNS:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Migrer tous les fichiers de tests."""
    test_dir = Path('tests/integration/django')
    
    if not test_dir.exists():
        print(f"❌ Dossier {test_dir} introuvable")
        return
    
    migrated_files = []
    
    # Parcourir tous les fichiers .py
    for filepath in test_dir.rglob('*.py'):
        if filepath.name == 'auth_service_compat.py':
            continue  # Skip le fichier de compatibilité lui-même
        
        if migrate_file(filepath):
            migrated_files.append(filepath)
            print(f"✅ Migré: {filepath.relative_to('tests/integration/django')}")
    
    print(f"\n📊 Résumé:")
    print(f"   {len(migrated_files)} fichiers migrés")
    
    if migrated_files:
        print(f"\n✅ Migration terminée avec succès!")
    else:
        print(f"\n⚠️  Aucun fichier à migrer")

if __name__ == '__main__':
    main()
