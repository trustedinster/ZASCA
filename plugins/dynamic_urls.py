from django.urls import path, include

from plugins.core.plugin_manager import get_plugin_manager
from plugins.core.base import URLProvider


def _build_url_list(section):
    pm = get_plugin_manager()
    patterns = pm.get_plugin_url_patterns(section)
    result = []
    for p in patterns:
        namespace = p.get('namespace', '')
        if namespace:
            result.append(
                path(
                    p['prefix'],
                    include(p['module'], namespace),
                )
            )
        else:
            result.append(
                path(
                    p['prefix'],
                    include(p['module']),
                )
            )
    return result


def get_plugin_admin_urls():
    return _build_url_list(URLProvider.ADMIN)


def get_plugin_provider_urls():
    return _build_url_list(URLProvider.PROVIDER)
