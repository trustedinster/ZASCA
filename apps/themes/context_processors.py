"""
主题上下文处理器

将主题配置和页面内容注入到所有模板上下文中
使用缓存优化性能
"""
from .models import ThemeConfig, PageContent


def theme_context(request):
    """
    主题上下文处理器

    注入以下变量到模板：
    - theme_config: ThemeConfig 实例
    - page_contents: {position: PageContent} 字典
    - theme_css_url: 当前主题的 CSS 文件路径
    - custom_css_vars: 自定义 CSS 变量字符串

    Returns:
        dict: 模板上下文变量
    """
    # 获取主题配置（带缓存）
    config = ThemeConfig.get_config()

    # 获取所有启用的页面内容（带缓存）
    contents = PageContent.get_all_enabled()

    # 构建 CSS 文件路径
    theme_css_url = f'css/themes/{config.active_theme}.css'

    # 生成自定义 CSS 变量
    custom_css_vars = config.generate_css_variables()

    return {
        'theme_config': config,
        'page_contents': contents,
        'theme_css_url': theme_css_url,
        'custom_css_vars': custom_css_vars,
    }
