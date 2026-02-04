from django.apps import AppConfig


class ErrorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.errors'
    verbose_name = '错误处理'