"""
Redis 辅助工具模块

提供 Redis 可选支持：配置了 REDIS_URL 且 Redis 服务可达时自动启用，
否则静默降级到本地替代方案（LocMemCache / DB Session / SQLite Celery）。

延迟导入策略：
- REDIS_URL 未配置时，绝不 import redis 包
- redis 包未安装时，静默降级，不报错

使用方式：
    from utils.redis_helper import is_redis_available, get_redis_client

    if is_redis_available():
        client = get_redis_client()
        client.set('key', 'value')
"""

import logging
import os

logger = logging.getLogger('2c2a')

_redis_client = None
_redis_available = None


def _get_redis_url():
    return os.environ.get('REDIS_URL', '').strip()


def is_redis_available():
    """
    检查 Redis 是否可用。

    首次调用时会尝试连接 Redis 并缓存结果，
    后续调用直接返回缓存值。

    REDIS_URL 未配置时不 import redis，redis 包未安装也不报错。
    """
    global _redis_available
    if _redis_available is not None:
        return _redis_available

    url = _get_redis_url()
    if not url:
        logger.info('REDIS_URL not configured, using local alternatives')
        _redis_available = False
        return False

    try:
        import redis
        client = redis.Redis.from_url(url, socket_connect_timeout=3)
        client.ping()
        logger.info('Redis is available, will use Redis for cache/session/celery')
        _redis_available = True
    except Exception as e:
        logger.warning(
            'REDIS_URL is configured but Redis is unreachable or redis package not installed, '
            'falling back to local alternatives: %s', e,
        )
        _redis_available = False

    return _redis_available


def get_redis_client():
    """
    获取 Redis 客户端实例。

    Returns:
        redis.Redis | None: Redis 客户端，不可用时返回 None
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not is_redis_available():
        return None

    try:
        import redis
        url = _get_redis_url()
        _redis_client = redis.Redis.from_url(url, socket_connect_timeout=3)
        return _redis_client
    except Exception as e:
        logger.warning('Failed to create Redis client: %s', e)
        return None


def reset_redis_state():
    """
    重置 Redis 状态缓存（主要用于测试）
    """
    global _redis_client, _redis_available
    _redis_client = None
    _redis_available = None
