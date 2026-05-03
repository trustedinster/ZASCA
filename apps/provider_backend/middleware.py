from django.shortcuts import redirect
from django.urls import reverse


class ProviderRedirectMiddleware:
    """
    提供商重定向中间件

    将提供商用户从 /admin/ 重定向到 /provider/，
    防止提供商访问 Django Admin 后台。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/') and not request.path.startswith('/admin/login/'):
            if hasattr(request, 'user') and request.user.is_authenticated:
                from .decorators import is_provider
                if is_provider(request.user) and not request.user.is_superuser:
                    return redirect('provider:dashboard')
        return self.get_response(request)
