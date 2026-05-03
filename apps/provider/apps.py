from django.apps import AppConfig


class ProviderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.provider'
    verbose_name = '提供商后台'
    label = 'provider'
