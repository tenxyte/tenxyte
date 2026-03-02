from django.conf import settings

class SecuritySettingsMixin:

    @property
    def RATE_LIMITING_ENABLED(self):
        """Activer/désactiver le rate limiting pour les tentatives de login et appels API."""
        return self._get('RATE_LIMITING_ENABLED', True)

    @property
    def RATE_LIMIT_WINDOW_MINUTES(self):
        """Fenêtre temporelle pour le comptage des tentatives de login (en minutes)."""
        return self._get('RATE_LIMIT_WINDOW_MINUTES', 15)

    @property
    def TRUSTED_PROXIES(self):
        """
        Liste des IPs ou CIDRs de proxies de confiance pour l'extraction de l'IP client
        depuis l'en-tête X-Forwarded-For.

        Si cette liste est vide (défaut), l'en-tête X-Forwarded-For est accepté sans
        validation (à utiliser seulement en développement ou derrière un seul proxy connu).

        En production avec plusieurs workers ou un load balancer, configurez explicitement
        les IPs de votre proxy/load balancer pour éviter la forge de l'en-tête.

        Exemple:
            TENXYTE_TRUSTED_PROXIES = ['10.0.0.1', '192.168.1.0/24', '127.0.0.1']
        """
        return self._get('TRUSTED_PROXIES', [])

    # =============================================
    # Multi-Application
    # =============================================

    @property
    def SESSION_LIMIT_ENABLED(self):
        """Activer/désactiver la limite de sessions concurrentes."""
        return self._get('SESSION_LIMIT_ENABLED', True)

    @property
    def DEFAULT_MAX_SESSIONS(self):
        """Nombre max de sessions concurrentes par défaut (surchargeable par utilisateur)."""
        return self._get('DEFAULT_MAX_SESSIONS', 1)

    @property
    def DEFAULT_SESSION_LIMIT_ACTION(self):
        """
        Action lorsque la limite de sessions est dépassée.
        Options: 'deny' (refuser) ou 'revoke_oldest' (révoquer la plus ancienne).
        """
        return self._get('DEFAULT_SESSION_LIMIT_ACTION', 'revoke_oldest')

    @property
    def DEVICE_LIMIT_ENABLED(self):
        """Activer/désactiver la limite de devices uniques."""
        return self._get('DEVICE_LIMIT_ENABLED', True)

    @property
    def DEFAULT_MAX_DEVICES(self):
        """Nombre max de devices uniques par défaut (surchargeable par utilisateur)."""
        return self._get('DEFAULT_MAX_DEVICES', 1)

    @property
    def DEVICE_LIMIT_ACTION(self):
        """
        Action lorsque la limite de devices est dépassée.
        Options: 'deny' (refuser) ou 'revoke_oldest' (révoquer les sessions du plus ancien device).
        """
        return self._get('DEVICE_LIMIT_ACTION', 'deny')

    # =============================================
    # Social Login Multi-Provider
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
    def AUDIT_LOGGING_ENABLED(self):
        """Activer/désactiver le journal d'audit."""
        return self._get('AUDIT_LOGGING_ENABLED', True)

    @property
    def AUDIT_LOG_RETENTION_DAYS(self):
        """
        Nombre de jours de rétention des logs d'audit avant purge automatique.
        0 = conserver indéfiniment (désactive la purge automatique).
        Default: 90 jours (recommandé RGPD).
        """
        return self._get('AUDIT_LOG_RETENTION_DAYS', 90)

    # =============================================
    # Twilio Settings (si backend Twilio) — toujours manuels
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

