from django.conf import settings

class AirsSettingsMixin:

    @property
    def AIRS_ENABLED(self):
        """Activer/désactiver le module AIRS (AI Responsibility & Security)."""
        return self._get('AIRS_ENABLED', True)

    @property
    def AIRS_TOKEN_MAX_LIFETIME(self):
        """Durée de vie max d'un AgentToken en secondes (24h par défaut)."""
        return self._get('AIRS_TOKEN_MAX_LIFETIME', 86400)

    @property
    def AIRS_DEFAULT_EXPIRY(self):
        """Durée d'expiration par défaut d'un AgentToken en secondes."""
        return self._get('AIRS_DEFAULT_EXPIRY', 3600)

    @property
    def AIRS_REQUIRE_EXPLICIT_PERMISSIONS(self):
        """Empêche un agent de recevoir 'toutes les permissions'."""
        return self._get('AIRS_REQUIRE_EXPLICIT_PERMISSIONS', True)

    # =============================================
    # Agent / AIRS Settings (Phase 2)
    # =============================================

    @property
    def AIRS_CIRCUIT_BREAKER_ENABLED(self):
        """Activer/désactiver le coupe-circuit de l'agent."""
        return self._get('AIRS_CIRCUIT_BREAKER_ENABLED', True)

    @property
    def AIRS_DEFAULT_MAX_RPM(self):
        """Limite par minute du coupe-circuit."""
        return self._get('AIRS_DEFAULT_MAX_RPM', 60)

    @property
    def AIRS_DEFAULT_MAX_TOTAL(self):
        """Limite totale du coupe-circuit."""
        return self._get('AIRS_DEFAULT_MAX_TOTAL', 1000)

    @property
    def AIRS_DEFAULT_MAX_FAILURES(self):
        """Nombre max d'échecs avant suspension par coupe-circuit."""
        return self._get('AIRS_DEFAULT_MAX_FAILURES', 10)

    @property
    def AIRS_CONFIRMATION_REQUIRED(self):
        """Liste globale des permissions nécessitant toujours une confirmation HITL."""
        return self._get('AIRS_CONFIRMATION_REQUIRED', [])

    # =============================================
    # Agent / AIRS Settings (Phase 3)
    # =============================================

    @property
    def AIRS_REDACT_PII(self):
        """Activer/désactiver la rédaction des PII pour les agents."""
        return self._get('AIRS_REDACT_PII', False)

    @property
    def AIRS_BUDGET_TRACKING_ENABLED(self):
        """Activer/désactiver le suivi de budget pour les agents."""
        return self._get('AIRS_BUDGET_TRACKING_ENABLED', False)

# Instance singleton accessible partout

