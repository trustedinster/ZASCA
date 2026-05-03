from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps


PROVIDER_GROUP_NAME = '主机提供商'


def is_provider(user):
    """检查用户是否属于提供商组"""
    if user.is_superuser:
        return False
    return user.groups.filter(name=PROVIDER_GROUP_NAME).exists()


def provider_required(view_func):
    """
    装饰器：要求当前用户为提供商
    非提供商用户将被重定向到登录页
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_provider(request.user):
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def superadmin_required(view_func):
    """
    装饰器：要求当前用户为超级管理员
    非超级管理员将被重定向到提供商仪表盘
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('provider:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
