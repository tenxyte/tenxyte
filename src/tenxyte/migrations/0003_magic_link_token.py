import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenxyte', '0002_organization_organizationmembership_organizationrole_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MagicLinkToken',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('token', models.CharField(db_index=True, max_length=191, unique=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('is_used', models.BooleanField(default=False)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='magic_link_tokens',
                    to=getattr(settings, 'TENXYTE_APPLICATION_MODEL', 'tenxyte.application'),
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='magic_link_tokens',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'magic_link_tokens',
            },
        ),
    ]
