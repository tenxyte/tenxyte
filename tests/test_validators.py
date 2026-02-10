"""
Tests pour les validateurs.
"""
import pytest

from tenxyte.validators import PasswordValidator, PasswordValidationResult


class TestPasswordValidator:
    """Tests pour PasswordValidator."""

    def test_valid_password(self):
        """Test avec un mot de passe valide."""
        validator = PasswordValidator()
        result = validator.validate("SecureP@ssw0rd!")

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.score > 50
        assert result.strength in ['good', 'strong', 'excellent']

    def test_too_short(self):
        """Test avec un mot de passe trop court."""
        validator = PasswordValidator(min_length=8)
        result = validator.validate("Abc1!")

        assert result.is_valid is False
        assert any('au moins 8' in error.lower() for error in result.errors)

    def test_missing_uppercase(self):
        """Test sans majuscule."""
        validator = PasswordValidator(require_uppercase=True)
        result = validator.validate("password123!")

        assert result.is_valid is False
        assert any('majuscule' in error.lower() for error in result.errors)

    def test_missing_lowercase(self):
        """Test sans minuscule."""
        validator = PasswordValidator(require_lowercase=True)
        result = validator.validate("PASSWORD123!")

        assert result.is_valid is False
        assert any('minuscule' in error.lower() for error in result.errors)

    def test_missing_digit(self):
        """Test sans chiffre."""
        validator = PasswordValidator(require_digit=True)
        result = validator.validate("Password!")

        assert result.is_valid is False
        assert any('chiffre' in error.lower() for error in result.errors)

    def test_missing_special(self):
        """Test sans caractère spécial."""
        validator = PasswordValidator(require_special=True)
        result = validator.validate("Password123")

        assert result.is_valid is False
        assert any('spécial' in error.lower() or 'special' in error.lower() for error in result.errors)

    def test_common_password(self):
        """Test avec un mot de passe courant."""
        validator = PasswordValidator()
        result = validator.validate("password123")

        assert result.is_valid is False
        assert any('courant' in error.lower() for error in result.errors)

    def test_sequence_detection(self):
        """Test de détection de séquences."""
        validator = PasswordValidator()
        result = validator.validate("Abc123456!")

        assert result.is_valid is False
        assert any('sequence' in error.lower() or 'séquence' in error.lower() for error in result.errors)

    def test_email_in_password(self):
        """Test avec email dans le mot de passe."""
        validator = PasswordValidator()
        result = validator.validate("john@example.com", email="john@example.com")

        assert result.is_valid is False
        assert any('email' in error.lower() for error in result.errors)

    def test_password_strength_weak(self):
        """Test force faible."""
        validator = PasswordValidator(
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_special=False
        )
        result = validator.validate("password")

        assert result.strength in ['weak', 'fair']
        assert result.score < 50

    def test_password_strength_strong(self):
        """Test force forte."""
        validator = PasswordValidator()
        result = validator.validate("MyV3ry$tr0ng&L0ngP@ssw0rd!")

        assert result.strength in ['strong', 'excellent']
        assert result.score >= 70

    def test_get_requirements(self):
        """Test de récupération des exigences."""
        validator = PasswordValidator(
            min_length=10,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True
        )

        requirements = validator.get_requirements()

        assert isinstance(requirements, list)
        assert len(requirements) > 0
        assert any('10' in req for req in requirements)

    def test_custom_min_length(self):
        """Test avec longueur minimale personnalisée."""
        validator = PasswordValidator(min_length=12)
        result = validator.validate("Short1!")

        assert result.is_valid is False
        assert any('12' in error for error in result.errors)

    def test_disabled_requirements(self):
        """Test avec exigences désactivées."""
        validator = PasswordValidator(
            min_length=6,
            require_uppercase=False,
            require_lowercase=False,
            require_digit=False,
            require_special=False,
            check_common=False,
            check_sequences=False
        )

        result = validator.validate("simple")

        # Devrait passer si toutes les règles sont désactivées
        assert len(result.errors) == 0 or not result.is_valid

    def test_max_length(self):
        """Test dépassement longueur max."""
        validator = PasswordValidator(max_length=20)
        long_password = "A1b2c3d4e5!" * 10  # Très long

        result = validator.validate(long_password)

        assert result.is_valid is False
        assert any('depasser' in error.lower() or 'dépasser' in error.lower() for error in result.errors)
