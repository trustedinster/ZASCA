"""
维护模式中间件
当REPAIRING环境变量为1时，将所有请求重定向到维护页面
"""
import os
from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponseRedirect


class MaintenanceModeMiddleware:
    """
    维护模式中间件
    当REPAIRING环境变量设置为1时，将所有请求重定向到维护页面
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 检查是否处于维护模式
        repairing = os.environ.get('REPAIRING', '0')
        
        # 排除维护页面本身和静态资源，避免无限重定向
        excluded_paths = [
            '/maintenance/',
            '/static/',
            '/media/',
        ]
        
        # 如果处于维护模式且不在排除路径中，则重定向到维护页面
        if (repairing.lower() == '1' or repairing == 'true' or repairing == 'on' or repairing == 'yes' or repairing == 'enabled') and \
           not any(request.path.startswith(path) for path in excluded_paths):
            
            # 检查请求是否是AJAX请求，如果是则返回JSON错误而不是重定向
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({
                    'error': '系统正在维护中，请稍后再试',
                    'maintenance': True
                }, status=503)
            
            # 对于非AJAX请求，渲染维护页面
            return render(request, 'maintenance.html')
        
        response = self.get_response(request)
        return response