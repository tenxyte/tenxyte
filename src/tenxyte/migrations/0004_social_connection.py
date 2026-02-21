import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenxyte', '0003_magic_link_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialConnection',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('provider', models.CharField(
                    choices=[
                        ('google', 'Google'),
                        ('github', 'GitHub'),
                        ('microsoft', 'Microsoft'),
                        ('facebook', 'Facebook'),
                        ('apple', 'Apple'),
                    ],
                    db_index=True,
                    max_length=32,
                )),
                ('provider_user_id', models.CharField(db_index=True, max_length=191)),
                ('email', models.CharField(blank=True, max_length=191)),
                ('first_name', models.CharField(blank=True, max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('avatar_url', models.URLField(blank=True, max_length=500)),
                ('access_token', models.TextField(blank=True)),
                ('refresh_token', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='social_connections',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'social_connections',
            },
        ),
        migrations.AlterUniqueTogether(
            name='socialconnection',
            unique_together={('provider', 'provider_user_id')},
        ),
    ]
