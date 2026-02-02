"""
用户管理应用配置
"""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """用户管理应用配置类"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = '用户管理'

    def ready(self):
        """应用就绪时执行的初始化操作"""
        # 导入信号处理器
        try:
            import apps.accounts.signals
        except ImportError:
            pass
