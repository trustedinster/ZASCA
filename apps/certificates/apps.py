from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.certificates'
    verbose_name = '证书管理系统'
    
    def ready(self):
        # 导入信号处理器
        import apps.certificates.signals