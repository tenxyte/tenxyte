from django.conf import settings


class JwtSettingsMixin:

    @property
    def JWT_SECRET_KEY(self):
        """Clé secrète pour signer les JWT.

        SECURITY: Une clé dédiée TENXYTE_JWT_SECRET_KEY est fortement recommandée.
        En production (DEBUG=False), cette clé DOIT être définie explicitement,
        sinon une ImproperlyConfigured exception est levée.
        En développement (DEBUG=True), une clé éphémère est auto-générée avec un warning.
        """
        key = getattr(settings, "TENXYTE_JWT_SECRET_KEY", None)
        if key is None:
            # In DEBUG mode, auto-generate an ephemeral key (invalidated on restart)
            if getattr(settings, "DEBUG", False):
                if not hasattr(self, "_dev_jwt_key"):
                    import secrets
                    import warnings

                    self._dev_jwt_key = secrets.token_hex(64)
                    warnings.warn(
                        "TENXYTE_JWT_SECRET_KEY is not set. Using auto-generated ephemeral key "
                        "(tokens will be invalidated on server restart). "
                        "Set TENXYTE_JWT_SECRET_KEY for persistent tokens.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                return self._dev_jwt_key
            from django.core.exceptions import ImproperlyConfigured

            raise ImproperlyConfigured(
                "TENXYTE_JWT_SECRET_KEY must be explicitly set. "
                "Do not rely on Django's SECRET_KEY for JWT signing. "
                'Generate a dedicated key: python -c "import secrets; print(secrets.token_hex(64))"'
            )
        return key

    @property
    def JWT_ALGORITHM(self):
        """Algorithme de signature JWT."""
        return self._get("JWT_ALGORITHM", "HS256")

    @property
    def JWT_PRIVATE_KEY(self):
        """Clé privée RSA/ECDSA pour signer les JWT (requise pour algos RS/PS/ES)."""
        return self._get("JWT_PRIVATE_KEY", None)

    @property
    def JWT_PUBLIC_KEY(self):
        """Clé publique RSA/ECDSA pour vérifier les JWT (requise pour algos RS/PS/ES)."""
        return self._get("JWT_PUBLIC_KEY", None)

    @property
    def JWT_ACCESS_TOKEN_LIFETIME(self):
        """Durée de vie du access token en secondes (défaut: 15 minutes)."""
        return self._get("JWT_ACCESS_TOKEN_LIFETIME", 900)

    @property
    def JWT_REFRESH_TOKEN_LIFETIME(self):
        """Durée de vie du refresh token en secondes (défaut: 7 jours)."""
        return self._get("JWT_REFRESH_TOKEN_LIFETIME", 86400 * 7)

    @property
    def JWT_AUTH_ENABLED(self):
        """
        Activer/désactiver l'authentification JWT.
        WARNING: Désactiver est dangereux, uniquement pour les tests.
        """
        return self._get("JWT_AUTH_ENABLED", True)

    @property
    def TOKEN_BLACKLIST_ENABLED(self):
        """Activer/désactiver le blacklisting des access tokens JWT."""
        return self._get("TOKEN_BLACKLIST_ENABLED", True)

    @property
    def REFRESH_TOKEN_ROTATION(self):
        """
        Activer/désactiver la rotation des refresh tokens.
        Si activé, l'ancien refresh token est invalidé lors du renouvellement.
        """
        return self._get("REFRESH_TOKEN_ROTATION", True)

    @property
    def JWT_PREVIOUS_SECRET_KEY(self):
        """Ancienne clé secrète JWT pour validation pendant la rotation de clés."""
        return self._get("JWT_PREVIOUS_SECRET_KEY", None)

    @property
    def JWT_PREVIOUS_PUBLIC_KEY(self):
        """Ancienne clé publique JWT pour validation pendant la rotation (RS256)."""
        return self._get("JWT_PREVIOUS_PUBLIC_KEY", None)

    # =============================================
    # 2FA / TOTP Settings
    # =============================================
