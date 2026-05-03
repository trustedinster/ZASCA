"""
提供商认证装饰器和辅助函数

集中管理提供商身份验证逻辑，供整个项目使用。
替代 hosts/admin.py、operations/admin.py、tickets/admin.py 中重复的 is_provider 函数。
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from functools import wraps


PROVIDER_GROUP_NAME = '主机提供商'


def is_provider(user):
    """
    检查用户是否属于提供商组

    超级管理员不属于提供商组，即使其权限更高。
    此逻辑与 Admin 后台的数据隔离保持一致。

    Args:
        user: 用户对象

    Returns:
        bool: 如果用户属于提供商组且不是超级管理员，返回 True
    """
    if user.is_superuser:
        return False
    return user.groups.filter(name=PROVIDER_GROUP_NAME).exists()


def provider_required(view_func):
    """
    装饰器：要求当前用户为提供商

    - 未登录用户将被重定向到登录页
    - 非提供商用户将被重定向到登录页
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_provider(request.user):
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_required(view_func):
    """
    装饰器：要求当前用户为超级管理员

    - 未登录用户将被重定向到登录页
    - 非超级管理员将被重定向到提供商仪表盘
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('provider:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
