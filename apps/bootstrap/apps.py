from django.apps import AppConfig


class BootstrapConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bootstrap'
    verbose_name = '主机引导系统'
    
    def ready(self):
        # 导入信号处理器
        import apps.bootstrap.signals