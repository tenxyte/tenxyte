"""
Schema invariance test — this phase (z_aud_1) adds no field, model, or migration.

Spec: specs/z_aud_1 (Phase 1 "Crédibilité"), Requirement 8.1, design.md "Property 11".
"""

from pathlib import Path

import pytest
from django.core.management import call_command

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "src" / "tenxyte" / "migrations"

# Frozen at the start of this phase (v0.9.6.4.2) and expected to still hold at its end (v1.0.0):
# Apple Sign-In reuses the existing free-text `provider` field on SocialConnection, and every other
# deliverable in this phase is documentation/packaging/CI — no schema change anywhere.
#
# 0019_rename_users_edit_permission (specs/z_aud_0000) is a data-only migration (RunPython
# renaming a Permission row's `code`, no AddField/CreateModel/AlterField) — it does not affect
# the schema this property actually guards, so the count below was bumped to include it.
EXPECTED_MIGRATION_COUNT = 26


def test_migration_count_unchanged():
    """Feature: z_aud_1, Property 11: Invariance du schéma de données (nombre de migrations)."""
    migration_files = [
        f for f in _MIGRATIONS_DIR.glob("*.py") if f.name != "__init__.py" and not f.name.startswith("_")
    ]
    assert len(migration_files) == EXPECTED_MIGRATION_COUNT, (
        f"Expected {EXPECTED_MIGRATION_COUNT} migration files, found {len(migration_files)}: "
        f"{sorted(f.name for f in migration_files)}. This phase should introduce zero schema change."
    )


@pytest.mark.django_db
def test_no_pending_makemigrations():
    """Feature: z_aud_1, Property 11: Invariance du schéma de données (zéro makemigrations en attente)."""
    # Raises CommandError if Django detects any model change not yet captured by a migration.
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)
