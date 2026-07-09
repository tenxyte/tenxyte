"""
Migration 0018 — Changement de mot de passe forcé à la première connexion

Contexte:
    Ajoute le support du changement de mot de passe forcé à la première
    connexion (feature: force_password_change_on_first_login) :
    - Nouveau champ `must_change_password` sur `User`, par défaut `False`
      pour préserver le comportement de tous les comptes existants (aucun
      compte existant n'est affecté tant que le flag n'est pas positionné
      explicitement par une Provisioning_Operation).

Impact:
    Purement additif : uniquement un `AddField`, aucune suppression de
    champ, contrainte ou choix existant.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenxyte", "0017_login_otp_type_and_passwordless_account"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "True lorsqu'un compte a été provisionné par un tiers (admin ou "
                    "invitation) et doit (re)définir son mot de passe à la première "
                    "connexion avant tout autre accès. Remis à False après un changement "
                    "réussi via /password/change/ ou /password/set-initial/."
                ),
            ),
        ),
    ]
