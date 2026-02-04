"""
WinRM 连接迁移
添加证书验证字段到 Host 模型
"""

from django.db import migrations, models


def add_default_cert_validation(apps, schema_editor):
    """为现有主机设置默认的证书验证模式"""
    Host = apps.get_model('hosts', 'Host')
    Host.objects.all().update(
        server_cert_validation='ignore',
        ca_cert_path='',
        client_cert_path='',
        client_key_path=''
    )


class Migration(migrations.Migration):

    dependencies = [
        ('hosts', '0005_host_connection_type_alter_host_port'),
    ]

    operations = [
        migrations.AddField(
            model_name='host',
            name='server_cert_validation',
            field=models.CharField(choices=[('ignore', '忽略证书'), ('validate', '验证证书')], default='ignore', max_length=20, verbose_name='证书验证模式'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='host',
            name='ca_cert_path',
            field=models.CharField(blank=True, max_length=500, verbose_name='CA证书路径'),
        ),
        migrations.AddField(
            model_name='host',
            name='client_cert_path',
            field=models.CharField(blank=True, max_length=500, verbose_name='客户端证书路径'),
        ),
        migrations.AddField(
            model_name='host',
            name='client_key_path',
            field=models.CharField(blank=True, max_length=500, verbose_name='客户端私钥路径'),
        ),
        migrations.RunPython(add_default_cert_validation),
    ]