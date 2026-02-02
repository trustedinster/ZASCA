import os
from celery import Celery
from django.conf import settings

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('zasca')
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

# 任务序列化配置
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# 队列配置
app.conf.task_routes = {
    'certificates.tasks.*': {'queue': 'certificates'},
    'hosts.tasks.*': {'queue': 'hosts'},
    'operations.tasks.*': {'queue': 'operations'},
    'bootstrap.tasks.*': {'queue': 'bootstrap'},
}

# 任务重试配置
app.conf.task_default_retry_delay = 30  # 默认重试延迟30秒
app.conf.task_max_retries = 3           # 最大重试次数3次