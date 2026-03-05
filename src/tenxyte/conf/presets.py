from django.conf import settings

SECURE_MODE_PRESETS = {
    # -------------------------------------------------------------------------
    # development — Démarrage rapide, sécurité de base
    # -------------------------------------------------------------------------
    'development': {
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
        'CORS_ALLOW_ALL_ORIGINS':       False,
        'SECURITY_HEADERS_ENABLED':     False,
    },

    # -------------------------------------------------------------------------
    # medium — Production standard, équilibre UX / sécurité
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

