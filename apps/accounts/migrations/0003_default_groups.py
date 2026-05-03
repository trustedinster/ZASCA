from django.db import migrations


DEFAULT_GROUPS = [
    {
        'name': '超管',
        'description': '系统超级管理员，拥有所有权限。对应Django的is_superuser属性。',
        'is_default': True,
        'sort_order': 0,
    },
    {
        'name': '主机提供商',
        'description': '主机提供商，可管理分配给自己的主机、产品、开户申请和工单。',
        'is_default': True,
        'sort_order': 1,
        'rename_from': '提供商',
    },
    {
        'name': '云电脑审批',
        'description': '云电脑审批人员，可管理开户申请和工单系统。',
        'is_default': True,
        'sort_order': 2,
    },
    {
        'name': '工单技术客服',
        'description': '工单技术客服，仅可管理工单系统。',
        'is_default': True,
        'sort_order': 3,
    },
    {
        'name': '普通用户',
        'description': '普通用户，可使用已授权的产品和服务。',
        'is_default': True,
        'sort_order': 4,
    },
]


def create_default_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    GroupProfile = apps.get_model('accounts', 'GroupProfile')

    for group_data in DEFAULT_GROUPS:
        rename_from = group_data.pop('rename_from', None)

        if rename_from:
            existing = Group.objects.filter(name=rename_from).first()
            if existing:
                existing.name = group_data['name']
                existing.save()
                group = existing
            else:
                group, _ = Group.objects.get_or_create(
                    name=group_data['name']
                )
        else:
            group, _ = Group.objects.get_or_create(
                name=group_data['name']
            )

        GroupProfile.objects.get_or_create(
            group=group,
            defaults={
                'is_default': group_data['is_default'],
                'description': group_data['description'],
                'sort_order': group_data['sort_order'],
            }
        )


def reverse_default_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    GroupProfile = apps.get_model('accounts', 'GroupProfile')

    for group_data in DEFAULT_GROUPS:
        group = Group.objects.filter(name=group_data['name']).first()
        if group:
            GroupProfile.objects.filter(group=group).delete()

    provider_group = Group.objects.filter(name='主机提供商').first()
    if provider_group:
        provider_group.name = '提供商'
        provider_group.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_groupprofile_model'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            create_default_groups,
            reverse_default_groups,
        ),
    ]
