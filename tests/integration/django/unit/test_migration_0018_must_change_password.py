"""
Tests unitaires pour la migration 0018 (must_change_password).

Vérifie que la migration 0018 est purement additive :
- uniquement un AddField (aucune suppression de champ, contrainte ou choix existant)
- dépend de 0017_login_otp_type_and_passwordless_account
- le nouveau champ must_change_password vaut False par défaut
- le champ est indépendant de has_usable_password (les quatre combinaisons sont représentables)

Feature: force_password_change_on_first_login
Validates: Requirements 1.1, 1.2, 1.3, 1.5, 7.4
"""
import importlib

import pytest
from django.db import migrations

from tenxyte.models import User

migration_0018 = importlib.import_module("tenxyte.migrations.0018_user_must_change_password")


class TestMigration0018IsAdditive:
    """Vérifie que la migration 0018 ne contient que des opérations additives."""

    def test_only_addfield_operations(self):
        """La migration ne doit contenir que des AddField."""
        operations = migration_0018.Migration.operations
        assert len(operations) > 0
        for operation in operations:
            assert isinstance(operation, migrations.AddField), (
                f"Opération non additive détectée : {operation!r}. "
                "Seul AddField est autorisé dans cette migration."
            )

    def test_no_removefield_operations(self):
        """La migration ne doit contenir aucun RemoveField."""
        operations = migration_0018.Migration.operations
        for operation in operations:
            assert not isinstance(operation, migrations.RemoveField), (
                f"RemoveField détecté : {operation!r}. Cette migration doit être purement additive."
            )

    def test_addfield_adds_must_change_password_with_default_false(self):
        """L'AddField sur user.must_change_password doit avoir default=False."""
        add_field_ops = [
            op
            for op in migration_0018.Migration.operations
            if isinstance(op, migrations.AddField)
            and op.model_name == "user"
            and op.name == "must_change_password"
        ]
        assert len(add_field_ops) == 1
        assert add_field_ops[0].field.default is False

    def test_migration_depends_on_0017(self):
        """La migration doit dépendre de 0017 (chaîne de migrations intacte)."""
        assert (
            "tenxyte",
            "0017_login_otp_type_and_passwordless_account",
        ) in migration_0018.Migration.dependencies


class TestMustChangePasswordDefaultValue:
    """Vérifie que must_change_password vaut False par défaut."""

    @pytest.mark.django_db
    def test_user_created_without_flag_defaults_to_false(self):
        """Un User créé sans préciser must_change_password doit valoir False."""
        user = User.objects.create_user(
            email="no-flag@example.com",
            password="SecurePassword123!",
        )
        assert user.must_change_password is False

    @pytest.mark.django_db
    def test_user_created_with_flag_true(self):
        """Un User créé avec must_change_password=True doit conserver True."""
        user = User.objects.create_user(
            email="forced@example.com",
            password="SecurePassword123!",
            must_change_password=True,
        )
        assert user.must_change_password is True

    @pytest.mark.django_db
    def test_flag_can_be_toggled(self):
        """Le flag doit pouvoir être basculé de False à True et retour."""
        user = User.objects.create_user(
            email="toggle@example.com",
            password="SecurePassword123!",
        )
        assert user.must_change_password is False

        user.must_change_password = True
        user.save(update_fields=["must_change_password"])
        user.refresh_from_db()
        assert user.must_change_password is True

        user.must_change_password = False
        user.save(update_fields=["must_change_password"])
        user.refresh_from_db()
        assert user.must_change_password is False


class TestMustChangePasswordIndependentFromHasUsablePassword:
    """Vérifie que must_change_password est indépendant de has_usable_password."""

    @pytest.mark.django_db
    def test_all_four_combinations_are_representable(self):
        """Les quatre combinaisons (has_usable_password, must_change_password) doivent être possibles."""
        combinations = [
            (True, False),   # compte normal
            (True, True),    # compte avec mot de passe temporaire
            (False, False),  # Passwordless_Account normal
            (False, True),   # Passwordless_Account invité
        ]
        for i, (has_usable, must_change) in enumerate(combinations):
            user = User.objects.create_user(
                email=f"combo-{i}@example.com",
                password="SecurePassword123!",
                has_usable_password=has_usable,
                must_change_password=must_change,
            )
            user.refresh_from_db()
            assert user.has_usable_password is has_usable, (
                f"Combinaison {i}: has_usable_password attendu {has_usable}, obtenu {user.has_usable_password}"
            )
            assert user.must_change_password is must_change, (
                f"Combinaison {i}: must_change_password attendu {must_change}, obtenu {user.must_change_password}"
            )
