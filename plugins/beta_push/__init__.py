import os
import logging

from plugins.core.base import PluginInterface, URLProvider, UIExtension, UIExtensionProvider

logger = logging.getLogger(__name__)


class BetaPushPlugin(PluginInterface, URLProvider, UIExtensionProvider):

    def __init__(self):
        super().__init__(
            plugin_id='beta_push',
            name='Beta数据推送',
            version='1.0.0',
            description='将生产环境数据异步推送到Beta版本数据库，支持增量同步',
        )

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> bool:
        return True

    def get_url_patterns(self):
        return [
            {
                'prefix': 'beta-push/',
                'module': 'plugins.beta_push.urls',
                'namespace': 'beta_push',
                'section': URLProvider.PROVIDER,
            },
        ]

    def get_ui_extensions(self):
        return [
            UIExtension(
                extension_type=UIExtension.NAV_ITEM,
                slot='admin_sidebar_plugins',
                html=(
                    '<a href="/provider/plugins/beta-push/" '
                    'class="flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition text-white/70 hover:bg-white/5 hover:text-white">'
                    '<span class="material-symbols-rounded text-lg shrink-0 text-cyan-400">sync_alt</span>'
                    '<span>Beta推送</span>'
                    '</a>'
                ),
                order=10,
            ),
        ]


def is_beta_db_configured():
    return bool(os.environ.get('BETA_DB_NAME', ''))
