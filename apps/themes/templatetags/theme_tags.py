"""
主题系统模板标签

提供便捷的模板标签获取主题配置和页面内容
"""
from django import template
from django.utils.safestring import mark_safe
from ..models import ThemeConfig, PageContent

register = template.Library()


@register.simple_tag
def get_content(position, default=''):
    """
    获取指定位置的页面内容

    用法:
        {% load theme_tags %}
        {% get_content 'login_welcome' as welcome_msg %}
        {{ welcome_msg }}

        或直接输出:
        {% get_content 'footer_text' '默认页脚' %}

    Args:
        position: 位置标识符
        default: 默认值

    Returns:
        str: 内容文本
    """
    return PageContent.get_content(position, default)


@register.simple_tag
def get_content_obj(position):
    """
    获取指定位置的 PageContent 对象

    用法:
        {% get_content_obj 'dashboard_notice' as notice %}
        {% if notice %}
            <h3>{{ notice.title }}</h3>
            {{ notice.content|safe }}
        {% endif %}

    Args:
        position: 位置标识符

    Returns:
        PageContent 或 None
    """
    contents = PageContent.get_all_enabled()
    return contents.get(position)


@register.simple_tag
def theme_css_url():
    """
    获取当前主题的 CSS 文件 URL

    用法:
        <link rel="stylesheet" href="{% static theme_css_url %}">

    Returns:
        str: CSS 文件路径
    """
    config = ThemeConfig.get_config()
    return f'css/themes/{config.active_theme}.css'


@register.simple_tag
def theme_data_attribute():
    """
    获取用于 HTML 标签的 data-theme 属性值

    用法:
        <html data-theme="{% theme_data_attribute %}">

    Returns:
        str: 主题标识符
    """
    config = ThemeConfig.get_config()
    return config.active_theme


@register.simple_tag
def branding(key, default=''):
    """
    获取品牌资源路径

    用法:
        <img src="{% branding 'logo' '/static/img/default-logo.png' %}">

    Args:
        key: 资源键名 (logo, logo_dark, favicon, login_bg)
        default: 默认路径

    Returns:
        str: 资源路径
    """
    config = ThemeConfig.get_config()
    return config.get_branding(key, default)


@register.simple_tag
def theme_color(key, default=''):
    """
    获取自定义颜色值

    用法:
        <div style="background-color: {% theme_color 'primary' '#6750A4' %}">

    Args:
        key: 颜色键名
        default: 默认颜色值

    Returns:
        str: 颜色值
    """
    config = ThemeConfig.get_config()
    return config.get_color(key, default)


@register.simple_tag
def custom_css_variables():
    """
    输出自定义 CSS 变量样式块

    用法:
        <head>
            <style>{% custom_css_variables %}</style>
        </head>

    Returns:
        str: CSS 变量定义
    """
    config = ThemeConfig.get_config()
    css = config.generate_css_variables()
    if config.css_overrides:
        css += '\n' + config.css_overrides
    return mark_safe(css)


@register.inclusion_tag('themes/partials/theme_head.html')
def theme_head():
    """
    包含主题相关的 <head> 内容

    用法:
        <head>
            {% theme_head %}
        </head>

    Returns:
        dict: 模板上下文
    """
    config = ThemeConfig.get_config()
    return {
        'theme_config': config,
        'theme_css_url': f'css/themes/{config.active_theme}.css',
        'custom_css': config.generate_css_variables(),
        'css_overrides': config.css_overrides,
    }


@register.filter
def is_mobile_enabled(config):
    """
    检查是否启用移动端优化

    用法:
        {% if theme_config|is_mobile_enabled %}
            <link rel="stylesheet" href="{% static 'css/themes/_responsive.css' %}">
        {% endif %}

    Args:
        config: ThemeConfig 实例

    Returns:
        bool
    """
    if config is None:
        return True
    return getattr(config, 'enable_mobile_optimization', True)
