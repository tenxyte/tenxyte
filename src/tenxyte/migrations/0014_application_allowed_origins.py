from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenxyte", "0013_alter_refreshtoken_application"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="allowed_origins",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of allowed origins for key-only (frontend) auth. Empty list requires secret.",
            ),
        ),
    ]
