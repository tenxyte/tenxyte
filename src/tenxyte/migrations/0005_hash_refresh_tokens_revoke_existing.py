"""
Migration 0005 — R1 Audit: Hash des refresh tokens

Contexte:
    Avant cette migration, les refresh tokens étaient stockés en clair dans la colonne
    `refresh_tokens.token`. Désormais, le modèle RefreshToken stocke SHA-256(token).

    Les tokens existants sont en clair — il est impossible de les rehacher car les
    valeurs brutes ne sont plus disponibles (elles n'ont été retournées qu'au client).

Stratégie de migration:
    1. Tous les refresh tokens existants sont révoqués (is_revoked=True).
    2. Le commentaire 'help_text' du champ 'token' est mis à jour (pas de changement de schéma).
    3. Les tokens invalides seront supprimés par la tâche de cleanup périodique.

Impact:
    - Toutes les sessions actives sont invalidées au déploiement.
    - Les utilisateurs doivent se reconnecter.
    - À prévoir en fenêtre de maintenance.
"""

from django.db import migrations


def revoke_all_plaintext_tokens(apps, schema_editor):
    """Révoque tous les tokens existants (stockés en clair, incompatibles avec le nouveau schéma SHA-256)."""
    RefreshToken = apps.get_model("tenxyte", "RefreshToken")
    count = RefreshToken.objects.filter(is_revoked=False).update(is_revoked=True)
    if count > 0:
        print(f"\n  ⚠️  [R1 Audit] {count} refresh token(s) révoqué(s) (migration vers SHA-256).")
        print("  ⚠️  Les utilisateurs doivent se reconnecter.\n")


def noop(apps, schema_editor):
    """Opération inverse : pas de rollback possible (tokens révoqués ne sont pas récupérables)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenxyte", "0004_auditlog_prompt_trace_id_alter_auditlog_action"),
    ]

    operations = [
        # Révoquer tous les tokens existants (données incompatibles avec SHA-256)
        migrations.RunPython(revoke_all_plaintext_tokens, reverse_code=noop),
        # Mettre à jour le help_text du champ token (changement de métadonnées uniquement)
        migrations.AlterField(
            model_name="refreshtoken",
            name="token",
            field=__import__("django.db.models", fromlist=["CharField"]).CharField(
                db_index=True,
                help_text="SHA-256 hash of the raw refresh token. Never store the raw value.",
                max_length=191,
                unique=True,
            ),
        ),
    ]
