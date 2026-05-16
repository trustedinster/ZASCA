import os
import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class BetaPushConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.beta_push'
    verbose_name = 'Beta数据推送'

    def ready(self):
        self._configure_beta_database()

    def _configure_beta_database(self):
        beta_db_name = os.environ.get('BETA_DB_NAME', '')
        if not beta_db_name:
            return

        if 'beta' in settings.DATABASES:
            return

        default_db = settings.DATABASES.get('default', {})
        engine = default_db.get('ENGINE', '')

        if engine not in (
            'django.db.backends.mysql',
            'django.db.backends.postgresql',
        ):
            logger.warning(
                'Beta推送插件仅支持MySQL/PostgreSQL架构，'
                '当前默认数据库引擎不是受支持的引擎'
            )
            return

        beta_db = {
            'NAME': beta_db_name,
            'USER': os.environ.get('BETA_DB_USER', default_db.get('USER', '')),
            'PASSWORD': os.environ.get('BETA_DB_PASSWORD', default_db.get('PASSWORD', '')),
            'HOST': os.environ.get('BETA_DB_HOST', default_db.get('HOST', '127.0.0.1')),
            'PORT': os.environ.get('BETA_DB_PORT', default_db.get('PORT', '3306')),
            'CONN_MAX_AGE': int(os.environ.get('BETA_DB_CONN_MAX_AGE', '60')),
        }

        if engine == 'django.db.backends.mysql':
            beta_db['ENGINE'] = 'django.db.backends.mysql'
            beta_db['OPTIONS'] = {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            }
        elif engine == 'django.db.backends.postgresql':
            beta_db['ENGINE'] = 'django.db.backends.postgresql'

        settings.DATABASES['beta'] = beta_db
        logger.info(f'Beta数据库已配置: {beta_db_name}')
