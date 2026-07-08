"""
Migration 0016 — Normalisation de l'indicatif téléphonique en base

Contexte:
    `phone_country_code` doit être stocké SANS le préfixe '+' (ex: "229").
    Le '+' n'est ajouté qu'à l'affichage / la sérialisation (voir
    `User.full_phone` et `AuthUserSerializer.get_phone`). Certaines lignes
    existantes peuvent contenir un '+' (ex: "+229") suite à des écritures
    directes ou à un ancien comportement, ce qui provoque un double préfixe
    ("++229") lors du formatage.

Impact:
    - Toutes les valeurs de `phone_country_code` commençant par '+' sont
      nettoyées (le '+' et les espaces superflus sont retirés).
    - Aucune donnée fonctionnelle n'est perdue, seul le format de stockage
      change.
"""

from django.db import migrations


def normalize_phone_country_code(apps, schema_editor):
    """Retire le '+' (et les espaces superflus) des indicatifs stockés."""
    User = apps.get_model("tenxyte", "User")
    users = User.objects.exclude(phone_country_code__isnull=True).exclude(phone_country_code="")

    updated = 0
    for user in users:
        normalized = user.phone_country_code.strip().lstrip("+")
        if normalized != user.phone_country_code:
            user.phone_country_code = normalized
            user.save(update_fields=["phone_country_code"])
            updated += 1

    if updated > 0:
        print(f"\n  ℹ️  [Phone normalize] {updated} indicatif(s) téléphonique(s) nettoyé(s) (préfixe '+' retiré).\n")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenxyte", "0015_add_unique_phone_constraint"),
    ]

    operations = [
        migrations.RunPython(normalize_phone_country_code, reverse_code=noop),
    ]
