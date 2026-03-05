"""
Migration 0007 — R10 Audit: Suppression des OAuth tokens en base

Contexte:
    Les champs `access_token` et `refresh_token` de la table `social_connections`
    contenaient des tokens OAuth en clair. L'audit (R10) recommande de ne plus les
    stocker pour réduire la surface d'exposition si la base de données est compromise.

    Les tokens OAuth ont une durée de vie courte et peuvent être ré-obtenus via le
    flux OAuth standard. Les stocker n'est généralement pas nécessaire.

Impact:
    - Tous les access_token et refresh_token existants sont effacés.
    - Les utilisateurs ne seront pas déconnectés (les JWT Tenxyte sont indépendants).
    - Si votre application nécessite les tokens OAuth post-connexion, implementez
      un stockage chiffré avec django-cryptography.
"""

from django.db import migrations, models


def clear_oauth_tokens(apps, schema_editor):
    """Efface tous les tokens OAuth stockés en clair."""
    SocialConnection = apps.get_model("tenxyte", "SocialConnection")
    count = SocialConnection.objects.exclude(access_token="", refresh_token="").count()

    if count > 0:
        SocialConnection.objects.update(access_token="", refresh_token="")
        print(f"\n  ⚠️  [R10 Audit] {count} connexion(s) sociale(s) : tokens OAuth effacés.")
        print("  ℹ️  Les utilisateurs restent connectés via leurs JWT Tenxyte.\n")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenxyte", "0006_encrypt_totp_secret"),
    ]

    operations = [
        # Effacer les tokens OAuth existants
        migrations.RunPython(clear_oauth_tokens, reverse_code=noop),
        # Mettre à jour les help_text des champs
        migrations.AlterField(
            model_name="socialconnection",
            name="access_token",
            field=models.TextField(
                blank=True, default="", help_text="Not stored for security (R10 audit). Always empty."
            ),
        ),
        migrations.AlterField(
            model_name="socialconnection",
            name="refresh_token",
            field=models.TextField(
                blank=True, default="", help_text="Not stored for security (R10 audit). Always empty."
            ),
        ),
    ]
