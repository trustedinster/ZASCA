"""
自定义错误处理视图
"""
from django.shortcuts import render


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
