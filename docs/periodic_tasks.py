"""
Tenxyte — Tâches Périodiques de Maintenance et Sécurité
========================================================

Ce document décrit les tâches qui doivent être exécutées périodiquement
pour maintenir la santé et la sécurité de votre installation Tenxyte.

Intégration possible avec Celery Beat, APScheduler, ou cron.

R15 Audit: Documenter et automatiser les tâches de nettoyage périodiques.
"""

# ============================================================================
# TÂCHES QUOTIDIENNES
# ============================================================================

# 1. Nettoyage des refresh tokens expirés
# ----------------------------------------
# Les RefreshToken révoqués ou expirés s'accumulent en base de données.
# Cette commande de gestion Django supprime les entrées obsolètes.
#
# Celery Beat (recommandé):
#   from celery import shared_task
#   @shared_task
#   def cleanup_refresh_tokens():
#       from tenxyte.models import RefreshToken
#       from django.utils import timezone
#       count = RefreshToken.objects.filter(
#           is_revoked=True
#       ).delete()[0]
#       count += RefreshToken.objects.filter(
#           expires_at__lt=timezone.now(), is_revoked=False
#       ).update(is_revoked=True)
#       return f"Cleaned {count} expired/revoked refresh tokens"
#
# Cron alternatif:
#   0 3 * * * python manage.py cleanup_tokens

# 2. Nettoyage des audit logs anciens (rétention)
# -------------------------------------------------
# Définir une politique de rétention pour éviter une croissance illimitée.
# Les réglementations (RGPD, SOC 2) peuvent imposer une rétention minimale ET maximale.
#
# Exemple : garder 90 jours d'audit logs
#   from tenxyte.models import AuditLog
#   from django.utils.timezone import now
#   from datetime import timedelta
#   AuditLog.objects.filter(created_at__lt=now() - timedelta(days=90)).delete()

# 3. Nettoyage des OTP expirés
# -----------------------------
# Les OTPCode non utilisés s'accumulent.
#   from tenxyte.models import OTPCode
#   from django.utils import timezone
#   OTPCode.objects.filter(expires_at__lt=timezone.now()).delete()


# ============================================================================
# TÂCHES HEBDOMADAIRES
# ============================================================================

# 4. Nettoyage des AgentToken expirés ou révoqués (AIRS)
# --------------------------------------------------------
#   from tenxyte.models.agent import AgentToken
#   from django.utils import timezone
#   AgentToken.objects.filter(
#       expires_at__lt=timezone.now()  # expirés
#   ).delete()

# 5. Nettoyage des MagicLink / tokens de vérification expirés
# ------------------------------------------------------------
# Selon vos modèles : UnverifiedEmail, PhoneVerification, etc.

# 6. Archivage des LoginAttempt anciens
# ----------------------------------------
# Les LoginAttempt n'ont pas besoin d'être conservés indéfiniment.
#   from tenxyte.models import LoginAttempt
#   from django.utils.timezone import now
#   from datetime import timedelta
#   LoginAttempt.objects.filter(attempted_at__lt=now() - timedelta(days=30)).delete()


# ============================================================================
# TÂCHES MENSUELLES / SÉCURITÉ
# ============================================================================

# 7. Rotation de la FIELD_ENCRYPTION_KEY
# -----------------------------------------
# Si vous utilisez django-cryptography pour le chiffrement du totp_secret (R2),
# planifiez une rotation périodique de la clé. Procédure :
# 1. Déchiffrer tous les champs avec l'ancienne clé
# 2. Chiffrer avec la nouvelle clé
# 3. Mettre à jour FIELD_ENCRYPTION_KEY dans settings.py
# Voir : https://django-cryptography.readthedocs.io/en/latest/key-rotation.html

# 8. Audit des tokens AgentToken à longue durée de vie
# -----------------------------------------------------
# Identifier les tokens AIRS avec une durée de vie > 24h qui n'ont pas été utilisés :
#   from tenxyte.models.agent import AgentToken
#   from django.utils import timezone
#   from datetime import timedelta
#   stale = AgentToken.objects.filter(
#       expires_at__gt=timezone.now() + timedelta(hours=24),
#       last_used_at__lt=timezone.now() - timedelta(days=7)
#   )

# 9. Vérification des dépendances vulnérables
# --------------------------------------------
# À exécuter manuellement ou en CI (R3, R7 audit) :
#   pip-audit
#   safety check
#   bandit -r src/tenxyte/


# ============================================================================
# CONFIGURATION CELERY BEAT (exemple)
# ============================================================================

# CELERY_BEAT_SCHEDULE = {
#     'tenxyte-cleanup-daily': {
#         'task': 'myapp.tasks.tenxyte_daily_cleanup',
#         'schedule': crontab(hour=3, minute=0),  # 3h du matin
#     },
#     'tenxyte-cleanup-weekly': {
#         'task': 'myapp.tasks.tenxyte_weekly_cleanup',
#         'schedule': crontab(hour=4, minute=0, day_of_week='monday'),
#     },
# }
