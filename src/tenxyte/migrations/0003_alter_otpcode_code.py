"""
Migration: Increase OTPCode.code max_length from 6 to 64 for SHA-256 hash storage.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenxyte', '0002_alter_application_options_user_max_devices_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otpcode',
            name='code',
            field=models.CharField(max_length=64),
        ),
    ]
