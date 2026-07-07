"""
Tests unitaires pour la migration 0017 (login OTP type + passwordless account).

Vérifie que la migration 0017 est purement additive :
- uniquement des AddField/AlterField (aucune suppression de champ, contrainte
  ou choix existant)
- le nouveau choix "login" pour OTPCode.otp_type est accepté par l'ORM
- les comptes existants obtiennent has_usable_password=True par défaut

Validates: Requirements 8.6
"""
import importlib

import pytest
from django.db import migrations

from tenxyte.models import User, OTPCode

# Le module de migration commence par un chiffre ("0017_..."), il n'est donc
# pas importable via une instruction `import` classique.
migration_0017 = importlib.import_module(
    "tenxyte.migrations.0017_login_otp_type_and_passwordless_account"
)


# Choix précédemment existants sur OTPCode.otp_type avant la migration 0017.
PREVIOUS_OTP_TYPE_CHOICES = [
    ("email_verification", "Email Verification"),
    ("phone_verification", "Phone Verification"),
    ("password_reset", "Password Reset"),
    ("login_2fa", "Login 2FA"),
]


class TestMigration0017IsAdditive:
    """Vérifie que la migration 0017 ne contient que des opérations additives."""

    def test_only_addfield_and_alterfield_operations(self):
        """La migration ne doit contenir que des AddField/AlterField."""
        operations = migration_0017.Migration.operations

        assert len(operations) > 0
        for operation in operations:
            assert isinstance(
                operation, (migrations.AddField, migrations.AlterField)
            ), (
                f"Opération non additive détectée : {operation!r}. "
                "Seuls AddField/AlterField sont autorisés."
            )

    def test_alterfield_on_otp_type_keeps_all_previous_choices(self):
        """L'AlterField sur otpcode.otp_type ne doit retirer aucun choix existant."""
        alter_field_ops = [
            op
            for op in migration_0017.Migration.operations
            if isinstance(op, migrations.AlterField)
            and op.model_name == "otpcode"
            and op.name == "otp_type"
        ]

        assert len(alter_field_ops) == 1
        new_choices = alter_field_ops[0].field.choices

        for previous_choice in PREVIOUS_OTP_TYPE_CHOICES:
            assert previous_choice in new_choices, (
                f"Le choix existant {previous_choice!r} a été retiré par la migration 0017."
            )

    def test_alterfield_on_otp_type_adds_login_choice(self):
        """L'AlterField sur otpcode.otp_type doit ajouter le nouveau choix 'login'."""
        alter_field_ops = [
            op
            for op in migration_0017.Migration.operations
            if isinstance(op, migrations.AlterField)
            and op.model_name == "otpcode"
            and op.name == "otp_type"
        ]

        assert len(alter_field_ops) == 1
        new_choices = alter_field_ops[0].field.choices

        assert ("login", "Login OTP") in new_choices

    def test_addfield_adds_has_usable_password_with_default_true(self):
        """L'AddField sur user.has_usable_password doit avoir default=True."""
        add_field_ops = [
            op
            for op in migration_0017.Migration.operations
            if isinstance(op, migrations.AddField)
            and op.model_name == "user"
            and op.name == "has_usable_password"
        ]

        assert len(add_field_ops) == 1
        assert add_field_ops[0].field.default is True

    def test_migration_depends_on_previous_migration(self):
        """La migration doit dépendre de 0016 (chaîne de migrations intacte)."""
        assert (
            "tenxyte",
            "0016_normalize_phone_country_code",
        ) in migration_0017.Migration.dependencies


class TestOTPCodeAcceptsLoginType:
    """Vérifie que OTPCode accepte le nouveau otp_type='login' sans erreur."""

    @pytest.mark.django_db
    def test_create_otp_with_login_type(self, user):
        """OTPCode.objects.create(..., otp_type='login') doit réussir sans erreur."""
        from django.utils import timezone
        from datetime import timedelta

        otp = OTPCode.objects.create(
            user=user,
            code=OTPCode._hash_code("123456"),
            otp_type="login",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        assert otp.otp_type == "login"

    @pytest.mark.django_db
    def test_full_clean_accepts_login_type(self, user):
        """full_clean() ne doit lever aucune ValidationError pour otp_type='login'."""
        from django.utils import timezone
        from datetime import timedelta

        otp = OTPCode(
            user=user,
            code=OTPCode._hash_code("123456"),
            otp_type="login",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        # Ne doit pas lever de ValidationError.
        otp.full_clean()


class TestExistingAccountsDefaultHasUsablePassword:
    """Vérifie que les comptes obtiennent has_usable_password=True par défaut."""

    @pytest.mark.django_db
    def test_user_created_without_has_usable_password_defaults_to_true(self):
        """Un User créé sans préciser has_usable_password doit valoir True."""
        new_user = User.objects.create_user(
            email="passwordless-default@example.com",
            password="SecurePassword123!",
        )

        assert new_user.has_usable_password is True

    @pytest.mark.django_db
    def test_existing_user_fixture_has_usable_password_true(self, user):
        """Le fixture 'user' (créé sans le champ explicite) doit valoir True."""
        assert user.has_usable_password is True
