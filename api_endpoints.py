"""
需要在C端实现的API端点示例
将这些代码添加到你的Django项目的views.py中
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def get_session_token(request):
    """
    H端用来获取SessionToken的API端点
    POST /api/get_session_token/
    Authorization: Bearer {initial_token}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # 从Authorization头获取InitialToken
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Invalid authorization header'}, status=401)
    
    initial_token = auth_header[7:]  # 移除 'Bearer ' 前缀
    
    try:
        # 查找对应的InitialToken记录
        from apps.bootstrap.models import InitialToken
        
        token_obj = InitialToken.objects.get(
            initial_token=initial_token,
            status__in=['ISSUED', 'TOTP_VERIFIED'],
            expires_at__gt=timezone.now()
        )
        
        # 创建ActiveSession记录
        from apps.bootstrap.models import ActiveSession
        import uuid
        
        session = ActiveSession.objects.create(
            host=token_obj.host,
            session_token=str(uuid.uuid4()),
            bound_ip=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            expires_at=timezone.now() + timezone.timedelta(hours=1)  # 1小时有效期
        )
        
        # 更新InitialToken状态
        token_obj.status = 'CONSUMED'
        token_obj.save()
        
        logger.info(f"为InitialToken {initial_token[:8]}... 创建了SessionToken {session.session_token[:8]}...")
        
        return JsonResponse({
            'session_token': session.session_token,
            'expires_in': 3600  # 1小时，单位秒
        })
        
    except InitialToken.DoesNotExist:
        logger.warning(f"无效的InitialToken: {initial_token[:8]}...")
        return JsonResponse({'error': 'Invalid or expired initial token'}, status=401)
    except Exception as e:
        logger.error(f"获取SessionToken时出错: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

# 记得在urls.py中添加路由：
"""
urlpatterns = [
    path('api/get_session_token/', get_session_token, name='get_session_token'),
    # ... 其他路由
]
"""