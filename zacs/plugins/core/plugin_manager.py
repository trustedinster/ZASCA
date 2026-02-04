"""
插件管理系统

实现插件的动态加载、管理和运行时控制
"""

import os
import sys
import importlib
import inspect
from typing import Dict, List, Type, Any, Optional, Set
from pathlib import Path
from django.conf import settings
from .base import PluginInterface, EventHook  # 修正导入路径
import logging

logger = logging.getLogger(__name__)


class PluginManager:
    """
    插件管理器
    负责插件的加载、初始化、运行和卸载
    """
    
    def __init__(self):
        self.plugins: Dict[str, PluginInterface] = {}
        self.hooks: Dict[str, EventHook] = {}
        self.loaded_modules: Set[str] = set()
        
    def discover_builtin_plugins(self) -> Dict[str, dict]:
        """
        发现系统内置插件
        """
        from ..available_plugins import ALL_AVAILABLE_PLUGINS
        return ALL_AVAILABLE_PLUGINS
    
    def load_builtin_plugin(self, plugin_key: str, plugin_info: dict) -> Optional[PluginInterface]:
        """
        加载内置插件
        """
        if not plugin_info.get('enabled', True):
            logger.info(f"插件 {plugin_key} 已禁用，跳过加载")
            return None
            
        try:
            module_path = plugin_info['module']
            class_name = plugin_info['class']
            
            # 动态导入模块
            module = importlib.import_module(module_path)
            
            # 获取插件类
            plugin_class = getattr(module, class_name)
            
            # 检查是否是有效的插件类
            if (inspect.isclass(plugin_class) and 
                issubclass(plugin_class, PluginInterface) and 
                plugin_class != PluginInterface):
                
                # 实例化插件
                plugin_instance = plugin_class()
                
                # 添加到插件字典
                self.plugins[plugin_instance.plugin_id] = plugin_instance
                
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
        """
        加载所有内置插件
        """
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
        """
        卸载指定插件
        """
        if plugin_id not in self.plugins:
            logger.warning(f"插件 {plugin_id} 不存在")
            return False
            
        plugin = self.plugins[plugin_id]
        
        try:
            # 关闭插件
            if not plugin.shutdown():
                logger.warning(f"插件 {plugin.name} 关闭时返回失败状态")
                
            # 从管理器中移除
            del self.plugins[plugin_id]
            
            logger.info(f"插件 {plugin.name} (ID: {plugin_id}) 已卸载")
            return True
        except Exception as e:
            logger.error(f"卸载插件 {plugin_id} 时发生错误: {str(e)}")
            return False
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """
        获取指定插件实例
        """
        return self.plugins.get(plugin_id)
    
    def get_all_plugins(self) -> Dict[str, PluginInterface]:
        """
        获取所有已加载的插件
        """
        return self.plugins.copy()
    
    def get_plugin_metadata(self) -> List[Dict[str, Any]]:
        """
        获取所有插件的元数据
        """
        metadata_list = []
        for plugin in self.plugins.values():
            metadata_list.append(plugin.metadata)
        return metadata_list
    
    def register_hook(self, hook_name: str) -> EventHook:
        """
        注册一个事件钩子
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = EventHook(hook_name)
        return self.hooks[hook_name]
    
    def get_hook(self, hook_name: str) -> Optional[EventHook]:
        """
        获取事件钩子
        """
        return self.hooks.get(hook_name)
    
    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        触发事件钩子
        """
        hook = self.get_hook(hook_name)
        if hook:
            return hook.execute(*args, **kwargs)
        return []
    
    def start_all_plugins(self):
        """
        启动所有插件
        """
        for plugin_id, plugin in self.plugins.items():
            try:
                if not plugin.initialize():
                    logger.warning(f"插件 {plugin.name} 启动失败")
            except Exception as e:
                logger.error(f"启动插件 {plugin.name} 时发生错误: {str(e)}")
    
    def stop_all_plugins(self):
        """
        停止所有插件
        """
        # 按相反顺序停止插件（如果有必要的话）
        for plugin_id in reversed(list(self.plugins.keys())):
            plugin = self.plugins[plugin_id]
            try:
                if not plugin.shutdown():
                    logger.warning(f"插件 {plugin.name} 停止时返回失败状态")
            except Exception as e:
                logger.error(f"停止插件 {plugin.name} 时发生错误: {str(e)}")


# 全局插件管理器实例
plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    """
    获取插件管理器实例
    """
    return plugin_manager