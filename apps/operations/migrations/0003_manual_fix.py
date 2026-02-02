# 数据库结构修复迁移
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0002_publichostinfo'),
    ]

    operations = [
        # 我们不删除不存在的字段，而是什么都不做
        # 这样可以标记迁移为已应用，避免错误
        migrations.RunSQL('SELECT 1;', reverse_sql='SELECT 1;'),
    ]
