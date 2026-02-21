import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenxyte', '0004_social_connection'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebAuthnCredential',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('credential_id', models.TextField(db_index=True, unique=True)),
                ('public_key', models.TextField()),
                ('sign_count', models.PositiveBigIntegerField(default=0)),
                ('device_name', models.CharField(blank=True, default='', max_length=100)),
                ('aaguid', models.CharField(blank=True, default='', max_length=36)),
                ('transports', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='webauthn_credentials',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'webauthn_credentials',
            },
        ),
        migrations.CreateModel(
            name='WebAuthnChallenge',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('challenge', models.CharField(db_index=True, max_length=191, unique=True)),
                ('operation', models.CharField(
                    choices=[('register', 'Register'), ('authenticate', 'Authenticate')],
                    max_length=16,
                )),
                ('is_used', models.BooleanField(default=False)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='webauthn_challenges',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'webauthn_challenges',
            },
        ),
    ]
