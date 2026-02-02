from django.http import JsonResponse
from .models import ActiveSession
from django.utils import timezone
from django.urls import resolve


class SessionValidationMiddleware:
    """会话验证中间件 - 根据规范实现"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 检查是否需要验证会话的API端点
        # 仅对需要认证的API端点进行验证
        if (request.path.startswith('/api/') or 
            request.path.startswith('/bootstrap/')) and \
           request.path not in ['/api/exchange_token/', '/bootstrap/exchange-token/']:
            
            # 检查Authorization头部
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                session_token = auth_header.split(' ')[1]
                
                # 验证会话有效性
                is_valid, result = self.check_session_validity(request, session_token)
                
                if not is_valid:
                    return JsonResponse({
                        'success': False,
                        'error': result
                    }, status=403)
        
        response = self.get_response(request)
        return response

    def check_session_validity(self, request, session_token):
        """检查会话有效性"""
        try:
            session = ActiveSession.objects.get(
                session_token=session_token,
                expires_at__gt=timezone.now()
            )
            
            # 获取真实客户端IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                current_ip = x_forwarded_for.split(',')[0].strip()
            else:
                current_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
            
            # IP校验
            if session.bound_ip != current_ip:
                return False, "IP address mismatch"
            
            return True, session
        except ActiveSession.DoesNotExist:
            return False, "Invalid or expired session token"