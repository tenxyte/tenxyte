"""
Validateurs pour l'authentification.

Validation robuste des mots de passe avec:
- Longueur minimale
- Complexite (majuscules, minuscules, chiffres, symboles)
- Detection des mots de passe courants
- Messages d'erreur explicites
"""

import re
from typing import Tuple, List, Optional
from dataclasses import dataclass

from .conf import auth_settings


@dataclass
class PasswordValidationResult:
    """Resultat de la validation d'un mot de passe."""

    is_valid: bool
    errors: List[str]
    score: int  # 0-100, force du mot de passe
    strength: str  # 'weak', 'fair', 'good', 'strong', 'excellent'


class PasswordValidator:
    """
    Validateur de mot de passe configurable.

    Usage:
        validator = PasswordValidator()
        result = validator.validate("MonMotDePasse123!")
        if not result.is_valid:
            print(result.errors)
    """

    # Mots de passe courants a rejeter (top 100 + variations)
    COMMON_PASSWORDS = {
        "password",
        "password1",
        "password123",
        "password1234",
        "123456",
        "1234567",
        "12345678",
        "123456789",
        "1234567890",
        "qwerty",
        "qwerty123",
        "azerty",
        "azerty123",
        "abc123",
        "abc1234",
        "abcdef",
        "abcd1234",
        "admin",
        "admin123",
        "administrator",
        "root",
        "root123",
        "user",
        "user123",
        "guest",
        "guest123",
        "login",
        "login123",
        "welcome",
        "welcome1",
        "welcome123",
        "letmein",
        "monkey",
        "dragon",
        "master",
        "shadow",
        "sunshine",
        "princess",
        "football",
        "baseball",
        "soccer",
        "iloveyou",
        "trustno1",
        "superman",
        "batman",
        "starwars",
        "passw0rd",
        "p@ssword",
        "p@ssw0rd",
        "pass1234",
        "test",
        "test123",
        "test1234",
        "testing",
        "demo",
        "demo123",
        "secret",
        "secret123",
        "private",
        "access",
        "changeme",
        "temp",
        "temp123",
        "temporary",
        "hello",
        "hello123",
        "bonjour",
        "salut",
        "111111",
        "000000",
        "666666",
        "888888",
        "999999",
        "aaaaaa",
        "qqqqqq",
        "zzzzzz",
        "motdepasse",
        "soleil",
        "amour",
        "france",
    }

    # Sequences a eviter
    SEQUENCES = [
        "0123456789",
        "9876543210",
        "abcdefghijklmnopqrstuvwxyz",
        "zyxwvutsrqponmlkjihgfedcba",
        "azertyuiop",
        "qwertyuiop",
        "poiuytreza",
    ]

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        require_uppercase: Optional[bool] = None,
        require_lowercase: Optional[bool] = None,
        require_digit: Optional[bool] = None,
        require_special: Optional[bool] = None,
        min_unique_chars: int = 5,
        check_common: bool = True,
        check_sequences: bool = True,
    ):
        # Utiliser conf.py comme valeurs par défaut
        self.min_length = min_length if min_length is not None else auth_settings.PASSWORD_MIN_LENGTH
        self.max_length = max_length if max_length is not None else auth_settings.PASSWORD_MAX_LENGTH
        self.require_uppercase = (
            require_uppercase if require_uppercase is not None else auth_settings.PASSWORD_REQUIRE_UPPERCASE
        )
        self.require_lowercase = (
            require_lowercase if require_lowercase is not None else auth_settings.PASSWORD_REQUIRE_LOWERCASE
        )
        self.require_digit = require_digit if require_digit is not None else auth_settings.PASSWORD_REQUIRE_DIGIT
        self.require_special = (
            require_special if require_special is not None else auth_settings.PASSWORD_REQUIRE_SPECIAL
        )
        self.min_unique_chars = min_unique_chars
        self.check_common = check_common
        self.check_sequences = check_sequences

    def validate(
        self, password: str, email: str = None, username: str = None, has_mfa: bool = False
    ) -> PasswordValidationResult:
        """
        Valide un mot de passe et retourne un resultat detaille.

        Args:
            password: Le mot de passe a valider
            email: Email de l'utilisateur (optionnel, pour eviter inclusion)
            username: Nom d'utilisateur (optionnel, pour eviter inclusion)

        Returns:
            PasswordValidationResult avec is_valid, errors, score et strength
        """
        errors = []
        score = 0

        if not password:
            return PasswordValidationResult(
                is_valid=False, errors=["Le mot de passe est requis"], score=0, strength="weak"
            )

        # === Longueur ===
        effective_min = self.min_length
        if not has_mfa:
            no_mfa_min = getattr(auth_settings, "PASSWORD_MIN_LENGTH_NO_MFA", None)
            if no_mfa_min and no_mfa_min > effective_min:
                effective_min = no_mfa_min

        if len(password) < effective_min:
            if not has_mfa and effective_min > self.min_length:
                errors.append(
                    f"Le mot de passe doit contenir au moins {effective_min} caractères "
                    f"(sans MFA actif; {self.min_length} avec MFA)"
                )
            else:
                errors.append(f"Le mot de passe doit contenir au moins {effective_min} caracteres")
        elif len(password) >= self.min_length:
            score += 20
            if len(password) >= 12:
                score += 10
            if len(password) >= 16:
                score += 10

        if len(password) > self.max_length:
            errors.append(f"Le mot de passe ne doit pas depasser {self.max_length} caracteres")

        # === Complexite ===
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_digit = bool(re.search(r"[0-9]", password))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', password))

        if self.require_uppercase and not has_upper:
            errors.append("Le mot de passe doit contenir au moins une lettre majuscule")
        elif has_upper:
            score += 10

        if self.require_lowercase and not has_lower:
            errors.append("Le mot de passe doit contenir au moins une lettre minuscule")
        elif has_lower:
            score += 10

        if self.require_digit and not has_digit:
            errors.append("Le mot de passe doit contenir au moins un chiffre")
        elif has_digit:
            score += 10

        if self.require_special and not has_special:
            errors.append("Le mot de passe doit contenir au moins un caractere special (!@#$%^&*...)")
        elif has_special:
            score += 15

        # === Caracteres uniques ===
        unique_chars = len(set(password.lower()))
        if unique_chars < self.min_unique_chars:
            errors.append(f"Le mot de passe doit contenir au moins {self.min_unique_chars} caracteres differents")
        elif unique_chars >= 8:
            score += 10

        # === Mots de passe courants ===
        if self.check_common:
            password_lower = password.lower()
            if password_lower in self.COMMON_PASSWORDS:
                errors.append("Ce mot de passe est trop courant et facile a deviner")
                score = max(0, score - 30)

        # === Sequences ===
        if self.check_sequences:
            password_lower = password.lower()
            for seq in self.SEQUENCES:
                # Chercher des sequences de 4+ caracteres
                for i in range(len(seq) - 3):
                    if seq[i : i + 4] in password_lower:
                        errors.append("Le mot de passe contient une sequence previsible (ex: 1234, abcd)")
                        score = max(0, score - 20)
                        break
                else:
                    continue
                break

        # === Inclusion email/username ===
        if email:
            email_local = email.split("@")[0].lower()
            if len(email_local) >= 3 and email_local in password.lower():
                errors.append("Le mot de passe ne doit pas contenir votre adresse email")
                score = max(0, score - 15)

        if username:
            if len(username) >= 3 and username.lower() in password.lower():
                errors.append("Le mot de passe ne doit pas contenir votre nom d'utilisateur")
                score = max(0, score - 15)

        # === Repetitions ===
        if re.search(r"(.)\1{3,}", password):
            errors.append("Le mot de passe ne doit pas contenir plus de 3 caracteres identiques consecutifs")
            score = max(0, score - 10)

        # === Score final ===
        score = max(0, min(100, score))

        # Determiner la force
        if score < 30:
            strength = "weak"
        elif score < 50:
            strength = "fair"
        elif score < 70:
            strength = "good"
        elif score < 90:
            strength = "strong"
        else:
            strength = "excellent"

        return PasswordValidationResult(is_valid=len(errors) == 0, errors=errors, score=score, strength=strength)

    def get_requirements(self) -> List[str]:
        """Retourne la liste des exigences pour affichage."""
        requirements = [
            f"Au moins {self.min_length} caracteres",
        ]

        if self.require_uppercase:
            requirements.append("Au moins une lettre majuscule (A-Z)")
        if self.require_lowercase:
            requirements.append("Au moins une lettre minuscule (a-z)")
        if self.require_digit:
            requirements.append("Au moins un chiffre (0-9)")
        if self.require_special:
            requirements.append("Au moins un caractere special (!@#$%^&*...)")
        if self.min_unique_chars > 1:
            requirements.append(f"Au moins {self.min_unique_chars} caracteres differents")

        return requirements


# Instance par defaut avec configuration standard
password_validator = PasswordValidator()


def validate_password(password: str, email: str = None, username: str = None) -> Tuple[bool, List[str]]:
    """
    Fonction helper pour valider un mot de passe.

    Returns:
        Tuple (is_valid, errors)
    """
    result = password_validator.validate(password, email, username)
    return result.is_valid, result.errors


def get_password_strength(password: str) -> dict:
    """
    Retourne la force d'un mot de passe.

    Returns:
        Dict avec score (0-100) et strength (weak/fair/good/strong/excellent)
    """
    result = password_validator.validate(password)
    return {"score": result.score, "strength": result.strength, "is_valid": result.is_valid}
