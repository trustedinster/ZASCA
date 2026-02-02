"""
DEMO模式中间件
用于处理演示模式下的特殊逻辑
"""
import os
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import User
from apps.operations.models import AccountOpeningRequest, CloudComputerUser, Product
from apps.hosts.models import Host


class DemoModeMiddleware:
    """
    DEMO模式中间件，处理演示环境的特殊逻辑
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.demo_mode = os.environ.get('ZASCA_DEMO', '').lower() == '1'
        if self.demo_mode:
            self.setup_demo_users()

    def __call__(self, request):
        if not self.demo_mode:
            return self.get_response(request)

        # 在DEMO模式下设置特殊标志
        request.is_demo_mode = True

        response = self.get_response(request)

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not self.demo_mode:
            return None

        # 为DEMO模式处理特定的视图逻辑
        # 检查是否是发送邮件的视图
        if hasattr(view_func, '__name__') and 'send_' in view_func.__name__ and 'email' in view_func.__name__:
            # 模拟发送邮件成功，但实际上不发送
            if request.method == 'POST':
                # 这里我们模拟一个成功响应
                return JsonResponse({'status': 'ok'})
        
        # 检查是否是密码修改相关的视图
        if (hasattr(view_func, '__name__') and 
            ('password' in view_func.__name__.lower() or 'change' in view_func.__name__.lower()) and
            any(pwd_keyword in request.path.lower() for pwd_keyword in ['password', 'pwd']) and
            'get-password' not in request.path.lower()):  # 排除获取密码的阅后即焚功能
            # 在DEMO模式下，不允许修改密码
            if request.method == 'POST':
                from django.contrib import messages
                messages.error(request, 'DEMO模式下不允许修改密码')
                # 重定向到profile页面或返回错误
                from django.shortcuts import redirect
                referer = request.META.get('HTTP_REFERER', '/')
                return redirect(referer)
        
        # 检查Django Admin密码更改URL
        if ('/admin/password_change/' in request.path or 
            ('/admin/auth/user/' in request.path and 'password' in request.path)):
            if request.method == 'POST':
                from django.contrib import messages
                messages.error(request, 'DEMO模式下不允许修改密码')
                from django.shortcuts import redirect
                referer = request.META.get('HTTP_REFERER', '/admin/')
                return redirect(referer)
        
        # 检查所有可能的密码更改路径
        if ('password' in request.path.lower() and 
            ('change' in request.path.lower() or 'update' in request.path.lower()) and
            'get-password' not in request.path.lower()):  # 排除获取密码的阅后即焚功能
            if request.method == 'POST':
                from django.contrib import messages
                messages.error(request, 'DEMO模式下不允许修改密码')
                from django.shortcuts import redirect
                referer = request.META.get('HTTP_REFERER', '/')
                return redirect(referer)

        return None

    def setup_demo_users(self):
        """
        创建DEMO模式下的用户
        """
        User = get_user_model()

        # 创建User用户
        user, created = User.objects.get_or_create(
            username='User',
            defaults={
                'email': 'user@example.com',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_active': True,
            }
        )
        if created:
            user.set_password('demo_user_password')
            user.save()

        # 创建Admin用户
        admin, created = User.objects.get_or_create(
            username='Admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Demo',
                'last_name': 'Admin',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            admin.set_password('demo_admin_password')
            # 分配特定权限
            self.assign_demo_permissions(admin)
            admin.save()

    def assign_demo_permissions(self, user):
        """
        为DEMO模式下的Admin用户分配特定权限
        """
        permissions = [
            # View登录日志
            ('accounts', 'loginlog', 'view'),
            # View日志记录 (UserActivity)
            ('dashboard', 'useractivity', 'view'),
            # View开户申请
            ('operations', 'accountopeningrequest', 'view'),
            # Change开户申请
            ('operations', 'accountopeningrequest', 'change'),
            # View云电脑用户
            ('operations', 'cloudcomputeruser', 'view'),
            # Change云电脑用户
            ('operations', 'cloudcomputeruser', 'change'),
            # View产品
            ('operations', 'product', 'view'),
        ]

        for app_label, model, perm_action in permissions:
            try:
                content_type = ContentType.objects.get(app_label=app_label, model=model)
                permission_codename = f'{perm_action}_{model}'
                permission = Permission.objects.get(content_type=content_type, codename=permission_codename)
                user.user_permissions.add(permission)
            except ContentType.DoesNotExist:
                print(f"ContentType not found: {app_label}.{model}")
            except Permission.DoesNotExist:
                print(f"Permission not found: {app_label}.{model}.{perm_action}")


def is_demo_mode():
    """
    检查是否处于DEMO模式
    """
    return os.environ.get('ZASCA_DEMO', '').lower() == '1'