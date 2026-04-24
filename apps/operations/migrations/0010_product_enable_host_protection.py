from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0009_rdpdomainroute'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='enable_host_protection',
            field=models.BooleanField(
                default=False,
                help_text=(
                    '启用后，用户只能通过Gateway隧道访问该产品的RDP，'
                    '主机不暴露公网IP。需要部署Gateway服务。'
                ),
                verbose_name='启用主机保护(通过Gateway)'
            ),
        ),
    ]
