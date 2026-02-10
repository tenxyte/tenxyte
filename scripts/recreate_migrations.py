"""
Script pour recréer les migrations compatibles avec toutes les bases de données.

Usage:
    python scripts/recreate_migrations.py
"""

import os
import shutil
from pathlib import Path

# Chemins
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = PACKAGE_ROOT / "src" / "tenxyte" / "migrations"

print("🗑️  Suppression des anciennes migrations...")

# Supprimer toutes les migrations sauf __init__.py
for file in MIGRATIONS_DIR.glob("*.py"):
    if file.name != "__init__.py":
        print(f"   Suppression : {file.name}")
        file.unlink()

print("\n✅ Migrations supprimées.")
print("\n📝 Prochaines étapes :")
print("\n1. Configurer la base de données dans votre projet de test (settings.py)")
print("   - SQLite (par défaut)")
print("   - PostgreSQL")
print("   - MySQL")
print("   - MongoDB (avec django-mongodb-backend)")
print("\n2. Exécuter dans votre projet de test :")
print("   python manage.py makemigrations tenxyte")
print("\n3. Les nouvelles migrations seront compatibles avec la DB choisie")
print("\n4. Tester avec :")
print("   python manage.py migrate")
