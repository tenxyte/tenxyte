# Generated migration for phone uniqueness constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenxyte", "0014_application_allowed_origins"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                fields=["phone_country_code", "phone_number"],
                condition=models.Q(("phone_number__isnull", False), ("is_deleted", False)),
                name="unique_phone_when_not_deleted",
            ),
        ),
    ]
