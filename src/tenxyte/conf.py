"""
Configuration settings pour Tenxyte.

Toutes les settings sont préfixées par TENXYTE_ pour éviter les conflits.
Des valeurs par défaut raisonnables sont fournies pour tous les paramètres.

Ordre de priorité (du plus fort au plus faible) :
    1. settings.py du projet (TENXYTE_<NOM> explicite)
    2. TENXYTE_SHORTCUT_SECURE_MODE preset (starter / medium / robust)
    3. Défaut conf.py

Usage:
    from tenxyte.conf import auth_settings

    secret = auth_settings.JWT_SECRET_KEY
    if auth_settings.RATE_LIMITING_ENABLED:
        ...
"""

from django.conf import settings


# =============================================================================
# Presets TENXYTE_SHORTCUT_SECURE_MODE
#
# Chaque preset définit un ensemble de valeurs pour les settings les plus
# importants. L'utilisateur peut toujours surcharger individuellement chaque
# setting dans son settings.py — cela prend la priorité sur le preset.
#
# Settings intentionnellement ABSENTS des presets (toujours manuels) :
#   - JWT_SECRET_KEY, GOOGLE_CLIENT_ID/SECRET, GITHUB_CLIENT_ID/SECRET,
#     MICROSOFT_CLIENT_ID/SECRET, FACEBOOK_APP_ID/SECRET,
#     TWILIO_*, NGH_*, SENDGRID_*, WEBAUTHN_RP_ID, WEBAUTHN_RP_NAME,
#     MAGIC_LINK_BASE_URL, CORS_ALLOWED_ORIGINS
# =============================================================================

SECURE_MODE_PRESETS = {
    # -------------------------------------------------------------------------
    # starter — Démarrage rapide, sécurité de base
    # Idéal pour : prototypes, projets internes, MVP, développement local
    # -------------------------------------------------------------------------
    'starter': {
        'JWT_ACCESS_TOKEN_LIFETIME':    3600,        # 1 heure
        'JWT_REFRESH_TOKEN_LIFETIME':   86400 * 30,  # 30 jours
        'REFRESH_TOKEN_ROTATION':       False,
        'TOKEN_BLACKLIST_ENABLED':      True,
        'ACCOUNT_LOCKOUT_ENABLED':      True,
        'MAX_LOGIN_ATTEMPTS':           10,
        'LOCKOUT_DURATION_MINUTES':     15,
        'RATE_LIMITING_ENABLED':        True,
        'PASSWORD_HISTORY_ENABLED':     False,
        'PASSWORD_HISTORY_COUNT':       0,
        'BREACH_CHECK_ENABLED':         False,
        'BREACH_CHECK_REJECT':          False,
        'MAGIC_LINK_ENABLED':           False,
        'WEBAUTHN_ENABLED':             False,
        'AUDIT_LOGGING_ENABLED':        False,
        'DEVICE_LIMIT_ENABLED':         False,
        'SESSION_LIMIT_ENABLED':        False,
        'CORS_ALLOW_ALL_ORIGINS':       True,
        'SECURITY_HEADERS_ENABLED':     False,
    },

    # -------------------------------------------------------------------------
    # medium — Production standard, équilibre UX / sécurité
    # Idéal pour : SaaS B2C, apps publiques, startups en croissance
    # -------------------------------------------------------------------------
    'medium': {
        'JWT_ACCESS_TOKEN_LIFETIME':    900,         # 15 minutes
        'JWT_REFRESH_TOKEN_LIFETIME':   86400 * 7,   # 7 jours
        'REFRESH_TOKEN_ROTATION':       True,
        'TOKEN_BLACKLIST_ENABLED':      True,
        'ACCOUNT_LOCKOUT_ENABLED':      True,
        'MAX_LOGIN_ATTEMPTS':           5,
        'LOCKOUT_DURATION_MINUTES':     30,
        'RATE_LIMITING_ENABLED':        True,
        'PASSWORD_HISTORY_ENABLED':     True,
        'PASSWORD_HISTORY_COUNT':       5,
        'BREACH_CHECK_ENABLED':         True,
        'BREACH_CHECK_REJECT':          True,
        'MAGIC_LINK_ENABLED':           True,
        'WEBAUTHN_ENABLED':             False,
        'AUDIT_LOGGING_ENABLED':        True,
        'DEVICE_LIMIT_ENABLED':         True,
        'DEFAULT_MAX_DEVICES':          5,
        'SESSION_LIMIT_ENABLED':        True,
        'CORS_ALLOW_ALL_ORIGINS':       False,
        'SECURITY_HEADERS_ENABLED':     True,
    },

    # -------------------------------------------------------------------------
    # robust — Sécurité maximale, conformité enterprise
    # Idéal pour : fintech, santé, SaaS B2B, données sensibles, RGPD strict
    # -------------------------------------------------------------------------
    'robust': {
        'JWT_ACCESS_TOKEN_LIFETIME':    300,         # 5 minutes
        'JWT_REFRESH_TOKEN_LIFETIME':   86400,       # 1 jour
        'REFRESH_TOKEN_ROTATION':       True,
        'TOKEN_BLACKLIST_ENABLED':      True,
        'ACCOUNT_LOCKOUT_ENABLED':      True,
        'MAX_LOGIN_ATTEMPTS':           3,
        'LOCKOUT_DURATION_MINUTES':     60,
        'RATE_LIMITING_ENABLED':        True,
        'PASSWORD_HISTORY_ENABLED':     True,
        'PASSWORD_HISTORY_COUNT':       12,
        'BREACH_CHECK_ENABLED':         True,
        'BREACH_CHECK_REJECT':          True,
        'MAGIC_LINK_ENABLED':           False,       # Lien email = vecteur d'attaque potentiel
        'WEBAUTHN_ENABLED':             True,        # Passkeys recommandées
        'AUDIT_LOGGING_ENABLED':        True,
        'DEVICE_LIMIT_ENABLED':         True,
        'DEFAULT_MAX_DEVICES':          2,
        'DEVICE_LIMIT_ACTION':          'deny',
        'SESSION_LIMIT_ENABLED':        True,
        'DEFAULT_MAX_SESSIONS':         1,
        'CORS_ALLOW_ALL_ORIGINS':       False,
        'SECURITY_HEADERS_ENABLED':     True,
    },
}

VALID_SECURE_MODES = set(SECURE_MODE_PRESETS.keys())


class TenxyteSettings:
    """
    Settings avec valeurs par défaut pour Tenxyte.

    Toutes les valeurs peuvent être surchargées dans settings.py du projet.

    Ordre de priorité :
        1. TENXYTE_<NOM> explicite dans settings.py
        2. Preset du TENXYTE_SHORTCUT_SECURE_MODE actif
        3. Valeur par défaut définie dans cette classe
    """

    def _get(self, name: str, default):
        """
        Résout la valeur d'un setting en appliquant la priorité :
        settings.py > preset > défaut.

        Args:
            name: Nom du setting SANS le préfixe TENXYTE_ (ex: 'JWT_ACCESS_TOKEN_LIFETIME')
            default: Valeur par défaut si ni settings.py ni preset ne définissent la valeur
        """
        django_key = f'TENXYTE_{name}'

        # 1. Valeur explicite dans settings.py — priorité absolue
        if hasattr(settings, django_key):
            return getattr(settings, django_key)

        # 2. Preset du mode actif
        mode = getattr(settings, 'TENXYTE_SHORTCUT_SECURE_MODE', None)
        if mode is not None:
            if mode not in VALID_SECURE_MODES:
                import warnings
                warnings.warn(
                    f"TENXYTE_SHORTCUT_SECURE_MODE='{mode}' is invalid. "
                    f"Valid values: {sorted(VALID_SECURE_MODES)}. Falling back to defaults.",
                    UserWarning,
                    stacklevel=3,
                )
            else:
                preset = SECURE_MODE_PRESETS[mode]
                if name in preset:
                    return preset[name]

        # 3. Défaut conf.py
        return default

    # =============================================
    # JWT Settings
    # =============================================

    @property
    def JWT_SECRET_KEY(self):
        """Clé secrète pour signer les JWT (utilise SECRET_KEY par défaut)."""
        return getattr(settings, 'TENXYTE_JWT_SECRET_KEY', settings.SECRET_KEY)

    @property
    def JWT_ALGORITHM(self):
        """Algorithme de signature JWT."""
        return self._get('JWT_ALGORITHM', 'HS256')

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
    def SMS_BACKEND(self):
        """
        Backend SMS à utiliser.
        Options:
        - 'tenxyte.backends.sms.TwilioBackend'
        - 'tenxyte.backends.sms.NGHBackend'
        - 'tenxyte.backends.sms.ConsoleBackend' (défaut, pour dev)
        """
        return self._get('SMS_BACKEND', 'tenxyte.backends.sms.ConsoleBackend')

    @property
    def SMS_ENABLED(self):
        """Activer l'envoi réel de SMS."""
        return self._get('SMS_ENABLED', False)

    @property
    def SMS_DEBUG(self):
        """Mode debug SMS (log au lieu d'envoyer)."""
        return self._get('SMS_DEBUG', True)

    # =============================================
    # Email Backend
    # =============================================

    @property
    def EMAIL_BACKEND(self):
        """
        Backend email à utiliser.
        Options:
        - 'tenxyte.backends.email.DjangoBackend' (défaut, utilise EMAIL_BACKEND Django)
        - 'tenxyte.backends.email.TemplateEmailBackend' (avec support templates)
        - 'tenxyte.backends.email.ConsoleBackend' (pour dev, affiche dans les logs)
        - 'tenxyte.backends.email.SendGridBackend' (legacy, préférer django-anymail)

        Recommandé: Utilisez DjangoBackend et configurez Django mail:
            EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
            # ou avec django-anymail:
            EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
        """
        return self._get('EMAIL_BACKEND', 'tenxyte.backends.email.DjangoBackend')

    # =============================================
    # Password Validation
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

    # =============================================
    # Security / Rate Limiting
    # =============================================

    @property
    def RATE_LIMITING_ENABLED(self):
        """Activer/désactiver le rate limiting pour les tentatives de login et appels API."""
        return self._get('RATE_LIMITING_ENABLED', True)

    @property
    def MAX_LOGIN_ATTEMPTS(self):
        """Nombre maximum de tentatives de login avant verrouillage."""
        return self._get('MAX_LOGIN_ATTEMPTS', 5)

    @property
    def LOCKOUT_DURATION_MINUTES(self):
        """Durée du verrouillage de compte en minutes."""
        return self._get('LOCKOUT_DURATION_MINUTES', 30)

    @property
    def RATE_LIMIT_WINDOW_MINUTES(self):
        """Fenêtre temporelle pour le comptage des tentatives de login (en minutes)."""
        return self._get('RATE_LIMIT_WINDOW_MINUTES', 15)

    @property
    def ACCOUNT_LOCKOUT_ENABLED(self):
        """Activer/désactiver le verrouillage de compte après échecs."""
        return self._get('ACCOUNT_LOCKOUT_ENABLED', True)

    # =============================================
    # Multi-Application
    # =============================================

    @property
    def APPLICATION_AUTH_ENABLED(self):
        """
        Activer/désactiver l'authentification par application (X-Access-Key / X-Access-Secret).
        """
        return self._get('APPLICATION_AUTH_ENABLED', True)

    @property
    def EXEMPT_PATHS(self):
        """Chemins exemptés de l'authentification par application (match par préfixe)."""
        return self._get('EXEMPT_PATHS', ['/admin/', '/api/v1/health/', '/api/v1/docs/'])

    @property
    def EXACT_EXEMPT_PATHS(self):
        """Chemins exemptés de l'authentification par application (match exact)."""
        return self._get('EXACT_EXEMPT_PATHS', ['/api/v1/'])

    # =============================================
    # Session & Device Limits
    # =============================================

    @property
    def TENXYTE_SESSION_LIMIT_ENABLED(self):
        """Activer/désactiver la limite de sessions concurrentes."""
        return self._get('SESSION_LIMIT_ENABLED', True)

    @property
    def TENXYTE_DEFAULT_MAX_SESSIONS(self):
        """Nombre max de sessions concurrentes par défaut (surchargeable par utilisateur)."""
        return self._get('DEFAULT_MAX_SESSIONS', 1)

    @property
    def TENXYTE_DEFAULT_SESSION_LIMIT_ACTION(self):
        """
        Action lorsque la limite de sessions est dépassée.
        Options: 'deny' (refuser) ou 'revoke_oldest' (révoquer la plus ancienne).
        """
        return self._get('DEFAULT_SESSION_LIMIT_ACTION', 'revoke_oldest')

    @property
    def TENXYTE_DEVICE_LIMIT_ENABLED(self):
        """Activer/désactiver la limite de devices uniques."""
        return self._get('DEVICE_LIMIT_ENABLED', True)

    @property
    def TENXYTE_DEFAULT_MAX_DEVICES(self):
        """Nombre max de devices uniques par défaut (surchargeable par utilisateur)."""
        return self._get('DEFAULT_MAX_DEVICES', 1)

    @property
    def TENXYTE_DEVICE_LIMIT_ACTION(self):
        """
        Action lorsque la limite de devices est dépassée.
        Options: 'deny' (refuser) ou 'revoke_oldest' (révoquer les sessions du plus ancien device).
        """
        return self._get('DEVICE_LIMIT_ACTION', 'deny')

    # =============================================
    # Social Login Multi-Provider
    # =============================================

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
    def BREACH_CHECK_ENABLED(self):
        """Activer/désactiver la vérification des mots de passe compromis via HIBP."""
        return self._get('BREACH_CHECK_ENABLED', False)

    @property
    def BREACH_CHECK_REJECT(self):
        """
        Si True, rejette les mots de passe compromis (erreur 400).
        Si False, avertit seulement dans les logs (mode warn).
        """
        return self._get('BREACH_CHECK_REJECT', True)

    # =============================================
    # Magic Link (Passwordless)
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
    def SIMPLE_THROTTLE_RULES(self):
        """
        Règles de throttling simples par URL.
        Permet de throttle n'importe quelle route sans créer de classe custom.

        Format: { 'url_prefix': 'rate' }
        - Prefix match par défaut: '/api/v1/products/' matche '/api/v1/products/123/'
        - Match exact avec '$': '/api/v1/health/$'
        - Rates: 'X/sec', 'X/min', 'X/hour', 'X/day'

        Exemple:
            TENXYTE_SIMPLE_THROTTLE_RULES = {
                '/api/v1/products/': '100/hour',
                '/api/v1/search/': '30/min',
                '/api/v1/upload/': '5/hour',
            }

        Nécessite d'ajouter 'tenxyte.throttles.SimpleThrottleRule' dans
        REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'].
        """
        return self._get('SIMPLE_THROTTLE_RULES', {})

    # =============================================
    # Audit Logging
    # =============================================

    @property
    def AUDIT_LOGGING_ENABLED(self):
        """Activer/désactiver le journal d'audit."""
        return self._get('AUDIT_LOGGING_ENABLED', True)

    # =============================================
    # Twilio Settings (si backend Twilio) — toujours manuels
    # =============================================

    @property
    def TWILIO_ACCOUNT_SID(self):
        """Twilio Account SID."""
        return getattr(settings, 'TWILIO_ACCOUNT_SID', '')

    @property
    def TWILIO_AUTH_TOKEN(self):
        """Twilio Auth Token."""
        return getattr(settings, 'TWILIO_AUTH_TOKEN', '')

    @property
    def TWILIO_PHONE_NUMBER(self):
        """Twilio Phone Number (format: +1234567890)."""
        return getattr(settings, 'TWILIO_PHONE_NUMBER', '')

    # =============================================
    # NGH Corp Settings (si backend NGH) — toujours manuels
    # =============================================

    @property
    def NGH_API_KEY(self):
        """NGH Corp API Key."""
        return getattr(settings, 'NGH_API_KEY', '')

    @property
    def NGH_API_SECRET(self):
        """NGH Corp API Secret."""
        return getattr(settings, 'NGH_API_SECRET', '')

    @property
    def NGH_SENDER_ID(self):
        """NGH Corp Sender ID affiché comme expéditeur du SMS."""
        return getattr(settings, 'NGH_SENDER_ID', '')

    # =============================================
    # SendGrid Settings (si backend SendGrid) — toujours manuels
    # =============================================

    @property
    def SENDGRID_API_KEY(self):
        """SendGrid API Key."""
        return getattr(settings, 'SENDGRID_API_KEY', '')

    @property
    def SENDGRID_FROM_EMAIL(self):
        """SendGrid email expéditeur."""
        return getattr(settings, 'SENDGRID_FROM_EMAIL', 'noreply@example.com')

    # =============================================
    # CORS Settings
    # =============================================

    @property
    def CORS_ENABLED(self):
        """Activer/désactiver le middleware CORS intégré."""
        return self._get('CORS_ENABLED', False)

    @property
    def CORS_ALLOW_ALL_ORIGINS(self):
        """Autoriser toutes les origines (dangereux en production)."""
        return self._get('CORS_ALLOW_ALL_ORIGINS', False)

    @property
    def CORS_ALLOWED_ORIGINS(self):
        """
        Liste des origines autorisées.
        Exemple: ['https://example.com', 'http://localhost:3000']
        """
        return self._get('CORS_ALLOWED_ORIGINS', [])

    @property
    def CORS_ALLOW_CREDENTIALS(self):
        """Autoriser les credentials (cookies, Authorization header)."""
        return self._get('CORS_ALLOW_CREDENTIALS', True)

    @property
    def CORS_ALLOWED_METHODS(self):
        """Méthodes HTTP autorisées."""
        return self._get('CORS_ALLOWED_METHODS', [
            'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'
        ])

    @property
    def CORS_ALLOWED_HEADERS(self):
        """Headers autorisés dans les requêtes."""
        return self._get('CORS_ALLOWED_HEADERS', [
            'Accept',
            'Accept-Language',
            'Content-Type',
            'Authorization',
            'X-Access-Key',
            'X-Access-Secret',
            'X-Requested-With',
        ])

    @property
    def CORS_EXPOSE_HEADERS(self):
        """Headers exposés au client."""
        return self._get('CORS_EXPOSE_HEADERS', [])

    @property
    def CORS_MAX_AGE(self):
        """Durée de cache du preflight en secondes (défaut: 24h)."""
        return self._get('CORS_MAX_AGE', 86400)

    # =============================================
    # Security Headers
    # =============================================

    @property
    def SECURITY_HEADERS_ENABLED(self):
        """Activer/désactiver les headers de sécurité."""
        return self._get('SECURITY_HEADERS_ENABLED', False)

    @property
    def SECURITY_HEADERS(self):
        """
        Headers de sécurité à ajouter aux réponses.
        Peut être surchargé dans settings.py.
        """
        return self._get('SECURITY_HEADERS', {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        })

    # =============================================
    # Google OAuth Settings
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

    @property
    def ORGANIZATIONS_ENABLED(self):
        """
        Enable Organizations feature (opt-in).
        Default: False (disabled for backward compatibility)
        """
        return self._get('ORGANIZATIONS_ENABLED', False)

    @property
    def ORG_ROLE_INHERITANCE(self):
        """
        Enable role inheritance in organization hierarchy.
        If True, roles propagate down from parent to children.
        Default: True
        """
        return self._get('ORG_ROLE_INHERITANCE', True)

    @property
    def ORG_MAX_DEPTH(self):
        """
        Maximum depth of organization hierarchy.
        Default: 5 levels
        """
        return self._get('ORG_MAX_DEPTH', 5)

    @property
    def ORG_MAX_MEMBERS(self):
        """
        Default maximum members per organization (0 = unlimited).
        Can be overridden per organization.
        Default: 0 (unlimited)
        """
        return self._get('ORG_MAX_MEMBERS', 0)

    @property
    def ORGANIZATION_MODEL(self):
        """
        Swappable Organization model (like AUTH_USER_MODEL).
        Default: 'tenxyte.Organization'
        """
        return self._get('ORGANIZATION_MODEL', 'tenxyte.Organization')

    @property
    def ORGANIZATION_ROLE_MODEL(self):
        """
        Swappable OrganizationRole model.
        Default: 'tenxyte.OrganizationRole'
        """
        return self._get('ORGANIZATION_ROLE_MODEL', 'tenxyte.OrganizationRole')

    @property
    def ORGANIZATION_MEMBERSHIP_MODEL(self):
        """
        Swappable OrganizationMembership model.
        Default: 'tenxyte.OrganizationMembership'
        """
        return self._get('ORGANIZATION_MEMBERSHIP_MODEL', 'tenxyte.OrganizationMembership')


# Instance singleton accessible partout
auth_settings = TenxyteSettings()
org_settings = auth_settings  # Alias pour clarté dans le code org
