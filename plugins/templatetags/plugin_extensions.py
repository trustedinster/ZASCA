import logging

from django import template
from django.utils.safestring import mark_safe

from plugins.core.plugin_manager import get_plugin_manager

register = template.Library()
logger = logging.getLogger(__name__)


@register.simple_tag(takes_context=True)
def plugin_extensions(context, slot):
    """
    在模板中渲染指定 slot 的所有插件 UI 扩展。

    用法:
        {% load plugin_extensions %}
        {% plugin_extensions "host_form_after_auth" %}
    """
    pm = get_plugin_manager()
    extensions = pm.get_ui_extensions(slot)

    if not extensions:
        return ''

    request = context.get('request')

    parts = []
    for ext in extensions:
        try:
            rendered = ext.render(request=request)
            if rendered:
                parts.append(rendered)
        except Exception as e:
            logger.error(
                f"渲染 UI 扩展失败 "
                f"(slot={slot}, "
                f"type={ext.extension_type}): {e}"
            )

    return mark_safe(''.join(parts))


@register.simple_tag(takes_context=True)
def plugin_nav_items(context):
    """
    渲染所有插件注册的导航项扩展。

    用法:
        {% load plugin_extensions %}
        {% plugin_nav_items %}
    """
    pm = get_plugin_manager()
    extensions = pm.get_ui_extensions(
        'admin_sidebar_plugins'
    )

    if not extensions:
        return ''

    request = context.get('request')
    parts = []
    for ext in extensions:
        try:
            rendered = ext.render(request=request)
            if rendered:
                parts.append(rendered)
        except Exception as e:
            logger.error(
                f"渲染导航扩展失败: {e}"
            )

    return mark_safe(''.join(parts))


@register.simple_tag(takes_context=True)
def plugin_has_extensions(context, slot):
    """
    判断指定 slot 是否有插件注册了扩展。

    用法:
        {% load plugin_extensions %}
        {% plugin_has_extensions "host_form_after_auth" as has_ext %}
        {% if has_ext %}
            ...
        {% endif %}
    """
    pm = get_plugin_manager()
    extensions = pm.get_ui_extensions(slot)
    return len(extensions) > 0
