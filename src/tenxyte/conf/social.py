from django.conf import settings

class SocialSettingsMixin:

    @property
    def SOCIAL_PROVIDERS(self):
        """
        Liste des providers OAuth2 activés.
        Options: 'google', 'github', 'microsoft', 'facebook'
        Par défaut: tous activés.
        """
        return self._get('SOCIAL_PROVIDERS', ['google', 'github', 'microsoft', 'facebook'])

    @property
    def GITHUB_CLIENT_ID(self):
        """GitHub OAuth App Client ID."""
        return getattr(settings, 'GITHUB_CLIENT_ID', '')

    @property
    def GITHUB_CLIENT_SECRET(self):
        """GitHub OAuth App Client Secret."""
        return getattr(settings, 'GITHUB_CLIENT_SECRET', '')

    @property
    def MICROSOFT_CLIENT_ID(self):
        """Microsoft Azure AD Application (client) ID."""
        return getattr(settings, 'MICROSOFT_CLIENT_ID', '')

    @property
    def MICROSOFT_CLIENT_SECRET(self):
        """Microsoft Azure AD Client Secret."""
        return getattr(settings, 'MICROSOFT_CLIENT_SECRET', '')

    @property
    def FACEBOOK_APP_ID(self):
        """Facebook App ID."""
        return getattr(settings, 'FACEBOOK_APP_ID', '')

    @property
    def FACEBOOK_APP_SECRET(self):
        """Facebook App Secret."""
        return getattr(settings, 'FACEBOOK_APP_SECRET', '')

    # =============================================
    # WebAuthn / Passkeys (FIDO2)
    # =============================================

    @property
    def WEBAUTHN_ENABLED(self):
        """Activer/désactiver l'authentification par Passkeys (WebAuthn/FIDO2)."""
        return self._get('WEBAUTHN_ENABLED', False)

    @property
    def WEBAUTHN_RP_ID(self):
        """Relying Party ID — doit correspondre au domaine de l'application (ex: 'yourapp.com')."""
        return self._get('WEBAUTHN_RP_ID', 'localhost')

    @property
    def WEBAUTHN_RP_NAME(self):
        """Nom affiché dans le prompt Passkey du navigateur."""
        return self._get('WEBAUTHN_RP_NAME', 'Tenxyte')

    @property
    def WEBAUTHN_CHALLENGE_EXPIRY_SECONDS(self):
        """Durée de validité du challenge WebAuthn en secondes."""
        return self._get('WEBAUTHN_CHALLENGE_EXPIRY_SECONDS', 300)

    # =============================================
    # Breach Password Check (HaveIBeenPwned)
    # =============================================

    @property
    def MAGIC_LINK_ENABLED(self):
        """Activer/désactiver l'authentification par magic link (sans mot de passe)."""
        return self._get('MAGIC_LINK_ENABLED', False)

    @property
    def MAGIC_LINK_EXPIRY_MINUTES(self):
        """Durée de validité du magic link en minutes."""
        return self._get('MAGIC_LINK_EXPIRY_MINUTES', 15)

    @property
    def MAGIC_LINK_BASE_URL(self):
        """URL de base utilisée pour construire le lien de vérification."""
        return self._get('MAGIC_LINK_BASE_URL', 'https://yourapp.com')

    # =============================================
    # Simple Throttle Rules
    # =============================================

    @property
    def GOOGLE_CLIENT_ID(self):
        """Google OAuth Client ID."""
        return getattr(settings, 'GOOGLE_CLIENT_ID', '')

    @property
    def GOOGLE_CLIENT_SECRET(self):
        """Google OAuth Client Secret."""
        return getattr(settings, 'GOOGLE_CLIENT_SECRET', '')

    # =============================================
    # Organizations Settings
    # =============================================

