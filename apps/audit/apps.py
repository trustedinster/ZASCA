from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = '审计日志系统'
    
    def ready(self):
        # 导入信号处理器
        import apps.audit.signals