"""
自定义错误处理视图
"""
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import QueryDict


def custom_404(request, exception):
    """
    自定义404错误页面

    Args:
        request: HTTP请求对象
        exception: 异常对象

    Returns:
        HttpResponse: 404错误页面
    """
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    """
    自定义500错误页面

    Args:
        request: HTTP请求对象

    Returns:
        HttpResponse: 500错误页面
    """
    return render(request, 'errors/500.html', status=500)


def extend_admin_login(request):
    """
    重定向Django Admin登录页面到accounts登录页面，并保留查询参数
    """
    # 构建带查询参数的目标URL
    next_url = request.GET.get('next', '')  # 获取next参数
    target_url = reverse('accounts:login')
    
    # 如果有next参数，则添加到目标URL
    if next_url:
        target_url += f'?next={next_url}'
    
    return redirect(target_url)