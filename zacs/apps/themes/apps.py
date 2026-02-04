"""
主题应用配置
"""
from django.apps import AppConfig


class ThemesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.themes'
    verbose_name = '主题管理'

    def ready(self):
        """应用启动时执行"""
        # 可以在这里注册信号等
        pass
