"""
Django项目插件系统集成
展示如何将插件系统集成到Django项目中
"""

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from . import plugin_manager


def initialize_plugins():
    """
    初始化项目插件
    应该在Django应用启动时调用
    """
    # 添加项目插件目录
    plugin_dirs = [
        "./plugins/custom_plugins",  # 自定义插件目录
        "./plugins/third_party",     # 第三方插件目录
    ]
    
    # 从设置中读取额外的插件目录
    if hasattr(settings, 'PLUGIN_DIRS'):
        plugin_dirs.extend(settings.PLUGIN_DIRS)
    
    for directory in plugin_dirs:
        plugin_manager.add_plugin_directory(directory)
    
    # 加载所有插件
    loaded_plugins = plugin_manager.load_all_plugins()
    print(f"Django项目已加载插件: {loaded_plugins}")
    
    return loaded_plugins


def get_plugin(plugin_id):
    """
    获取插件实例
    :param plugin_id: 插件ID
    :return: 插件实例或None
    """
    return plugin_manager.get_plugin(plugin_id)


def trigger_hook(hook_name, *args, **kwargs):
    """
    触发钩子
    :param hook_name: 钩子名称
    :param args: 参数
    :param kwargs: 关键字参数
    :return: 钩子执行结果
    """
    return plugin_manager.trigger_hook(hook_name, *args, **kwargs)


def register_hook(hook_name, handler):
    """
    注册钩子处理器
    :param hook_name: 钩子名称
    :param handler: 处理器函数
    """
    plugin_manager.register_hook(hook_name, handler)


def plugin_api_view(request, plugin_id, action):
    """
    插件API视图
    提供对插件功能的HTTP访问
    """
    plugin = get_plugin(plugin_id)
    
    if not plugin:
        return JsonResponse({
            'error': f'Plugin {plugin_id} not found',
            'success': False
        }, status=404)
    
    if not plugin.enabled:
        return JsonResponse({
            'error': f'Plugin {plugin_id} is disabled',
            'success': False
        }, status=400)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}
    else:
        data = request.GET.dict()
    
    # 根据动作调用插件方法
    if hasattr(plugin, action):
        try:
            method = getattr(plugin, action)
            if callable(method):
                result = method(**data)
                return JsonResponse({
                    'result': result,
                    'success': True
                })
            else:
                return JsonResponse({
                    'error': f'{action} is not callable',
                    'success': False
                }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'success': False
            }, status=500)
    else:
        return JsonResponse({
            'error': f'Action {action} not found in plugin {plugin_id}',
            'success': False
        }, status=400)


@csrf_exempt
def plugin_management_api(request):
    """
    插件管理API
    用于管理插件的启用/禁用、加载/卸载等
    """
    if request.method == 'GET':
        # 返回所有插件信息
        plugins = []
        for plugin in plugin_manager.get_all_plugins():
            plugins.append(plugin.metadata)
        return JsonResponse({'plugins': plugins})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            plugin_id = data.get('plugin_id')
            
            if action == 'enable':
                success = plugin_manager.enable_plugin(plugin_id)
                return JsonResponse({'success': success})
            elif action == 'disable':
                success = plugin_manager.disable_plugin(plugin_id)
                return JsonResponse({'success': success})
            elif action == 'reload':
                # 重新加载插件（在实际实现中可能需要更复杂的逻辑）
                plugin_manager.unregister_plugin(plugin_id)
                # 重新从目录加载
                for directory in plugin_manager.plugin_dirs:
                    plugin_manager.load_plugins_from_directory(directory)
                return JsonResponse({'success': True})
            else:
                return JsonResponse({
                    'error': f'Unknown action: {action}',
                    'success': False
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'success': False
            }, status=500)


# Django中间件示例
class PluginMiddleware:
    """
    插件中间件
    在请求处理过程中执行插件钩子
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 在请求处理前触发钩子
        trigger_hook('before_request', request=request)
        
        response = self.get_response(request)
        
        # 在请求处理后触发钩子
        trigger_hook('after_request', request=request, response=response)
        
        return response
        
    def process_view(self, request, view_func, view_args, view_kwargs):
        """在视图函数调用前触发钩子"""
        result = trigger_hook('before_view', 
                             request=request, 
                             view_func=view_func,
                             view_args=view_args,
                             view_kwargs=view_kwargs)
        # 如果任何插件返回了HttpResponse，则使用它
        for res in result:
            if res and hasattr(res, 'status_code'):
                return res
        return None