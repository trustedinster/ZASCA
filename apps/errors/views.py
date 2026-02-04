"""
错误处理视图
"""
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden
from django.shortcuts import render
import logging

logger = logging.getLogger('zasca')


def handler400(request, exception=None):
    """400 错误处理"""
    logger.warning(f"400 Bad request from {request.META.get('REMOTE_ADDR')} to {request.path}")
    return render(request, 'errors/400.html', {
        'error_title': '错误的请求',
        'error_message': '您的请求格式不正确或包含无效数据。',
        'request_id': getattr(request, 'request_id', None)
    }, status=400)


def handler403(request, exception=None):
    """403 错误处理"""
    logger.warning(f"403 Forbidden access from {request.META.get('REMOTE_ADDR')} to {request.path}")
    return render(request, 'errors/403.html', {
        'error_title': '访问被拒绝',
        'error_message': '您没有权限访问此页面。',
        'request_id': getattr(request, 'request_id', None)
    }, status=403)


def handler404(request, exception=None):
    """404 错误处理"""
    logger.info(f"404 Not found: {request.path}")
    return render(request, 'errors/404.html', {
        'error_title': '页面未找到',
        'error_message': '您请求的页面不存在或已被移动。',
        'request_path': request.path,
        'request_id': getattr(request, 'request_id', None)
    }, status=404)


def handler500(request):
    """500 错误处理"""
    logger.error(f"500 Server error at {request.path}", exc_info=True)
    # 获取追踪 ID
    import uuid
    trace_id = str(uuid.uuid4())

    # 使用通用错误消息，不暴露技术细节
    return render(request, 'errors/500.html', {
        'error_title': '服务器错误',
        'error_message': '服务器遇到了意外情况，我们正在努力修复此问题。',
        'request_id': getattr(request, 'request_id', None),
        'trace_id': trace_id,
        'support_message': '如果问题持续存在，请联系技术支持团队'
    }, status=500)