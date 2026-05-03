from django.db import migrations, models
import hashlib
import base64


def _get_fernet():
    from django.conf import settings
    from cryptography.fernet import Fernet
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_existing_passwords(apps, schema_editor):
    CloudComputerUser = apps.get_model('operations', 'CloudComputerUser')
    fernet = _get_fernet()
    for user in CloudComputerUser.objects.filter(
        _initial_password__isnull=False
    ).exclude(_initial_password=''):
        try:
            fernet.decrypt(user._initial_password.encode())
        except Exception:
            encrypted = fernet.encrypt(user._initial_password.encode()).decode()
            CloudComputerUser.objects.filter(pk=user.pk).update(
                _initial_password=encrypted
            )


def decrypt_passwords_back(apps, schema_editor):
    CloudComputerUser = apps.get_model('operations', 'CloudComputerUser')
    fernet = _get_fernet()
    for user in CloudComputerUser.objects.filter(
        _initial_password__isnull=False
    ).exclude(_initial_password=''):
        try:
            decrypted = fernet.decrypt(user._initial_password.encode()).decode()
            CloudComputerUser.objects.filter(pk=user.pk).update(
                _initial_password=decrypted
            )
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0013_productgroup_created_by'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cloudcomputeruser',
            name='initial_password',
        ),
        migrations.AddField(
            model_name='cloudcomputeruser',
            name='_initial_password',
            field=models.CharField(blank=True, db_column='initial_password', help_text='用户的初始密码(加密存储)，查看后将被清除', max_length=512, verbose_name='初始密码(加密)'),
        ),
        migrations.RunPython(encrypt_existing_passwords, decrypt_passwords_back),
    ]
