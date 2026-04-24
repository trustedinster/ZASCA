from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hosts', '0008_add_providers_to_host_and_hostgroup'),
    ]

    operations = [
        migrations.AddField(
            model_name='host',
            name='tunnel_token',
            field=models.CharField(
                blank=True, max_length=64, null=True,
                unique=True, verbose_name='隧道Token'
            ),
        ),
        migrations.AddField(
            model_name='host',
            name='tunnel_status',
            field=models.CharField(
                choices=[
                    ('no_tunnel', '无隧道'),
                    ('offline', '隧道离线'),
                    ('online', '隧道在线'),
                    ('error', '隧道错误'),
                ],
                default='no_tunnel', max_length=20,
                verbose_name='隧道状态'
            ),
        ),
        migrations.AddField(
            model_name='host',
            name='tunnel_connected_at',
            field=models.DateTimeField(
                blank=True, null=True, verbose_name='隧道连接时间'
            ),
        ),
        migrations.AddField(
            model_name='host',
            name='tunnel_last_seen_at',
            field=models.DateTimeField(
                blank=True, null=True, verbose_name='隧道最后心跳'
            ),
        ),
        migrations.AddField(
            model_name='host',
            name='tunnel_client_version',
            field=models.CharField(
                blank=True, max_length=50,
                verbose_name='隧道客户端版本'
            ),
        ),
        migrations.AddField(
            model_name='host',
            name='tunnel_client_ip',
            field=models.GenericIPAddressField(
                blank=True, null=True,
                verbose_name='隧道客户端IP'
            ),
        ),
        migrations.AddField(
            model_name='host',
            name='tunnel_public_key',
            field=models.TextField(
                blank=True, verbose_name='隧道公钥(Ed25519)'
            ),
        ),
        migrations.AlterField(
            model_name='host',
            name='connection_type',
            field=models.CharField(
                choices=[
                    ('winrm', 'WinRM'),
                    ('ssh', 'SSH'),
                    ('localwinserver', '本地WinServer'),
                    ('tunnel', '隧道模式(零公网IP)'),
                ],
                default='winrm', max_length=20,
                verbose_name='连接类型'
            ),
        ),
    ]
