"""
插件管理命令
提供类似 pip 的插件管理功能，支持安装、卸载、列出插件等操作
"""
import os
import sys
import subprocess
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from plugins.core.plugin_manager import get_plugin_manager
from plugins.models import PluginRecord
import importlib.util
from plugins.available_plugins import ALL_AVAILABLE_PLUGINS
import shutil


class Command(BaseCommand):
    help = '插件管理命令，类似 pip 的功能'

    def add_arguments(self, parser):
        parser.add_argument('action', type=str, help='操作类型: install, uninstall, list, info')
        parser.add_argument('plugin_name', nargs='?', type=str, help='插件名称或本地路径')
        parser.add_argument('--source', type=str, help='插件源地址或本地路径')
        parser.add_argument('--force', action='store_true', help='强制执行操作')

    def handle(self, *args, **options):
        action = options['action']
        plugin_name = options.get('plugin_name')

        if action == 'list':
            self.list_plugins()
        elif action == 'install':
            if not plugin_name:
                raise CommandError('安装插件需要指定插件名称或路径')
            self.install_plugin(plugin_name, options.get('source'), options.get('force'))
        elif action == 'uninstall':
            if not plugin_name:
                raise CommandError('卸载插件需要指定插件名称')
            self.uninstall_plugin(plugin_name, options.get('force'))
        elif action == 'info':
            if not plugin_name:
                raise CommandError('查看插件信息需要指定插件名称')
            self.plugin_info(plugin_name)
        else:
            raise CommandError(f'未知的操作: {action}. 支持的操作: install, uninstall, list, info')

    def list_plugins(self):
        """列出所有已安装的插件"""
        self.stdout.write(self.style.SUCCESS('已安装的插件:'))
        
        plugin_manager = get_plugin_manager()
        loaded_plugins = plugin_manager.get_all_plugins()
        
        if not loaded_plugins:
            self.stdout.write('  没有加载任何插件')
        else:
            for plugin_id, plugin in loaded_plugins.items():
                status = '✓' if hasattr(plugin, 'enabled') and plugin.enabled else '✓'  # 默认认为是启用的
                self.stdout.write(f'  [{status}] {plugin.name} (v{plugin.version}) - {plugin.description}')
        
        # 也列出数据库中的记录
        db_records = PluginRecord.objects.all()
        if db_records.exists():
            self.stdout.write('\n数据库中的插件记录:')
            for record in db_records:
                status = '✓' if record.is_active else '✗'
                # 检查是否是可用插件
                is_available = record.plugin_id in ALL_AVAILABLE_PLUGINS
                availability_indicator = '●' if is_available else '○'  # ●表示可用，○表示私有/不可用
                self.stdout.write(f'  [{status}{availability_indicator}] {record.name} (v{record.version}) - {record.plugin_id}')
        
        # 显示可用但未安装的插件
        self.stdout.write('\n可用插件:')
        installed_plugin_ids = {p.plugin_id for p in loaded_plugins.values()}
        for plugin_id, plugin_info in ALL_AVAILABLE_PLUGINS.items():
            status = '✓' if plugin_id in installed_plugin_ids else '○'
            self.stdout.write(f'  [{status}] {plugin_info["name"]} - {plugin_info["description"]}')

    def plugin_info(self, plugin_name):
        """显示插件详细信息"""
        plugin_manager = get_plugin_manager()
        
        # 首先尝试获取已加载的插件
        loaded_plugins = plugin_manager.get_all_plugins()
        plugin = None
        for pid, p in loaded_plugins.items():
            if p.plugin_id == plugin_name or p.name.lower() == plugin_name.lower():
                plugin = p
                break
        
        if not plugin:
            # 尝试从可用插件列表中查找
            for plugin_id, plugin_info in ALL_AVAILABLE_PLUGINS.items():
                if plugin_id == plugin_name or plugin_info['name'].lower() == plugin_name.lower():
                    self.stdout.write(f'插件信息: {plugin_info["name"]}')
                    self.stdout.write(f'  ID: {plugin_id}')
                    self.stdout.write(f'  版本: {plugin_info["version"]}')
                    self.stdout.write(f'  描述: {plugin_info["description"]}')
                    self.stdout.write(f'  模块: {plugin_info["module"]}')
                    self.stdout.write(f'  类: {plugin_info["class"]}')
                    self.stdout.write(f'  状态: {"已启用" if plugin_info["enabled"] else "已禁用"}')
                    return
        
        if plugin:
            self.stdout.write(f'插件信息: {plugin.name}')
            self.stdout.write(f'  ID: {plugin.plugin_id}')
            self.stdout.write(f'  版本: {plugin.version}')
            self.stdout.write(f'  描述: {plugin.description}')
            if hasattr(plugin, 'enabled'):
                self.stdout.write(f'  状态: {"已启用" if plugin.enabled else "已禁用"}')
            else:
                self.stdout.write(f'  状态: 已加载')
        else:
            # 检查是否在数据库中有记录（可能是私有插件）
            db_record = PluginRecord.objects.filter(plugin_id=plugin_name).first()
            if db_record:
                self.stdout.write(f'插件信息: {db_record.name}')
                self.stdout.write(f'  ID: {db_record.plugin_id}')
                self.stdout.write(f'  版本: {db_record.version}')
                self.stdout.write(f'  描述: {db_record.description}')
                self.stdout.write(f'  状态: {"已激活" if db_record.is_active else "未激活"}')
                self.stdout.write(f'  注意: 此插件在数据库中有记录，但当前版本中不可用（可能是私有插件）')
            else:
                raise CommandError(f'找不到插件: {plugin_name}')

    def install_plugin(self, plugin_name, source=None, force=False):
        """安装插件"""
        self.stdout.write(f'正在安装插件: {plugin_name}')
        
        # 检查是否是本地路径
        if os.path.exists(plugin_name) and os.path.isdir(plugin_name):
            # 从本地路径安装
            self.install_from_path(plugin_name)
            return
        
        # 检查是否是可用的内置插件
        if plugin_name in ALL_AVAILABLE_PLUGINS:
            plugin_info = ALL_AVAILABLE_PLUGINS[plugin_name]
            self.install_builtin_plugin(plugin_name, plugin_info)
        else:
            # 尝试从可用插件中按名称查找
            found_plugin = False
            for plugin_id, plugin_info in ALL_AVAILABLE_PLUGINS.items():
                if plugin_info['name'].lower() == plugin_name.lower():
                    self.install_builtin_plugin(plugin_id, plugin_info)
                    found_plugin = True
                    break
            
            if not found_plugin:
                # 检查是否是来自外部的插件文件夹
                if source and os.path.exists(source) and os.path.isdir(source):
                    self.install_from_path(source)
                else:
                    raise CommandError(f'找不到插件: {plugin_name}. 可用的插件: {list(ALL_AVAILABLE_PLUGINS.keys())}')

    def install_from_path(self, plugin_path):
        """从本地路径安装插件"""
        if not os.path.exists(plugin_path):
            raise CommandError(f'插件路径不存在: {plugin_path}')
        
        # 尝试直接加载插件模块
        plugin_files = [f for f in os.listdir(plugin_path) if f.endswith('.py')]
        if not plugin_files:
            raise CommandError(f'插件路径中没有Python文件: {plugin_path}')
        
        # 假设主插件文件是目录名同名的文件或第一个Python文件
        plugin_file = None
        plugin_dir_name = os.path.basename(plugin_path)
        for pf in plugin_files:
            if pf == f"{plugin_dir_name}.py":
                plugin_file = pf
                break
        if not plugin_file:
            plugin_file = plugin_files[0]
        
        plugin_module_path = os.path.join(plugin_path, plugin_file)
        
        try:
            # 动态导入插件模块
            spec = importlib.util.spec_from_file_location(
                f"external_plugin_{plugin_dir_name}", 
                plugin_module_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找插件类（继承自PluginInterface的类）
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (hasattr(attr, '__bases__') and 
                    len(attr.__bases__) > 0 and 
                    any(base.__name__ == 'PluginInterface' for base in attr.__bases__ if hasattr(base, '__name__'))):
                    plugin_class = attr
                    break
            
            if plugin_class:
                plugin_instance = plugin_class()
                plugin_manager = get_plugin_manager()
                
                # 将插件添加到管理器中
                plugin_manager.plugins[plugin_instance.plugin_id] = plugin_instance
                
                if plugin_instance.initialize():
                    self.stdout.write(self.style.SUCCESS(f'成功从路径安装插件: {plugin_instance.name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'插件 {plugin_instance.name} 安装成功但初始化失败'))
                
                # 在数据库中创建记录
                plugin_record, created = PluginRecord.objects.update_or_create(
                    plugin_id=plugin_instance.plugin_id,
                    defaults={
                        'name': plugin_instance.name,
                        'version': plugin_instance.version,
                        'description': plugin_instance.description,
                        'is_active': True,
                    }
                )
                
                if created:
                    self.stdout.write(f'已创建插件数据库记录')
            else:
                raise CommandError(f'在 {plugin_path} 中未找到有效的插件类')
                
        except Exception as e:
            raise CommandError(f'从路径安装插件失败: {str(e)}')
    
    def install_builtin_plugin(self, plugin_id, plugin_info):
        """安装内置插件"""
        plugin_manager = get_plugin_manager()
        
        # 检查插件是否已加载
        if plugin_id in plugin_manager.get_all_plugins():
            self.stdout.write(
                self.style.WARNING(f'插件 {plugin_info["name"]} 已经加载.')
            )
            return
        
        # 加载插件
        plugin = plugin_manager.load_builtin_plugin(plugin_id, plugin_info)
        if not plugin:
            raise CommandError(f'加载插件 {plugin_info["name"]} 失败')
        
        # 尝试初始化插件
        try:
            if plugin.initialize():
                self.stdout.write(self.style.SUCCESS(f'成功安装并初始化插件: {plugin.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'插件 {plugin.name} 安装成功但初始化失败'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'插件 {plugin.name} 安装成功但初始化出错: {str(e)}'))
        
        # 在数据库中创建或更新记录
        plugin_record, created = PluginRecord.objects.update_or_create(
            plugin_id=plugin.plugin_id,
            defaults={
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(f'已创建插件数据库记录')

    def uninstall_plugin(self, plugin_name, force=False):
        """卸载插件"""
        self.stdout.write(f'正在卸载插件: {plugin_name}')
        
        plugin_manager = get_plugin_manager()
        
        # 查找插件
        plugin = None
        loaded_plugins = plugin_manager.get_all_plugins()
        for pid, p in loaded_plugins.items():
            if p.plugin_id == plugin_name or p.name.lower() == plugin_name.lower():
                plugin = p
                break
        
        if not plugin:
            # 检查是否在数据库中有记录（即使是私有插件）
            db_record = PluginRecord.objects.filter(plugin_id=plugin_name).first()
            if db_record:
                # 询问是否删除数据库记录
                if force or input(f'插件 {plugin_name} 未加载但数据库中有记录。是否删除数据库记录？(y/N): ').lower() == 'y':
                    PluginRecord.objects.filter(plugin_id=plugin_name).delete()
                    self.stdout.write(self.style.SUCCESS(f'已从数据库中删除插件记录: {plugin_name}'))
                    return
                else:
                    self.stdout.write(f'操作已取消')
                    return
            else:
                raise CommandError(f'找不到已加载的插件: {plugin_name}')
        
        try:
            # 尝试关闭插件
            if hasattr(plugin, 'shutdown'):
                plugin.shutdown()
            
            # 从插件管理器中卸载
            success = plugin_manager.unload_plugin(plugin.plugin_id)
            
            if success:
                # 更新数据库记录
                PluginRecord.objects.filter(plugin_id=plugin.plugin_id).update(is_active=False)
                self.stdout.write(self.style.SUCCESS(f'成功卸载插件: {plugin.name}'))
            else:
                raise CommandError(f'卸载插件 {plugin.name} 失败')
        except Exception as e:
            if force:
                # 强制从数据库删除记录
                PluginRecord.objects.filter(plugin_id=plugin.plugin_id).delete()
                self.stdout.write(self.style.WARNING(f'强制卸载插件: {plugin.name}'))
            else:
                raise CommandError(f'卸载插件失败: {str(e)}')