from django.apps import AppConfig


class ProviderBackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.provider_backend'
    verbose_name = '提供商后台'
