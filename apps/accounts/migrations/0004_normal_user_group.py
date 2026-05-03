from django.db import migrations


def add_normal_user_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    GroupProfile = apps.get_model('accounts', 'GroupProfile')

    group, _ = Group.objects.get_or_create(name='普通用户')
    GroupProfile.objects.get_or_create(
        group=group,
        defaults={
            'is_default': True,
            'description': '普通用户，可使用已授权的产品和服务。',
            'sort_order': 4,
        }
    )


def remove_normal_user_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    GroupProfile = apps.get_model('accounts', 'GroupProfile')

    group = Group.objects.filter(name='普通用户').first()
    if group:
        GroupProfile.objects.filter(group=group).delete()
        group.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_default_groups'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            add_normal_user_group,
            remove_normal_user_group,
        ),
    ]
