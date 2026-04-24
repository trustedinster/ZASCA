from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('operations', '0008_accountopeningrequest_requested_disk_capacity_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RdpDomainRoute',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID'
                )),
                ('domain', models.CharField(
                    max_length=255, unique=True,
                    verbose_name='RDP域名',
                    help_text='分配给用户的临时RDP访问域名'
                )),
                ('tunnel_token', models.CharField(
                    max_length=64, verbose_name='隧道Token',
                    help_text='关联主机的隧道Token'
                )),
                ('is_active', models.BooleanField(
                    default=True, verbose_name='是否有效',
                    help_text='域名是否仍然有效'
                )),
                ('expires_at', models.DateTimeField(
                    verbose_name='过期时间',
                    help_text='域名过期时间，10分钟无连接后过期'
                )),
                ('last_activity_at', models.DateTimeField(
                    auto_now=True, verbose_name='最后活动时间',
                    help_text='最后一次RDP连接活动时间'
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True, verbose_name='创建时间'
                )),
                ('assigned_to', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='分配用户',
                    help_text='被分配此RDP域名的用户'
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='operations.product',
                    verbose_name='关联产品',
                    help_text='此域名关联的云电脑产品'
                )),
            ],
            options={
                'verbose_name': 'RDP域名路由',
                'verbose_name_plural': 'RDP域名路由',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='rdpdomainroute',
            index=models.Index(fields=['domain'], name='operations_rdp_domain_idx'),
        ),
        migrations.AddIndex(
            model_name='rdpdomainroute',
            index=models.Index(fields=['is_active'], name='operations_rdp_active_idx'),
        ),
        migrations.AddIndex(
            model_name='rdpdomainroute',
            index=models.Index(fields=['assigned_to'], name='operations_rdp_user_idx'),
        ),
        migrations.AddIndex(
            model_name='rdpdomainroute',
            index=models.Index(fields=['expires_at'], name='operations_rdp_expires_idx'),
        ),
        migrations.AddIndex(
            model_name='rdpdomainroute',
            index=models.Index(fields=['product'], name='operations_rdp_product_idx'),
        ),
    ]
