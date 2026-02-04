"""
操作记录应用配置
"""
from django.apps import AppConfig


class OperationsConfig(AppConfig):
    """操作记录应用配置类"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.operations'
    verbose_name = '操作记录'
