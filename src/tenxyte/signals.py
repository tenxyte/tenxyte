"""
Signals pour Tenxyte.

Connectés automatiquement via apps.py ready().

=======================================================
SIGNAUX PUBLICS — Pour les intégrateurs (R14 Audit)
=======================================================

Les signaux suivants peuvent être connectés par les projets qui utilisent Tenxyte
pour déclencher des alertes, des logs SIEM, ou d'autres actions :

.. code-block:: python

    from tenxyte.signals import suspicious_login_detected

    @receiver(suspicious_login_detected)
    def handle_suspicious_login(sender, user, ip_address, reason, **kwargs):
        alert_siem(user=user, ip=ip_address, event=reason)

Signaux disponibles:
    - account_locked(user, reason)
    - suspicious_login_detected(user, ip_address, reason)
    - brute_force_detected(user, ip_address, attempt_count)
    - agent_circuit_breaker_triggered(agent_token, reason)
"""

import logging

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver, Signal

logger = logging.getLogger("tenxyte.signals")


# ============================================================================
# Signaux publics pour les événements de sécurité critiques (R14 Audit)
# ============================================================================

account_locked = Signal()
"""
Émis quand un compte est verrouillé (trop de tentatives échouées).
Arguments: user (AbstractUser), reason (str)
"""

suspicious_login_detected = Signal()
"""
Émis lors d'une tentative de connexion suspecte (IP inconnue, user-agent inhabituel, etc.)
Arguments: user (AbstractUser), ip_address (str), reason (str)
"""

brute_force_detected = Signal()
"""
Émis quand un comportement de brute-force est détecté sur une adresse IP ou un compte.
Arguments: user (AbstractUser|None), ip_address (str), attempt_count (int)
"""

agent_circuit_breaker_triggered = Signal()
"""
Émis quand le circuit breaker AIRS suspend un AgentToken.
Arguments: agent_token (AgentToken), reason (str)
"""


# ============================================================================
# Helpers internes
# ============================================================================


def _get_user_model_label():
    """Retourne le label du modèle User configuré."""
    return getattr(settings, "AUTH_USER_MODEL", "tenxyte.User")


# ============================================================================
# Handlers internes
# ============================================================================


@receiver(pre_delete)
def audit_user_deletion(sender, instance, **kwargs):
    """
    Enregistre la suppression d'un utilisateur dans le journal d'audit.
    Déclenché avant la suppression pour capturer les infos du user.
    """
    from .conf import auth_settings

    user_model_label = _get_user_model_label()
    sender_label = f"{sender._meta.app_label}.{sender._meta.object_name}"

    if sender_label != user_model_label:
        return

    if not auth_settings.AUDIT_LOGGING_ENABLED:
        return

    from .models import AuditLog

    AuditLog.log(
        action="account_deleted",
        user=None,
        details={
            "deleted_user_id": str(instance.pk),
            "deleted_user_email": getattr(instance, "email", ""),
        },
    )
    logger.info("User %s (%s) deleted", instance.pk, getattr(instance, "email", ""))


@receiver(post_save)
def log_account_locked(sender, instance, **kwargs):
    """
    Enregistre le verrouillage d'un compte dans le journal d'audit.
    Déclenché lorsque is_locked passe à True.
    Émet aussi le signal public `account_locked` pour les intégrateurs (R14).
    """
    from .conf import auth_settings

    user_model_label = _get_user_model_label()
    sender_label = f"{sender._meta.app_label}.{sender._meta.object_name}"

    if sender_label != user_model_label:
        return

    if not auth_settings.AUDIT_LOGGING_ENABLED:
        return

    if not hasattr(instance, "is_locked"):
        return

    # Seulement si le compte vient d'être verrouillé (pas à la création)
    if not kwargs.get("created", False) and instance.is_locked:
        # Vérifier que c'est bien un changement (pas juste un save normal)
        if kwargs.get("update_fields") and "is_locked" not in kwargs["update_fields"]:
            return

        from .models import AuditLog

        AuditLog.log(action="account_locked", user=instance, details={"reason": "too_many_failed_attempts"})

        # Émettre le signal public pour les intégrateurs (R14)
        account_locked.send(sender=sender, user=instance, reason="too_many_failed_attempts")
