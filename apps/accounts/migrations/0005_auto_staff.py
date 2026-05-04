from django.db import migrations, models


AUTO_STAFF_GROUPS = ['超管', '主机提供商', '云电脑审批', '工单技术客服']


def set_auto_staff(apps, schema_editor):
    GroupProfile = apps.get_model('accounts', 'GroupProfile')
    GroupProfile.objects.filter(
        group__name__in=AUTO_STAFF_GROUPS
    ).update(auto_staff=True)

    User = apps.get_model('accounts', 'User')
    for user in User.objects.filter(is_superuser=True, is_staff=False):
        user.is_staff = True
        user.save(update_fields=['is_staff'])

    for profile in GroupProfile.objects.filter(auto_staff=True):
        for user in profile.group.user_set.filter(is_staff=False):
            user.is_staff = True
            user.save(update_fields=['is_staff'])


def unset_auto_staff(apps, schema_editor):
    GroupProfile = apps.get_model('accounts', 'GroupProfile')
    GroupProfile.objects.filter(auto_staff=True).update(auto_staff=False)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_normal_user_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupprofile',
            name='auto_staff',
            field=models.BooleanField(
                default=False,
                help_text='勾选后，属于该组的用户将自动获得员工身份(is_staff)',
                verbose_name='自动员工',
            ),
        ),
        migrations.RunPython(set_auto_staff, unset_auto_staff),
    ]
