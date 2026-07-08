"""
Migration 0017 — Login OTP type et compte passwordless

Contexte:
    Ajoute le support additif de la connexion passwordless par OTP
    téléphonique :
    - Nouveau choix `"login"` pour `OTPCode.otp_type` (aucune valeur
      existante retirée).
    - Nouveau champ `has_usable_password` sur `User`, par défaut `True`
      pour préserver le comportement de tous les comptes existants (créés
      avant cette fonctionnalité, tous dotés d'un mot de passe choisi par
      leur propriétaire).

Impact:
    Purement additif : uniquement des `AddField`/`AlterField`, aucune
    suppression de champ, contrainte ou choix existant.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenxyte", "0016_normalize_phone_country_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="has_usable_password",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "False pour un Passwordless_Account : le mot de passe stocké est une "
                    "valeur aléatoire inutilisable (créé via login OTP auto-register, ou "
                    "jamais remplacé par un mot de passe choisi par l'utilisateur)."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="otpcode",
            name="otp_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("email_verification", "Email Verification"),
                    ("phone_verification", "Phone Verification"),
                    ("password_reset", "Password Reset"),
                    ("login_2fa", "Login 2FA"),
                    ("login", "Login OTP"),
                ],
            ),
        ),
    ]
