"""
插件管理命令
提供类似 pip 的插件管理功能，支持安装、卸载、搜索、登录等操作
"""
import os
import sys
import subprocess
import json
import re
import toml
import inspect
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from plugins.core.plugin_manager import get_plugin_manager
from plugins.models import PluginRecord
import importlib
import importlib.util
from plugins.available_plugins import ALL_AVAILABLE_PLUGINS
import shutil
import urllib.request
import urllib.error

PLUGIN_REGISTRY_URL = "https://raw.githubusercontent.com/ZASCAteam/zasca-plugin-registry/main/plugins.json"
PLUGIN_REGISTRY_RAW_API = "https://api.github.com/repos/ZASCAteam/zasca-plugin-registry/contents/plugins.json"


class Command(BaseCommand):
    help = '插件管理命令，类似 pip 的功能'

    def add_arguments(self, parser):
        parser.add_argument('action', type=str, help='操作类型: install, uninstall, list, info, search, login')
        parser.add_argument('plugin_name', nargs='?', type=str, help='插件名称或本地路径')
        parser.add_argument('--source', type=str, help='插件源地址或本地路径')
        parser.add_argument('--force', action='store_true', help='强制执行操作')
        parser.add_argument('--registry', type=str, default=PLUGIN_REGISTRY_URL, help='插件仓库地址')

    def handle(self, *args, **options):
        action = options['action']
        plugin_name = options.get('plugin_name')

        if action == 'list':
            self.list_plugins()
        elif action == 'install':
            if not plugin_name:
                raise CommandError('安装插件需要指定插件名称或路径')
            self.install_plugin(plugin_name, options.get('source'), options.get('force'), options.get('registry'))
        elif action == 'uninstall':
            if not plugin_name:
                raise CommandError('卸载插件需要指定插件名称')
            self.uninstall_plugin(plugin_name, options.get('force'))
        elif action == 'info':
            if not plugin_name:
                raise CommandError('查看插件信息需要指定插件名称')
            self.plugin_info(plugin_name)
        elif action == 'search':
            keyword = plugin_name or ''
            self.search_plugins(keyword, options.get('registry'))
        elif action == 'login':
            self.login_github()
        else:
            raise CommandError(f'未知的操作: {action}. 支持的操作: install, uninstall, list, info, search, login')

    def _fetch_registry(self, registry_url=None):
        url = registry_url or PLUGIN_REGISTRY_URL
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'ZASCA-PluginManager/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return data.get('plugins', {})
        except Exception:
            pass

        try:
            result = subprocess.run(
                ['gh', 'api', '-H', 'Accept: application/vnd.github.v3.raw',
                 'repos/ZASCAteam/zasca-plugin-registry/contents/plugins.json'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return data.get('plugins', {})
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            pass
        except json.JSONDecodeError:
            pass
        except Exception:
            pass

        raise CommandError(
            '无法访问插件仓库。\n'
            '请检查网络连接或使用 "uv run manage.py plugin login" 登录 GitHub CLI 后重试。'
        )

    def search_plugins(self, keyword='', registry_url=None):
        remote_plugins = self._fetch_registry(registry_url)
        if not remote_plugins:
            self.stdout.write('远程插件仓库中没有插件')
            return

        results = {}
        for plugin_id, info in remote_plugins.items():
            if not keyword:
                results[plugin_id] = info
            else:
                kw = keyword.lower()
                if (kw in plugin_id.lower() or
                    kw in info.get('name', '').lower() or
                    kw in info.get('description', '').lower()):
                    results[plugin_id] = info

        if not results:
            self.stdout.write(f'未找到与 "{keyword}" 匹配的插件')
            return

        self.stdout.write(self.style.SUCCESS(f'找到 {len(results)} 个插件:'))
        self.stdout.write('')
        for plugin_id, info in results.items():
            self.stdout.write(f'  {self.style.SUCCESS(plugin_id)}')
            self.stdout.write(f'    名称: {info.get("name", "N/A")}')
            self.stdout.write(f'    简介: {info.get("description", "N/A")}')
            self.stdout.write(f'    仓库: {info.get("repository", "N/A")}')
            self.stdout.write(f'    版本: {info.get("version", "N/A")}')
            self.stdout.write('')

    def login_github(self):
        self.stdout.write('正在检查 GitHub CLI 认证状态...')
        try:
            result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS('GitHub CLI 已认证'))
                self.stdout.write(result.stdout.strip())
                return
        except FileNotFoundError:
            raise CommandError(
                '未找到 gh CLI，请先安装 GitHub CLI: https://cli.github.com/'
            )
        except subprocess.TimeoutExpired:
            raise CommandError('检查认证状态超时')

        self.stdout.write('GitHub CLI 未认证，正在启动登录流程...')
        try:
            result = subprocess.run(
                ['gh', 'auth', 'login'],
                stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr
            )
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS('GitHub 登录成功!'))
            else:
                raise CommandError('GitHub 登录失败')
        except FileNotFoundError:
            raise CommandError(
                '未找到 gh CLI，请先安装 GitHub CLI: https://cli.github.com/'
            )

    def install_plugin(self, plugin_name, source=None, force=False, registry_url=None):
        self.stdout.write(f'正在安装插件: {plugin_name}')

        if os.path.exists(plugin_name) and os.path.isdir(plugin_name):
            self.install_from_path(plugin_name)
            return

        plugin_path = os.path.join(settings.BASE_DIR, 'plugins', plugin_name)
        if os.path.exists(plugin_path) and os.path.isdir(plugin_path):
            self.install_from_path(plugin_path)
            return

        if plugin_name in ALL_AVAILABLE_PLUGINS:
            plugin_info = ALL_AVAILABLE_PLUGINS[plugin_name]
            self.install_builtin_plugin(plugin_name, plugin_info)
            return

        for plugin_id, plugin_info in ALL_AVAILABLE_PLUGINS.items():
            if plugin_info['name'].lower() == plugin_name.lower():
                self.install_builtin_plugin(plugin_id, plugin_info)
                return

        if source and os.path.exists(source) and os.path.isdir(source):
            self.install_from_path(source)
            return

        self.install_from_registry(plugin_name, registry_url, force)

    def install_from_registry(self, plugin_name, registry_url=None, force=False):
        remote_plugins = self._fetch_registry(registry_url)

        plugin_info = None
        for pid, info in remote_plugins.items():
            if pid == plugin_name or info.get('name', '').lower() == plugin_name.lower():
                plugin_info = info
                plugin_name = pid
                break

        if not plugin_info:
            available = list(remote_plugins.keys())
            raise CommandError(
                f'在远程仓库中找不到插件: {plugin_name}\n'
                f'可用的远程插件: {available}'
            )

        repository_url = plugin_info.get('repository')
        if not repository_url:
            raise CommandError(f'插件 {plugin_name} 没有提供仓库地址')

        target_dir = os.path.join(settings.BASE_DIR, 'plugins', plugin_name)
        if os.path.exists(target_dir):
            if force:
                shutil.rmtree(target_dir)
            else:
                raise CommandError(
                    f'插件目录已存在: {target_dir}\n'
                    f'使用 --force 强制重新安装'
                )

        self.stdout.write(f'正在从 {repository_url} 克隆插件...')

        clone_url = repository_url
        if repository_url.startswith('https://github.com/'):
            clone_url = repository_url.replace('https://github.com/', 'git@github.com:')

        try:
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', clone_url, target_dir],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                self.stdout.write('SSH 克隆失败，尝试 HTTPS...')
                result = subprocess.run(
                    ['git', 'clone', '--depth', '1', repository_url, target_dir],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode != 0:
                    raise CommandError(f'克隆插件仓库失败: {result.stderr.strip()}')
        except subprocess.TimeoutExpired:
            raise CommandError('克隆插件仓库超时')
        except FileNotFoundError:
            raise CommandError('未找到 git，请先安装 git')

        self.stdout.write(self.style.SUCCESS(f'插件仓库已克隆到: {target_dir}'))

        git_dir = os.path.join(target_dir, '.git')
        if os.path.exists(git_dir):
            shutil.rmtree(git_dir)
            self.stdout.write('已移除 .git 目录')

        plugin_record, created = PluginRecord.objects.update_or_create(
            plugin_id=plugin_name,
            defaults={
                'name': plugin_info.get('name', plugin_name),
                'version': plugin_info.get('version', '0.0.0'),
                'description': plugin_info.get('description', ''),
                'is_active': True,
            }
        )
        if created:
            self.stdout.write('已创建插件数据库记录')
        else:
            self.stdout.write('已更新插件数据库记录')

        self._try_register_cloned_plugin(plugin_name, target_dir, plugin_info)

        self.stdout.write(self.style.SUCCESS(
            f'插件 {plugin_info.get("name", plugin_name)} 安装完成!'
        ))

    def _try_register_cloned_plugin(self, plugin_id, plugin_path, registry_info):
        plugin_class = None
        plugin_module_name = None

        plugin_class, plugin_module_name = self._load_plugin_class_from_package(
            plugin_id, plugin_path
        )

        if plugin_class:
            try:
                plugin_instance = plugin_class()
                plugin_manager = get_plugin_manager()
                plugin_manager.plugins[plugin_instance.plugin_id] = plugin_instance

                try:
                    plugin_instance.initialize()
                except Exception:
                    pass

                plugin_record, _ = PluginRecord.objects.update_or_create(
                    plugin_id=plugin_instance.plugin_id,
                    defaults={
                        'name': plugin_instance.name,
                        'version': plugin_instance.version,
                        'description': plugin_instance.description,
                        'is_active': True,
                    }
                )

                self.add_plugin_to_toml_config(plugin_instance.plugin_id, {
                    'name': plugin_instance.name,
                    'module': plugin_module_name,
                    'class': plugin_class.__name__,
                    'description': plugin_instance.description,
                    'version': plugin_instance.version,
                    'enabled': True
                })
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f'插件类注册失败（插件文件已下载）: {str(e)}'
                ))
        else:
            self.stdout.write(self.style.WARNING(
                '未找到 PluginInterface 子类，插件已下载但未自动注册到 TOML 配置'
            ))
            self.stdout.write('你可能需要手动在 plugins.toml 中添加插件配置')

    def _load_plugin_class_from_package(self, plugin_id, plugin_path):
        plugin_class = None
        plugin_module_name = None

        init_file = os.path.join(plugin_path, '__init__.py')
        if os.path.exists(init_file):
            try:
                mod_name = f'plugins.{plugin_id}'
                init_module = importlib.import_module(mod_name)
                if hasattr(init_module, 'PLUGIN_INFO'):
                    pinfo = getattr(init_module, 'PLUGIN_INFO')
                    if 'main_class' in pinfo and hasattr(init_module, pinfo['main_class']):
                        plugin_class = getattr(init_module, pinfo['main_class'])
                        plugin_module_name = mod_name
            except ImportError:
                pass

        if not plugin_class:
            plugin_class, plugin_module_name = self._scan_py_files_for_plugin(
                plugin_id, plugin_path
            )

        return plugin_class, plugin_module_name

    def _scan_py_files_for_plugin(self, plugin_id, plugin_path):
        py_files = [
            f for f in os.listdir(plugin_path)
            if f.endswith('.py') and f != '__init__.py'
        ]
        for pf in py_files:
            fp = os.path.join(plugin_path, pf)
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not re.search(
                    r'class\s+\w+\s*\([^)]*PluginInterface',
                    content, re.DOTALL
                ):
                    continue

                mod_name = f'plugins.{plugin_id}.{pf[:-3]}'
                try:
                    module = importlib.import_module(mod_name)
                except ImportError:
                    spec = importlib.util.spec_from_file_location(
                        f"external_plugin_{plugin_id}", fp
                    )
                    if spec is None or spec.loader is None:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[mod_name] = module
                    spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if not inspect.isclass(attr) or not hasattr(attr, '__mro__'):
                        continue
                    if attr.__name__ == 'PluginInterface':
                        continue
                    if any(
                        hasattr(base, '__name__') and base.__name__ == 'PluginInterface'
                        for base in attr.__mro__
                    ):
                        return attr, mod_name
            except Exception:
                continue

        return None, None

    def install_from_path(self, plugin_path):
        if not os.path.exists(plugin_path):
            raise CommandError(f'插件路径不存在: {plugin_path}')

        init_file_path = os.path.join(plugin_path, '__init__.py')
        plugin_info_from_init = None

        if os.path.exists(init_file_path):
            try:
                spec = importlib.util.spec_from_file_location(
                    f"plugin_init_{os.path.basename(plugin_path)}",
                    init_file_path
                )
                init_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(init_module)

                if hasattr(init_module, 'PLUGIN_INFO'):
                    plugin_info_from_init = getattr(init_module, 'PLUGIN_INFO')
            except Exception:
                pass

        plugin_class = None
        plugin_file = None
        if plugin_info_from_init and 'main_class' in plugin_info_from_init:
            main_class_name = plugin_info_from_init['main_class']
            if hasattr(init_module, main_class_name):
                plugin_class = getattr(init_module, main_class_name)
                plugin_file = '__init__.py'

        if not plugin_class:
            plugin_files = [f for f in os.listdir(plugin_path) if f.endswith('.py')]
            if not plugin_files:
                raise CommandError(f'插件路径中没有Python文件: {plugin_path}')

            plugin_file = None
            plugin_dir_name = os.path.basename(plugin_path)

            for pf in plugin_files:
                if pf == f"{plugin_dir_name}.py":
                    plugin_file = pf
                    break

            if not plugin_file:
                for pf in plugin_files:
                    if pf == '__init__.py':
                        continue
                    file_path = os.path.join(plugin_path, pf)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'PluginInterface' in content and 'class' in content and (
                                '(PluginInterface)' in content or
                                '(PluginInterface,' in content or
                                '(BasePlugin)' in content or
                                'PluginInterface):' in content
                            ):
                                plugin_file = pf
                                break
                    except UnicodeDecodeError:
                        continue

            if not plugin_file:
                plugin_file = plugin_files[0]

            plugin_module_path = os.path.join(plugin_path, plugin_file)

            try:
                spec = importlib.util.spec_from_file_location(
                    f"external_plugin_{plugin_dir_name}",
                    plugin_module_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (hasattr(attr, '__bases__') and
                        inspect.isclass(attr) and
                        any(hasattr(base, '__name__') and base.__name__ == 'PluginInterface' for base in attr.__bases__)):
                        plugin_class = attr
                        break

            except Exception as e:
                raise CommandError(f'从文件 {plugin_file} 加载插件模块失败: {str(e)}')

        if not plugin_class:
            raise CommandError(f'在 {plugin_path} 中未找到有效的插件类')

        try:
            plugin_instance = plugin_class()
            plugin_manager = get_plugin_manager()

            plugin_manager.plugins[plugin_instance.plugin_id] = plugin_instance

            if plugin_instance.initialize():
                self.stdout.write(self.style.SUCCESS(f'成功从路径安装插件: {plugin_instance.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'插件 {plugin_instance.name} 安装成功但初始化失败'))

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

            plugin_dir_name = os.path.basename(plugin_path)
            if plugin_file == '__init__.py':
                module_name = f'plugins.{plugin_dir_name}'
            else:
                plugin_files = [f for f in os.listdir(plugin_path) if f.endswith('.py')]
                actual_plugin_file = None

                for pf in plugin_files:
                    if pf == '__init__.py':
                        continue
                    file_path = os.path.join(plugin_path, pf)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if plugin_class.__name__ in content and 'class' in content and plugin_class.__name__ + '(' in content:
                                actual_plugin_file = pf
                                break
                    except UnicodeDecodeError:
                        continue

                if actual_plugin_file:
                    module_name = f'plugins.{plugin_dir_name}.{actual_plugin_file[:-3]}'
                else:
                    module_name = f'plugins.{plugin_dir_name}.{plugin_file[:-3]}'

            self.add_plugin_to_toml_config(plugin_instance.plugin_id, {
                'name': plugin_instance.name,
                'module': module_name,
                'class': plugin_class.__name__,
                'description': plugin_instance.description,
                'version': plugin_instance.version,
                'enabled': True
            })
        except Exception as e:
            raise CommandError(f'从路径安装插件失败: {str(e)}')

    def install_builtin_plugin(self, plugin_id, plugin_info):
        plugin_manager = get_plugin_manager()

        if plugin_id in plugin_manager.get_all_plugins():
            self.stdout.write(
                self.style.WARNING(f'插件 {plugin_info["name"]} 已经加载.')
            )
            return

        plugin = plugin_manager.load_builtin_plugin(plugin_id, plugin_info)
        if not plugin:
            raise CommandError(f'加载插件 {plugin_info["name"]} 失败')

        try:
            if plugin.initialize():
                self.stdout.write(self.style.SUCCESS(f'成功安装并初始化插件: {plugin.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'插件 {plugin.name} 安装成功但初始化失败'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'插件 {plugin.name} 安装成功但初始化出错: {str(e)}'))

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

        if plugin_id not in ALL_AVAILABLE_PLUGINS:
            self.add_plugin_to_toml_config(plugin_id, plugin_info)

    def uninstall_plugin(self, plugin_name, force=False):
        self.stdout.write(f'正在卸载插件: {plugin_name}')

        plugin_manager = get_plugin_manager()

        plugin = None
        loaded_plugins = plugin_manager.get_all_plugins()
        for pid, p in loaded_plugins.items():
            if p.plugin_id == plugin_name or p.name.lower() == plugin_name.lower():
                plugin = p
                break

        if not plugin:
            db_record = PluginRecord.objects.filter(plugin_id=plugin_name).first()
            if db_record:
                if force or input(f'插件 {plugin_name} 未加载但数据库中有记录。是否删除数据库记录？(y/N): ').lower() == 'y':
                    PluginRecord.objects.filter(plugin_id=plugin_name).delete()
                    self.remove_plugin_from_toml_config(plugin_name)
                    plugin_dir = os.path.join(settings.BASE_DIR, 'plugins', plugin_name)
                    if os.path.exists(plugin_dir):
                        shutil.rmtree(plugin_dir)
                        self.stdout.write(f'已删除插件目录: {plugin_dir}')
                    self.stdout.write(self.style.SUCCESS(f'已从数据库中删除插件记录: {plugin_name}'))
                    return
                else:
                    self.stdout.write(f'操作已取消')
                    return
            else:
                raise CommandError(f'找不到已加载的插件: {plugin_name}')

        try:
            if hasattr(plugin, 'shutdown'):
                plugin.shutdown()

            success = plugin_manager.unload_plugin(plugin.plugin_id)

            if success:
                PluginRecord.objects.filter(plugin_id=plugin.plugin_id).update(is_active=False)
                self.remove_plugin_from_toml_config(plugin.plugin_id)
                plugin_dir = os.path.join(settings.BASE_DIR, 'plugins', plugin.plugin_id)
                if os.path.exists(plugin_dir):
                    shutil.rmtree(plugin_dir)
                    self.stdout.write(f'已删除插件目录: {plugin_dir}')
                self.stdout.write(self.style.SUCCESS(f'成功卸载插件: {plugin.name}'))
            else:
                raise CommandError(f'卸载插件 {plugin.name} 失败')
        except Exception as e:
            if force:
                PluginRecord.objects.filter(plugin_id=plugin.plugin_id).delete()
                self.remove_plugin_from_toml_config(plugin.plugin_id)
                plugin_dir = os.path.join(settings.BASE_DIR, 'plugins', plugin.plugin_id)
                if os.path.exists(plugin_dir):
                    shutil.rmtree(plugin_dir)
                self.stdout.write(self.style.WARNING(f'强制卸载插件: {plugin.name}'))
            else:
                raise CommandError(f'卸载插件失败: {str(e)}')

    def list_plugins(self):
        self.stdout.write(self.style.SUCCESS('已安装的插件:'))

        plugin_manager = get_plugin_manager()
        loaded_plugins = plugin_manager.get_all_plugins()

        if not loaded_plugins:
            self.stdout.write('  没有加载任何插件')
        else:
            for plugin_id, plugin in loaded_plugins.items():
                status = '✓' if hasattr(plugin, 'enabled') and plugin.enabled else '✓'
                self.stdout.write(f'  [{status}] {plugin.name} (v{plugin.version}) - {plugin.description}')

        db_records = PluginRecord.objects.all()
        if db_records.exists():
            self.stdout.write('\n数据库中的插件记录:')
            for record in db_records:
                status = '✓' if record.is_active else '✗'
                is_available = record.plugin_id in ALL_AVAILABLE_PLUGINS
                availability_indicator = '●' if is_available else '○'
                self.stdout.write(f'  [{status}{availability_indicator}] {record.name} (v{record.version}) - {record.plugin_id}')

        self.stdout.write('\n可用插件:')
        installed_plugin_ids = {p.plugin_id for p in loaded_plugins.values()}
        for plugin_id, plugin_info in ALL_AVAILABLE_PLUGINS.items():
            status = '✓' if plugin_id in installed_plugin_ids else '○'
            self.stdout.write(f'  [{status}] {plugin_info["name"]} - {plugin_info["description"]}')

        self.stdout.write('\n远程仓库插件 (使用 plugins search 查看更多):')
        try:
            remote_plugins = self._fetch_registry()
            for plugin_id, info in remote_plugins.items():
                installed = '✓' if plugin_id in installed_plugin_ids else '○'
                self.stdout.write(f'  [{installed}] {info.get("name", plugin_id)} - {info.get("description", "N/A")}')
        except Exception:
            self.stdout.write(self.style.WARNING('  无法连接远程仓库'))

    def plugin_info(self, plugin_name):
        plugin_manager = get_plugin_manager()

        loaded_plugins = plugin_manager.get_all_plugins()
        plugin = None
        for pid, p in loaded_plugins.items():
            if p.plugin_id == plugin_name or p.name.lower() == plugin_name.lower():
                plugin = p
                break

        if not plugin:
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
            try:
                remote_plugins = self._fetch_registry()
                for plugin_id, info in remote_plugins.items():
                    if plugin_id == plugin_name or info.get('name', '').lower() == plugin_name.lower():
                        self.stdout.write(f'远程插件信息: {info.get("name", plugin_id)}')
                        self.stdout.write(f'  ID: {plugin_id}')
                        self.stdout.write(f'  版本: {info.get("version", "N/A")}')
                        self.stdout.write(f'  描述: {info.get("description", "N/A")}')
                        self.stdout.write(f'  仓库: {info.get("repository", "N/A")}')
                        return
            except Exception:
                pass

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

    def add_plugin_to_toml_config(self, plugin_id, plugin_info):
        config_file_path = os.path.join(settings.BASE_DIR, 'plugins', 'plugins.toml')

        if os.path.exists(config_file_path):
            with open(config_file_path, 'r', encoding='utf-8') as f:
                toml_data = toml.load(f)
        else:
            toml_data = {
                'builtin': {},
                'third_party': {}
            }

        if plugin_id in toml_data.get('builtin', {}) or plugin_id in toml_data.get('third_party', {}):
            self.stdout.write(f'插件 {plugin_id} 已存在于配置中')
            return

        toml_data.setdefault('third_party', {})[plugin_id] = {
            'name': plugin_info['name'],
            'module': plugin_info['module'],
            'class': plugin_info['class'],
            'description': plugin_info['description'],
            'version': plugin_info['version'],
            'enabled': plugin_info['enabled']
        }

        with open(config_file_path, 'w', encoding='utf-8') as f:
            toml.dump(toml_data, f)

        self.stdout.write(f'已将插件 {plugin_id} 添加到 TOML 配置文件')

    def remove_plugin_from_toml_config(self, plugin_id):
        config_file_path = os.path.join(settings.BASE_DIR, 'plugins', 'plugins.toml')

        if not os.path.exists(config_file_path):
            self.stdout.write(f'TOML 配置文件不存在: {config_file_path}')
            return

        with open(config_file_path, 'r', encoding='utf-8') as f:
            toml_data = toml.load(f)

        plugin_removed = False
        if 'builtin' in toml_data and plugin_id in toml_data['builtin']:
            del toml_data['builtin'][plugin_id]
            plugin_removed = True
            self.stdout.write(f'已从 builtin 部分移除插件 {plugin_id}')

        if 'third_party' in toml_data and plugin_id in toml_data['third_party']:
            del toml_data['third_party'][plugin_id]
            plugin_removed = True
            self.stdout.write(f'已从 third_party 部分移除插件 {plugin_id}')

        if plugin_removed:
            with open(config_file_path, 'w', encoding='utf-8') as f:
                toml.dump(toml_data, f)

            self.stdout.write(f'已从 TOML 配置文件中移除插件 {plugin_id}')
        else:
            self.stdout.write(f'插件 {plugin_id} 在 TOML 配置文件中未找到')
