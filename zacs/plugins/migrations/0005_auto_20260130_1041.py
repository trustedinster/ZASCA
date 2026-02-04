# 修复依赖问题的占位迁移文件
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('plugins', '0003_auto_20260129_1808'),
    ]

    operations = [
        # 占位操作，不实际改变数据库
        migrations.RunSQL(migrations.RunSQL.noop, reverse_sql=migrations.RunSQL.noop),
    ]