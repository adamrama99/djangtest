from django.db import migrations


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ("requester", "executor", "admin"):
        Group.objects.get_or_create(name=name)


def remove_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["requester", "executor", "admin"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0017_jadwaltayang_jadwaltayangbuktiplaylist_and_more"),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
