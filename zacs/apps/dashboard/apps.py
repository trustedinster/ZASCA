"""
仪表盘应用配置
"""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """仪表盘应用配置类"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = '仪表盘'

    def ready(self):
        """应用就绪时注册信号"""
        import apps.dashboard.signals
