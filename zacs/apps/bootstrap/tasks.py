from celery import shared_task
from django.utils import timezone
from .models import ActiveSession, InitialToken
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_sessions():
    """清理过期的活动会话"""
    try:
        expired_sessions = ActiveSession.objects.filter(expires_at__lt=timezone.now())
        count = expired_sessions.count()
        expired_sessions.delete()
        
        logger.info(f"清理了 {count} 个过期的活动会话")
        return f"清理了 {count} 个过期的活动会话"
    except Exception as e:
        logger.error(f"清理过期会话时出错: {str(e)}")
        raise


@shared_task
def cleanup_expired_initial_tokens():
    """清理过期的初始令牌"""
    try:
        # 删除已过期且已消耗的令牌，或者过期超过7天的令牌
        cutoff_time = timezone.now() - timedelta(days=7)
        expired_tokens = InitialToken.objects.filter(
            expires_at__lt=cutoff_time
        )
        count = expired_tokens.count()
        expired_tokens.delete()
        
        logger.info(f"清理了 {count} 个过期的初始令牌")
        return f"清理了 {count} 个过期的初始令牌"
    except Exception as e:
        logger.error(f"清理过期初始令牌时出错: {str(e)}")
        raise


@shared_task
def generate_bootstrap_config(hostname, ip_address, operator_id):
    """生成引导配置 - 模拟函数"""
    try:
        # 这里应该是实际的引导配置生成逻辑
        # 模拟返回一些配置信息
        config = {
            'hostname': hostname,
            'ip_address': ip_address,
            'generated_at': timezone.now().isoformat(),
            'status': 'success'
        }
        
        return {
            'success': True,
            'config': config
        }
    except Exception as e:
        logger.error(f"生成引导配置时出错: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def initialize_host_bootstrap(host_id, operator_id):
    """初始化主机引导 - 模拟函数"""
    try:
        # 这里应该是实际的主机引导初始化逻辑
        from apps.hosts.models import Host
        host = Host.objects.get(id=host_id)
        
        # 模拟引导过程
        result = {
            'host_id': host_id,
            'hostname': host.hostname,
            'status': 'completed',
            'completed_at': timezone.now().isoformat()
        }
        
        return result
    except Exception as e:
        logger.error(f"初始化主机引导时出错: {str(e)}")
        raise
