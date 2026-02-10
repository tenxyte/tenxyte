"""
Signals pour Tenxyte.

Connectés automatiquement via apps.py ready().
"""

import logging

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger('tenxyte.signals')


def _get_user_model_label():
    """Retourne le label du modèle User configuré."""
    return getattr(settings, 'AUTH_USER_MODEL', 'tenxyte.User')


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
        action='account_deleted',
        user=None,
        details={
            'deleted_user_id': str(instance.pk),
            'deleted_user_email': getattr(instance, 'email', ''),
        }
    )
    logger.info("User %s (%s) deleted", instance.pk, getattr(instance, 'email', ''))


@receiver(post_save)
def log_account_locked(sender, instance, **kwargs):
    """
    Enregistre le verrouillage d'un compte dans le journal d'audit.
    Déclenché lorsque is_locked passe à True.
    """
    from .conf import auth_settings

    user_model_label = _get_user_model_label()
    sender_label = f"{sender._meta.app_label}.{sender._meta.object_name}"

    if sender_label != user_model_label:
        return

    if not auth_settings.AUDIT_LOGGING_ENABLED:
        return

    if not hasattr(instance, 'is_locked'):
        return

    # Seulement si le compte vient d'être verrouillé (pas à la création)
    if not kwargs.get('created', False) and instance.is_locked:
        # Vérifier que c'est bien un changement (pas juste un save normal)
        if kwargs.get('update_fields') and 'is_locked' not in kwargs['update_fields']:
            return

        from .models import AuditLog
        AuditLog.log(
            action='account_locked',
            user=instance,
            details={'reason': 'too_many_failed_attempts'}
        )
