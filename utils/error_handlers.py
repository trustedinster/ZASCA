"""
异常处理工具模块
提供安全的异常处理和错误包装
"""
import logging
from typing import Optional, Any, Dict
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework.exceptions import APIException

logger = logging.getLogger('zasca')


class SecurityException(Exception):
    """安全相关异常"""
    pass


class WinRMConnectionException(Exception):
    """WinRM 连接异常"""
    pass


class InvalidUserInputException(Exception):
    """用户输入无效异常"""
    pass


def safe_exception_handler(func):
    """安全的异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SecurityException as e:
            # 安全异常，记录但不暴露详情
            logger.warning(f"Security exception in {func.__name__}: {str(e)}")
            raise Exception("操作被拒绝，请联系管理员")
        except WinRMConnectionException as e:
            # WinRM 连接异常，提供有用信息
            logger.error(f"WinRM connection error in {func.__name__}: {str(e)}")
            raise Exception("无法连接到远程主机，请检查主机状态和网络连接")
        except (DatabaseError, IntegrityError) as e:
            # 数据库异常，不暴露具体错误
            logger.error(f"Database error in {func.__name__}: {type(e).__name__}")
            raise Exception("数据处理失败，请稍后重试")
        except ValidationError as e:
            # 验证异常，可以返回原始信息
            logger.info(f"Validation error in {func.__name__}: {str(e)}")
            raise
        except PermissionDenied as e:
            # 权限异常
            logger.warning(f"Permission denied in {func.__name__}: {str(e)}")
            raise Exception("您没有执行此操作的权限")
        except APIException as e:
            # API 异常，保持原样
            raise
        except ValueError as e:
            # 值错误，提供有用信息
            logger.info(f"Value error in {func.__name__}: {str(e)}")
            raise Exception(f"无效的输入: {str(e)}")
        except Exception as e:
            # 其他未预期的异常
            from django.conf import settings
            logger.error(f"Unexpected error in {func.__name__}: {type(e).__name__}")
            # 在生产环境中不暴露内部错误
            if hasattr(settings, 'DEBUG') and settings.DEBUG:
                raise
            else:
                raise Exception("发生未知错误，请联系技术支持")
    return wrapper


def sanitize_error_message(error_msg: str, user_friendly: bool = True) -> str:
    """
    清理错误消息，移除敏感信息

    Args:
        error_msg: 原始错误消息
        user_friendly: 是否返回用户友好的消息

    Returns:
        清理后的错误消息
    """
    # 敏感信息模式
    sensitive_patterns = [
        r'password\s*[:=]\s*\S+',
        r'pwd\s*[:=]\s*\S+',
        r'secret\s*[:=]\s*\S+',
        r'token\s*[:=]\s*\S+',
        r'key\s*[:=]\s*\S+',
        r'\\Users\\\w+',  # Windows 用户名
        r'/home/\w+',     # Linux 用户名
        r'\d+\.\d+\.\d+\.\d+',  # IP 地址（部分脱敏）
    ]

    import re
    sanitized = error_msg

    for pattern in sensitive_patterns:
        sanitized = re.sub(pattern, '***', sanitized, flags=re.IGNORECASE)

    if user_friendly:
        # 替换技术术语为用户友好的消息
        replacements = {
            'NameResolutionError': '无法解析主机名',
            'ConnectionRefusedError': '连接被拒绝，请检查服务是否运行',
            'TimeoutError': '连接超时，请检查网络连接',
            'AuthenticationError': '认证失败，请检查用户名和密码',
            'AccessDenied': '访问被拒绝，权限不足',
            'NotFound': '请求的资源不存在',
        }

        for tech_term, friendly_msg in replacements.items():
            if tech_term in sanitized:
                sanitized = friendly_msg
                break

    return sanitized


def create_error_response(error: Exception, request=None) -> Dict[str, Any]:
    """
    创建标准的错误响应

    Args:
        error: 异常对象
        request: HTTP 请求对象（可选）

    Returns:
        错误响应字典
    """
    from django.conf import settings

    error_type = type(error).__name__
    error_message = str(error)

    # 清理错误消息
    if not (hasattr(settings, 'DEBUG') and settings.DEBUG):
        error_message = sanitize_error_message(error_message)

    response = {
        'success': False,
        'error': {
            'type': error_type,
            'message': error_message,
        }
    }

    # 添加追踪 ID（如果有）
    import uuid
    response['trace_id'] = str(uuid.uuid4())

    # 添加请求信息（如果有）
    if request:
        response['request_id'] = getattr(request, 'request_id', None)
        response['user'] = request.user.username if request.user.is_authenticated else 'anonymous'

    return response