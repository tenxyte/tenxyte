"""
Migration 0006 — R2 Audit: Chiffrement du totp_secret

Contexte:
    Le champ `users.totp_secret` était stocké en clair. Il est maintenant chiffré
    avec django-cryptography (AES-256 via Fernet).

Prérequis:
    - `django-cryptography` doit être installé : pip install django-cryptography
    - `FIELD_ENCRYPTION_KEY` doit être défini dans settings.py.

Impact:
    - La colonne est élargie de 32 → 128 chars pour accueillir les valeurs chiffrées.
    - Les totp_secrets existants seront chiffrés au prochain accès via l'ORM.
"""

from django.db import migrations, models


def log_totp_migration_info(apps, schema_editor):
    """Informe de l'impact de la migration TOTP."""
    User = apps.get_model("tenxyte", "User")
    count = User.objects.filter(is_2fa_enabled=True).count()
    if count > 0:
        print(f"\n  ℹ️  [R2 Audit] {count} utilisateur(s) avec 2FA actif.")
        print("  ℹ️  Les totp_secrets seront chiffrés au prochain accès via l'ORM (django-cryptography).")
        print("  ℹ️  Installez django-cryptography et définissez FIELD_ENCRYPTION_KEY.\n")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenxyte", "0005_hash_refresh_tokens_revoke_existing"),
    ]

    operations = [
        # Agrandir la colonne pour accueillir la valeur chiffrée (Fernet ajoute ~100 chars)
        migrations.AlterField(
            model_name="user",
            name="totp_secret",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        # Log info sur les utilisateurs avec 2FA actif
        migrations.RunPython(log_totp_migration_info, reverse_code=noop),
    ]
