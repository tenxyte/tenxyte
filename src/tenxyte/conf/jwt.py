from django.conf import settings

class JwtSettingsMixin:

    @property
    def JWT_SECRET_KEY(self):
        """Clé secrète pour signer les JWT.

        SECURITY: Une clé dédiée TENXYTE_JWT_SECRET_KEY est fortement recommandée.
        En production (DEBUG=False), cette clé DOIT être définie explicitement,
        sinon une ImproperlyConfigured exception est levée.
        En développement, un UserWarning de sécurité est émis.
        """
        key = getattr(settings, 'TENXYTE_JWT_SECRET_KEY', None)
        if key is None:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "TENXYTE_JWT_SECRET_KEY must be explicitly set. "
                "Do not rely on Django's SECRET_KEY for JWT signing. "
                "Generate a dedicated key: python -c \"import secrets; print(secrets.token_hex(64))\""
            )
        return key

    @property
    def JWT_ALGORITHM(self):
        """Algorithme de signature JWT."""
        return self._get('JWT_ALGORITHM', 'HS256')

    @property
    def JWT_PRIVATE_KEY(self):
        """Clé privée RSA/ECDSA pour signer les JWT (requise pour algos RS/PS/ES)."""
        return self._get('JWT_PRIVATE_KEY', None)

    @property
    def JWT_PUBLIC_KEY(self):
        """Clé publique RSA/ECDSA pour vérifier les JWT (requise pour algos RS/PS/ES)."""
        return self._get('JWT_PUBLIC_KEY', None)

    @property
    def JWT_ACCESS_TOKEN_LIFETIME(self):
        """Durée de vie du access token en secondes (défaut: 1 heure)."""
        return self._get('JWT_ACCESS_TOKEN_LIFETIME', 3600)

    @property
    def JWT_REFRESH_TOKEN_LIFETIME(self):
        """Durée de vie du refresh token en secondes (défaut: 7 jours)."""
        return self._get('JWT_REFRESH_TOKEN_LIFETIME', 86400 * 7)

    @property
    def JWT_AUTH_ENABLED(self):
        """
        Activer/désactiver l'authentification JWT.
        WARNING: Désactiver est dangereux, uniquement pour les tests.
        """
        return self._get('JWT_AUTH_ENABLED', True)

    @property
    def TOKEN_BLACKLIST_ENABLED(self):
        """Activer/désactiver le blacklisting des access tokens JWT."""
        return self._get('TOKEN_BLACKLIST_ENABLED', True)

    @property
    def REFRESH_TOKEN_ROTATION(self):
        """
        Activer/désactiver la rotation des refresh tokens.
        Si activé, l'ancien refresh token est invalidé lors du renouvellement.
        """
        return self._get('REFRESH_TOKEN_ROTATION', True)

    # =============================================
    # 2FA / TOTP Settings
    # =============================================

