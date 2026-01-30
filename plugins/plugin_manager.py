"""
插件管理系统管理器
负责插件的加载、卸载、管理和执行
"""

import os
import sys
import importlib.util
from typing import Any, Dict, List, Optional, Type

from plugins.core.base import PluginInterface, EventHook


class PluginManager:
    """
    插件管理器
    负责管理所有插件的生命周期
    """
    
    def __init__(self):
        self.plugins: Dict[str, PluginInterface] = {}
        self.hooks: Dict[str, EventHook] = {}
        self.plugin_dirs: List[str] = []
        
    def _get_plugin_model(self):
        """延迟导入PluginRecord模型"""
        try:
            from django.conf import settings
            # 检查Django是否已配置
            if settings.configured:
                from .models import PluginRecord
                return PluginRecord
        except (ImportError, AttributeError):
            pass
        return None
        
    def add_plugin_directory(self, directory: str):
        """添加插件目录"""
        if os.path.isdir(directory) and directory not in self.plugin_dirs:
            self.plugin_dirs.append(directory)
            
    def load_plugins_from_directory(self, directory: str) -> List[str]:
        """
        从指定目录加载插件
        :param directory: 插件目录路径
        :return: 成功加载的插件ID列表
        """
        loaded_plugins = []
        
        if not os.path.isdir(directory):
            print(f"Plugin directory does not exist: {directory}")
            return loaded_plugins
            
        # 首先检查主目录中的插件文件
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            # 检查是否是Python文件且不是__init__.py
            if os.path.isfile(item_path) and item.endswith('.py') and item != '__init__.py':
                # 跳过特定的非插件文件
                if item in ['base.py', 'models.py', 'admin.py', 'views.py', 'urls.py', 'signals.py', 'django_integration.py']:
                    continue
                    
                plugin_filename = item[:-3]  # 移除.py后缀
                module_name = f"plugins.{plugin_filename}"  # 使用不同的模块名避免冲突
                
                try:
                    # 使用 importlib.util.spec_from_file_location 动态加载模块
                    spec = importlib.util.spec_from_file_location(module_name, item_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        # 添加到 sys.modules 以支持相对导入
                        sys.modules[spec.name] = module
                        spec.loader.exec_module(module)
                        
                        # 查找插件类（继承自PluginInterface的类）
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (
                                isinstance(attr, type) and 
                                issubclass(attr, PluginInterface) and 
                                attr != PluginInterface
                            ):
                                plugin_class: Type[PluginInterface] = attr
                                
                                # 创建插件实例并初始化
                                plugin_instance = plugin_class()
                                
                                # 如果插件实例没有设置ID，则使用默认值
                                if not hasattr(plugin_instance, 'plugin_id'):
                                    plugin_instance.plugin_id = f"{plugin_filename}_{plugin_class.__name__.lower()}"
                                    
                                if self.register_plugin(plugin_instance):
                                    loaded_plugins.append(plugin_instance.plugin_id)
                                    
                except ImportError as e:
                    # 忽略导入错误（可能是非插件模块）
                    pass
                except Exception as e:
                    print(f"Error loading plugin from {item_path}: {str(e)}")
                    
        # 检查子目录，如qq_verification
        for subdir in os.listdir(directory):
            subdir_path = os.path.join(directory, subdir)
            if os.path.isdir(subdir_path):
                for item in os.listdir(subdir_path):
                    if item.endswith('.py') and item != '__init__.py':
                        item_path = os.path.join(subdir_path, item)
                        
                        # 跳过特定的非插件文件
                        if item in ['__init__.py', 'qq_checker.py']:  # qq_checker.py不是插件类
                            continue
                            
                        plugin_filename = f"{subdir}_{item[:-3]}"  # 包含子目录名
                        
                        try:
                            # 使用 importlib.util.spec_from_file_location 动态加载模块
                            spec = importlib.util.spec_from_file_location(f"plugins.{subdir}.{item[:-3]}", item_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                # 添加到 sys.modules 以支持相对导入
                                sys.modules[spec.name] = module
                                spec.loader.exec_module(module)
                                
                                # 查找插件类（继承自PluginInterface的类）
                                for attr_name in dir(module):
                                    attr = getattr(module, attr_name)
                                    if (
                                        isinstance(attr, type) and 
                                        issubclass(attr, PluginInterface) and 
                                        attr != PluginInterface
                                    ):
                                        plugin_class: Type[PluginInterface] = attr
                                        
                                        # 创建插件实例并初始化
                                        plugin_instance = plugin_class()
                                        
                                        # 如果插件实例没有设置ID，则使用默认值
                                        if not hasattr(plugin_instance, 'plugin_id'):
                                            plugin_instance.plugin_id = f"{plugin_filename}_{plugin_class.__name__.lower()}"
                                            
                                        if self.register_plugin(plugin_instance):
                                            loaded_plugins.append(plugin_instance.plugin_id)
                                            
                        except ImportError as e:
                            # 忽略导入错误（可能是非插件模块）
                            pass
                        except Exception as e:
                            print(f"Error loading plugin from {item_path}: {str(e)}")
                    
        return loaded_plugins
        
    def register_plugin(self, plugin: PluginInterface) -> bool:
        """
        注册插件
        :param plugin: 插件实例
        :return: 注册是否成功
        """
        if plugin.plugin_id in self.plugins:
            print(f"Plugin with ID {plugin.plugin_id} already exists")
            return False
            
        try:
            # 初始化插件
            if plugin.initialize():
                self.plugins[plugin.plugin_id] = plugin
                print(f"Successfully registered plugin: {plugin.name} ({plugin.plugin_id})")
                
                # 同步到数据库（如果Django可用）
                plugin_model = self._get_plugin_model()
                if plugin_model:
                    try:
                        from django.db import transaction
                        # 使用事务和原子操作
                        with transaction.atomic():
                            plugin_record, created = plugin_model.objects.get_or_create(
                                plugin_id=plugin.plugin_id,
                                defaults={
                                    'name': plugin.name,
                                    'version': plugin.version,
                                    'description': plugin.description,
                                    'is_active': plugin.enabled
                                }
                            )
                    except Exception as db_error:
                        print(f"Error syncing plugin to database: {str(db_error)}")
                
                return True
            else:
                print(f"Failed to initialize plugin: {plugin.name}")
                return False
        except Exception as e:
            print(f"Error initializing plugin {plugin.name}: {str(e)}")
            return False
            
    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件
        :param plugin_id: 插件ID
        :return: 卸载是否成功
        """
        if plugin_id not in self.plugins:
            print(f"Plugin with ID {plugin_id} does not exist")
            return False
            
        plugin = self.plugins[plugin_id]
        
        try:
            # 关闭插件
            if plugin.shutdown():
                del self.plugins[plugin_id]
                print(f"Successfully unregistered plugin: {plugin.name}")
                
                return True
            else:
                print(f"Failed to shutdown plugin: {plugin.name}")
                return False
        except Exception as e:
            print(f"Error shutting down plugin {plugin.name}: {str(e)}")
            return False
            
    def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = True
            
            # 同步到数据库（如果Django可用）
            plugin_model = self._get_plugin_model()
            if plugin_model:
                try:
                    # 使用 update 方法直接更新数据库，避免触发信号
                    rows_updated = plugin_model.objects.filter(plugin_id=plugin_id).update(is_active=True)
                    if rows_updated > 0:
                        print(f"Database updated for plugin {plugin_id} (enabled)")
                except Exception as db_error:
                    print(f"Error updating plugin status in database: {str(db_error)}")
            
            return True
        return False
        
    def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = False
            
            # 同步到数据库（如果Django可用）
            plugin_model = self._get_plugin_model()
            if plugin_model:
                try:
                    # 使用 update 方法直接更新数据库，避免触发信号
                    rows_updated = plugin_model.objects.filter(plugin_id=plugin_id).update(is_active=False)
                    if rows_updated > 0:
                        print(f"Database updated for plugin {plugin_id} (disabled)")
                except Exception as db_error:
                    print(f"Error updating plugin status in database: {str(db_error)}")
            
            return True
        return False
        
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """获取插件实例"""
        return self.plugins.get(plugin_id)
        
    def get_all_plugins(self) -> List[PluginInterface]:
        """获取所有插件"""
        return list(self.plugins.values())
        
    def get_enabled_plugins(self) -> List[PluginInterface]:
        """获取所有启用的插件"""
        return [plugin for plugin in self.plugins.values() if plugin.enabled]
        
    def load_all_plugins(self) -> List[str]:
        """
        从所有已注册的目录加载插件
        :return: 成功加载的插件ID列表
        """
        all_loaded = []
        for directory in self.plugin_dirs:
            loaded = self.load_all_plugins_from_directory(directory)
            all_loaded.extend(loaded)
        return all_loaded
        
    def load_all_plugins_from_directory(self, directory: str) -> List[str]:
        """
        从指定目录加载所有插件
        :param directory: 插件目录路径
        :return: 成功加载的插件ID列表
        """
        loaded_plugins = []
        
        if not os.path.isdir(directory):
            print(f"Plugin directory does not exist: {directory}")
            return loaded_plugins
            
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            # 检查是否是Python文件且不是__init__.py
            if os.path.isfile(item_path) and item.endswith('.py') and item != '__init__.py':
                plugin_filename = item[:-3]  # 移除.py后缀
                module_name = f"sample_plugins_{plugin_filename}"  # 使用不同的模块名避免冲突
                
                try:
                    # 使用 importlib.util.spec_from_file_location 动态加载模块
                    spec = importlib.util.spec_from_file_location(module_name, item_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        # 添加到 sys.modules 以支持相对导入
                        sys.modules[spec.name] = module
                        spec.loader.exec_module(module)
                        
                        # 查找插件类（继承自PluginInterface的类）
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (
                                isinstance(attr, type) and 
                                issubclass(attr, PluginInterface) and 
                                attr != PluginInterface
                            ):
                                plugin_class: Type[PluginInterface] = attr
                                
                                # 创建插件实例并初始化
                                plugin_instance = plugin_class()
                                
                                # 如果插件实例没有设置ID，则使用默认值
                                if not hasattr(plugin_instance, 'plugin_id'):
                                    plugin_instance.plugin_id = f"{plugin_filename}_{plugin_class.__name__.lower()}"
                                    
                                if self.register_plugin(plugin_instance):
                                    loaded_plugins.append(plugin_instance.plugin_id)
                                    
                except ImportError as e:
                    print(f"Failed to import plugin module from {item_path}: {str(e)}")
                except Exception as e:
                    print(f"Error loading plugin from {item_path}: {str(e)}")
                    
        return loaded_plugins
        
    def register_hook(self, hook_name: str, handler: callable):
        """
        注册钩子处理器
        :param hook_name: 钩子名称
        :param handler: 处理器函数
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = EventHook(hook_name)
        self.hooks[hook_name].register(handler)
        
    def unregister_hook(self, hook_name: str, handler: callable):
        """
        注销钩子处理器
        :param hook_name: 钩子名称
        :param handler: 处理器函数
        """
        if hook_name in self.hooks:
            self.hooks[hook_name].unregister(handler)
            
    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        触发钩子
        :param hook_name: 钩子名称
        :param args: 传递给处理器的位置参数
        :param kwargs: 传递给处理器的关键字参数
        :return: 所有处理器的返回值列表
        """
        if hook_name in self.hooks:
            return self.hooks[hook_name].execute(*args, **kwargs)
        return []
        
    def get_hook(self, hook_name: str) -> Optional[EventHook]:
        """获取钩子实例"""
        return self.hooks.get(hook_name)
        
    def shutdown_all_plugins(self):
        """关闭所有插件"""
        for plugin_id in list(self.plugins.keys()):
            self.unregister_plugin(plugin_id)