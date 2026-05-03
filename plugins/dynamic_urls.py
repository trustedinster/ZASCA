from django.urls import path, include

from plugins.core.plugin_manager import get_plugin_manager
from plugins.core.base import URLProvider


def get_plugin_admin_urls():
    pm = get_plugin_manager()
    patterns = pm.get_plugin_url_patterns(
        URLProvider.ADMIN
    )
    result = []
    for p in patterns:
        result.append(
            path(
                p['prefix'],
                include(p['module']),
            )
        )
    return result


def get_plugin_provider_urls():
    pm = get_plugin_manager()
    patterns = pm.get_plugin_url_patterns(
        URLProvider.PROVIDER
    )
    result = []
    for p in patterns:
        result.append(
            path(
                p['prefix'],
                include(p['module']),
            )
        )
    return result
