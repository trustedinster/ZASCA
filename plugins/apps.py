"""
插件应用配置
"""

from django.apps import AppConfig


class PluginsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins'
    verbose_name = '插件管理'

    def ready(self):
        # 导入信号处理器
        import plugins.signals
        
        # 初始化插件管理器并加载所有插件
        from .core.plugin_manager import get_plugin_manager
        plugin_manager = get_plugin_manager()
        plugin_manager.load_all_builtin_plugins()