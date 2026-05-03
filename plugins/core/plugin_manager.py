import os
import sys
import importlib
import inspect
import logging
from typing import Dict, List, Type, Any, Optional, Set
from pathlib import Path
from django.conf import settings
from .base import (
    PluginInterface,
    EventHook,
    ServiceProvider,
    ServiceRegistry,
    UIExtension,
    UIExtensionProvider,
    URLProvider,
)

logger = logging.getLogger(__name__)


class PluginManager:
    def __init__(self):
        self.plugins: Dict[str, PluginInterface] = {}
        self.hooks: Dict[str, EventHook] = {}
        self.loaded_modules: Set[str] = set()
        self.service_registry = ServiceRegistry()
        self._ui_extensions: Dict[
            str, List[UIExtension]
        ] = {}

    def discover_builtin_plugins(self) -> Dict[str, dict]:
        from ..available_plugins import ALL_AVAILABLE_PLUGINS
        return ALL_AVAILABLE_PLUGINS

    def load_builtin_plugin(self, plugin_key: str, plugin_info: dict) -> Optional[PluginInterface]:
        if not plugin_info.get('enabled', True):
            logger.info(f"插件 {plugin_key} 已禁用，跳过加载")
            return None

        try:
            module_path = plugin_info['module']
            class_name = plugin_info['class']

            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)

            if (inspect.isclass(plugin_class) and
                issubclass(plugin_class, PluginInterface) and
                plugin_class != PluginInterface):

                plugin_instance = plugin_class()
                self.plugins[plugin_instance.plugin_id] = plugin_instance

                if isinstance(plugin_instance, ServiceProvider):
                    self.service_registry.register(plugin_instance)

                logger.info(f"成功加载插件: {plugin_instance.name} (ID: {plugin_instance.plugin_id})")
                return plugin_instance
            else:
                logger.error(f"模块 {module_path} 中的 {class_name} 不是一个有效的插件类")
                return None

        except ImportError as e:
            logger.error(f"无法导入插件模块 {plugin_info['module']}: {str(e)}")
            return None
        except AttributeError as e:
            logger.error(f"模块 {plugin_info['module']} 中找不到类 {plugin_info['class']}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"加载插件 {plugin_key} 时发生错误: {str(e)}")
            return None

    def load_all_builtin_plugins(self):
        builtin_plugins = self.discover_builtin_plugins()

        for plugin_key, plugin_info in builtin_plugins.items():
            plugin = self.load_builtin_plugin(plugin_key, plugin_info)
            if plugin:
                try:
                    if not plugin.initialize():
                        logger.warning(f"插件 {plugin.name} 初始化失败")
                except Exception as e:
                    logger.error(f"插件 {plugin.name} 初始化时发生错误: {str(e)}")

    def unload_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self.plugins:
            logger.warning(f"插件 {plugin_id} 不存在")
            return False

        plugin = self.plugins[plugin_id]

        try:
            if isinstance(plugin, ServiceProvider):
                self.service_registry.unregister(plugin.get_service_name())

            if not plugin.shutdown():
                logger.warning(f"插件 {plugin.name} 关闭时返回失败状态")

            del self.plugins[plugin_id]

            logger.info(f"插件 {plugin.name} (ID: {plugin_id}) 已卸载")
            return True
        except Exception as e:
            logger.error(f"卸载插件 {plugin_id} 时发生错误: {str(e)}")
            return False

    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        return self.plugins.get(plugin_id)

    def get_all_plugins(self) -> Dict[str, PluginInterface]:
        return self.plugins.copy()

    def get_plugin_metadata(self) -> List[Dict[str, Any]]:
        metadata_list = []
        for plugin in self.plugins.values():
            metadata_list.append(plugin.metadata)
        return metadata_list

    def get_service(self, service_name: str) -> Optional[Any]:
        return self.service_registry.get(service_name)

    def get_services_by_interface(self, interface: Type) -> List[Any]:
        return self.service_registry.get_by_interface(interface)

    def list_services(self) -> Dict[str, Any]:
        return self.service_registry.list_services()

    def register_hook(self, hook_name: str) -> EventHook:
        if hook_name not in self.hooks:
            self.hooks[hook_name] = EventHook(hook_name)
        return self.hooks[hook_name]

    def get_hook(self, hook_name: str) -> Optional[EventHook]:
        return self.hooks.get(hook_name)

    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        hook = self.get_hook(hook_name)
        if hook:
            return hook.execute(*args, **kwargs)
        return []

    def start_all_plugins(self):
        for plugin_id, plugin in self.plugins.items():
            try:
                if not plugin.initialize():
                    logger.warning(
                        f"插件 {plugin.name} 启动失败"
                    )
            except Exception as e:
                logger.error(
                    f"启动插件 {plugin.name} "
                    f"时发生错误: {str(e)}"
                )

    def _collect_ui_extensions(self):
        self._ui_extensions.clear()
        for plugin in self.plugins.values():
            if isinstance(plugin, UIExtensionProvider):
                try:
                    exts = plugin.get_ui_extensions()
                    for ext in exts:
                        slot = ext.slot
                        if slot not in self._ui_extensions:
                            self._ui_extensions[slot] = []
                        self._ui_extensions[slot].append(ext)
                except Exception as e:
                    logger.error(
                        f"收集插件 {plugin.name} "
                        f"UI扩展失败: {str(e)}"
                    )
        for slot in self._ui_extensions:
            self._ui_extensions[slot].sort(
                key=lambda e: e.order
            )

    def get_ui_extensions(
        self, slot: str
    ) -> List[UIExtension]:
        if not self._ui_extensions:
            self._collect_ui_extensions()
        return self._ui_extensions.get(slot, [])

    def get_all_ui_slots(self) -> List[str]:
        if not self._ui_extensions:
            self._collect_ui_extensions()
        return list(self._ui_extensions.keys())

    def get_plugin_url_patterns(
        self, section: str
    ) -> List[dict]:
        patterns = []
        for plugin in self.plugins.values():
            if isinstance(plugin, URLProvider):
                try:
                    for p in plugin.get_url_patterns():
                        if p.get('section') == section:
                            patterns.append(p)
                except Exception as e:
                    logger.error(
                        f"收集插件 {plugin.name} "
                        f"URL失败: {str(e)}"
                    )
        return patterns

    def stop_all_plugins(self):
        for plugin_id in reversed(list(self.plugins.keys())):
            plugin = self.plugins[plugin_id]
            try:
                if not plugin.shutdown():
                    logger.warning(f"插件 {plugin.name} 停止时返回失败状态")
            except Exception as e:
                logger.error(f"停止插件 {plugin.name} 时发生错误: {str(e)}")


plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    return plugin_manager
