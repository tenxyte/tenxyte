from django.conf import settings

class AuthSettingsMixin:

    @property
    def TOTP_ISSUER(self):
        """Nom de l'émetteur TOTP affiché dans l'app authenticator."""
        return self._get('TOTP_ISSUER', 'MyApp')

    @property
    def TOTP_VALID_WINDOW(self):
        """Fenêtre de validité TOTP (nombre de périodes de 30s acceptées avant/après)."""
        return self._get('TOTP_VALID_WINDOW', 1)

    @property
    def BACKUP_CODES_COUNT(self):
        """Nombre de codes de secours générés."""
        return self._get('BACKUP_CODES_COUNT', 10)

    # =============================================
    # OTP Settings
    # =============================================

    @property
    def OTP_LENGTH(self):
        """Longueur du code OTP."""
        return self._get('OTP_LENGTH', 6)

    @property
    def OTP_EMAIL_VALIDITY(self):
        """Durée de validité OTP email en minutes."""
        return self._get('OTP_EMAIL_VALIDITY', 15)

    @property
    def OTP_PHONE_VALIDITY(self):
        """Durée de validité OTP SMS en minutes."""
        return self._get('OTP_PHONE_VALIDITY', 10)

    @property
    def OTP_MAX_ATTEMPTS(self):
        """Nombre maximum de tentatives OTP."""
        return self._get('OTP_MAX_ATTEMPTS', 5)

    # =============================================
    # SMS Backend
    # =============================================

    @property
    def PASSWORD_MIN_LENGTH(self):
        """Longueur minimale du mot de passe."""
        return self._get('PASSWORD_MIN_LENGTH', 8)

    @property
    def PASSWORD_MAX_LENGTH(self):
        """Longueur maximale du mot de passe."""
        return self._get('PASSWORD_MAX_LENGTH', 128)

    @property
    def BCRYPT_ROUNDS(self):
        """Facteur de travail (work factor) pour bcrypt."""
        return self._get('BCRYPT_ROUNDS', 12)

    @property
    def PASSWORD_REQUIRE_UPPERCASE(self):
        """Exiger au moins une majuscule."""
        return self._get('PASSWORD_REQUIRE_UPPERCASE', True)

    @property
    def PASSWORD_REQUIRE_LOWERCASE(self):
        """Exiger au moins une minuscule."""
        return self._get('PASSWORD_REQUIRE_LOWERCASE', True)

    @property
    def PASSWORD_REQUIRE_DIGIT(self):
        """Exiger au moins un chiffre."""
        return self._get('PASSWORD_REQUIRE_DIGIT', True)

    @property
    def PASSWORD_REQUIRE_SPECIAL(self):
        """Exiger au moins un caractère spécial."""
        return self._get('PASSWORD_REQUIRE_SPECIAL', True)

    @property
    def PASSWORD_HISTORY_ENABLED(self):
        """Activer/désactiver la vérification de l'historique des mots de passe."""
        return self._get('PASSWORD_HISTORY_ENABLED', True)

    @property
    def PASSWORD_HISTORY_COUNT(self):
        """Nombre d'anciens mots de passe à vérifier."""
        return self._get('PASSWORD_HISTORY_COUNT', 5)

    @property
    def SOCIAL_REQUIRE_VERIFIED_EMAIL(self):
        """Si True, refuse le login social si l'email n'est pas vérifié par le provider."""
        return self._get('SOCIAL_REQUIRE_VERIFIED_EMAIL', True)

    @property
    def AGENT_ACTION_RETENTION_DAYS(self):
        """Nombre de jours de rétention pour les actions Agent en attente (HITL)."""
        return self._get('AGENT_ACTION_RETENTION_DAYS', 7)

    @property
    def PURGE_IP_ON_DELETION(self):
        """Si True, purge l'IP des logs d'audit lors de la suppression de compte."""
        return self._get('PURGE_IP_ON_DELETION', False)

    @property
    def MAX_LOGIN_ATTEMPTS(self):
        """Nombre maximum de tentatives de login avant verrouillage."""
        return self._get('MAX_LOGIN_ATTEMPTS', 5)

    @property
    def LOCKOUT_DURATION_MINUTES(self):
        """Durée du verrouillage de compte en minutes."""
        return self._get('LOCKOUT_DURATION_MINUTES', 30)

    @property
    def ACCOUNT_LOCKOUT_ENABLED(self):
        """Activer/désactiver le verrouillage de compte après échecs."""
        return self._get('ACCOUNT_LOCKOUT_ENABLED', True)

