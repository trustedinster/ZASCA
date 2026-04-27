from django.apps import AppConfig


class TicketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tickets'
    verbose_name = '工单系统'

    def ready(self):
        """
        应用就绪时导入信号处理器
        """
        import apps.tickets.signals  # noqa: F401
