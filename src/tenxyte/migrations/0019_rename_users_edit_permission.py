from django.db import migrations


def forward(apps, schema_editor):
    Permission = apps.get_model("tenxyte", "Permission")
    old = Permission.objects.filter(code="users.edit").first()
    if not old:
        return
    new = Permission.objects.filter(code="users.update").first()
    if new is None:
        # Renommer en place : conserve les M2M (rôles + permissions directes).
        old.code = "users.update"
        old.name = "Update Users"
        old.description = "Can update user information"
        old.save(update_fields=["code", "name", "description"])
        return
    # `users.update` existe déjà (créé par un tenxyte_seed post-patch) :
    # basculer les liens de l'ancienne vers la nouvelle, puis supprimer.
    RoleThrough = Permission.roles.through
    RoleThrough.objects.filter(permission_id=old.id).exclude(
        role_id__in=RoleThrough.objects.filter(permission_id=new.id).values("role_id")
    ).update(permission_id=new.id)
    DirectThrough = apps.get_model("tenxyte", "User").direct_permissions.through
    DirectThrough.objects.filter(permission_id=old.id).exclude(
        user_id__in=DirectThrough.objects.filter(permission_id=new.id).values("user_id")
    ).update(permission_id=new.id)
    RoleThrough.objects.filter(permission_id=old.id).delete()
    DirectThrough.objects.filter(permission_id=old.id).delete()
    old.delete()


def backward(apps, schema_editor):
    Permission = apps.get_model("tenxyte", "Permission")
    p = Permission.objects.filter(code="users.update").first()
    if p and not Permission.objects.filter(code="users.edit").exists():
        p.code = "users.edit"
        p.name = "Edit Users"
        p.description = "Can edit user information"
        p.save(update_fields=["code", "name", "description"])


class Migration(migrations.Migration):
    dependencies = [("tenxyte", "0018_user_must_change_password")]
    operations = [migrations.RunPython(forward, backward)]
