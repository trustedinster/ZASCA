from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from django.views import View
from .models import InitialToken, ActiveSession
from apps.hosts.models import Host
from apps.certificates.models import CertificateAuthority, ServerCertificate
from apps.tasks.models import AsyncTask
from apps.bootstrap.tasks import generate_bootstrap_config, initialize_host_bootstrap
from django.shortcuts import get_object_or_404
import json
import logging
from datetime import datetime
import pyotp
from django.utils import timezone
import secrets
import uuid


logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def get_bootstrap_config(request):
    """获取主机引导配置API"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        hostname = data.get('hostname')
        ip_address = data.get('ip_address')
        auth_token = data.get('auth_token')  # 认证令牌
        
        if not hostname or not auth_token:
            return JsonResponse({
                'success': False,
                'error': 'Hostname and auth_token are required'
            }, status=400)
        
        # 验证初始令牌
        try:
            token_obj = InitialToken.objects.get(
                token=auth_token,
                status='TOTP_VERIFIED',  # 确保已经TOTP验证
                expires_at__gt=timezone.now()
            )
        except InitialToken.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or unauthorized bootstrap token'
            }, status=401)
        
        # 验证主机是否匹配令牌
        if str(token_obj.host.id) != data.get('host_id', ''):
            return JsonResponse({
                'success': False,
                'error': 'Host ID does not match the token'
            }, status=400)
        
        # 标记令牌为已使用
        token_obj.status = 'CONSUMED'
        token_obj.save()
        
        # 生成活动会话
        session_token = str(uuid.uuid4())
        bound_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        ActiveSession.objects.create(
            session_token=session_token,
            host=token_obj.host,
            bound_ip=bound_ip,
            expires_at=timezone.now() + timezone.timedelta(days=1)  # 24小时有效期
        )
        
        # 生成引导配置（异步任务）
        from django.contrib.auth.models import User
        admin_user = User.objects.filter(is_superuser=True).first()
        operator_id = admin_user.id if admin_user else None
        
        task_result = generate_bootstrap_config.delay(
            hostname=hostname,
            ip_address=ip_address or token_obj.host.ip_address,
            operator_id=operator_id
        )
        
        # 等待任务完成（最多等待30秒）
        config_result = task_result.get(timeout=30)
        
        if config_result['success']:
            return JsonResponse({
                'success': True,
                'data': config_result['config'],
                'session_token': session_token  # 返回新的会话令牌
            })
        else:
            return JsonResponse({
                'success': False,
                'error': config_result.get('error', 'Failed to generate bootstrap config')
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error getting bootstrap config: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def trigger_host_bootstrap(request):
    """触发主机引导流程API"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        host_id = data.get('host_id')
        operator_id = data.get('operator_id')  # 操作员ID
        
        if not host_id:
            return JsonResponse({
                'success': False,
                'error': 'Host ID is required'
            }, status=400)
        
        if not operator_id:
            return JsonResponse({
                'success': False,
                'error': 'Operator ID is required'
            }, status=400)
        
        # 验证主机存在
        try:
            host = Host.objects.get(id=host_id)
        except Host.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Host not found'
            }, status=404)
        
        # 启动引导任务
        task_result = initialize_host_bootstrap.delay(
            host_id=host_id,
            operator_id=operator_id
        )
        
        # 等待任务开始（不等待完成，因为这可能需要较长时间）
        task_info = task_result.info
        
        return JsonResponse({
            'success': True,
            'data': {
                'task_id': task_result.id,
                'host_id': host_id,
                'hostname': host.hostname,
                'status': 'started'
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error triggering host bootstrap: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_initial_token(request):
    """创建初始令牌API - 根据规范"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        host_id = data.get('host_id')
        operator_id = data.get('operator_id')  # 创建者ID
        expire_hours = data.get('expire_hours', 24)  # 默认24小时过期
        
        if not host_id:
            return JsonResponse({
                'success': False,
                'error': 'Host ID is required'
            }, status=400)
        
        if not operator_id:
            return JsonResponse({
                'success': False,
                'error': 'Operator ID is required'
            }, status=400)
        
        # 验证主机存在
        try:
            host = Host.objects.get(id=host_id)
        except Host.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Host not found'
            }, status=404)
        
        # 验证操作员存在
        from django.contrib.auth.models import User
        try:
            operator = User.objects.get(id=operator_id)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Operator not found'
            }, status=404)
        
        # 创建初始令牌
        from datetime import timedelta
        from django.utils import timezone
        
        token = secrets.token_urlsafe(32)  # 生成安全的随机令牌
        expires_at = timezone.now() + timedelta(hours=expire_hours)
        
        initial_token = InitialToken.objects.create(
            token=token,
            host=host,
            expires_at=expires_at,
            status='ISSUED'
        )
        
        # 计算TOTP密钥
        totp_secret = initial_token.generate_totp_secret()
        
        return JsonResponse({
            'success': True,
            'data': {
                'token': initial_token.token,
                'expires_at': initial_token.expires_at.isoformat(),
                'host_id': host.id,
                'hostname': host.hostname,
                'totp_secret': totp_secret  # 返回TOTP密钥用于验证
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating initial token: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_bootstrap_status(request):
    """检查引导状态API"""
    try:
        token = request.GET.get('token')
        host_id = request.GET.get('host_id')
        
        if not token and not host_id:
            return JsonResponse({
                'success': False,
                'error': 'Either token or host_id is required'
            }, status=400)
        
        if token:
            # 通过令牌查询
            try:
                initial_token = InitialToken.objects.get(token=token)
                host = initial_token.host
            except InitialToken.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid token'
                }, status=404)
        else:
            # 通过主机ID查询
            try:
                host = Host.objects.get(id=host_id)
            except Host.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Host not found'
                }, status=404)
        
        return JsonResponse({
            'success': True,
            'data': {
                'host_id': host.id,
                'hostname': host.hostname,
                'init_status': host.init_status if hasattr(host, 'init_status') else 'unknown',
                'initialized_at': getattr(host, 'initialized_at', None),
                'certificate_thumbprint': getattr(host, 'certificate_thumbprint', None),
                'ip_address': host.ip_address,
                'port': host.port
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking bootstrap status: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


class BootstrapManagementView(View):
    """引导管理视图 - 需要管理员权限"""
    
    @method_decorator(permission_required('bootstrap.view_initialtoken'))
    def get(self, request):
        """获取引导令牌列表"""
        try:
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)  # 最大100条每页
            status_filter = request.GET.get('status')  # issued, verified, consumed, all
            
            queryset = InitialToken.objects.select_related('host').all()
            
            # 状态过滤
            if status_filter == 'issued':
                queryset = queryset.filter(status='ISSUED')
            elif status_filter == 'verified':
                queryset = queryset.filter(status='TOTP_VERIFIED')
            elif status_filter == 'consumed':
                queryset = queryset.filter(status='CONSUMED')
            elif status_filter == 'expired':
                from django.utils import timezone
                queryset = queryset.filter(expires_at__lt=timezone.now())
            elif status_filter != 'all':
                # 默认显示未过期的
                from django.utils import timezone
                queryset = queryset.filter(expires_at__gt=timezone.now())
            
            # 分页
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            tokens = queryset[start_idx:end_idx]
            
            total_count = queryset.count()
            
            result = {
                'success': True,
                'data': {
                    'tokens': [
                        {
                            'id': token.token,
                            'token': token.token,
                            'hostname': token.host.hostname,
                            'host_id': token.host.id,
                            'created_at': token.created_at.isoformat(),
                            'expires_at': token.expires_at.isoformat(),
                            'status': token.status,
                            'is_expired': token.expires_at < timezone.now()
                        }
                        for token in tokens
                    ],
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size
                    }
                }
            }
            
            return JsonResponse(result)
            
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid page or page_size parameter'
            }, status=400)
        except Exception as e:
            logger.error(f"Error getting bootstrap tokens: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @method_decorator(permission_required('bootstrap.delete_initialtoken'))
    def delete(self, request):
        """删除引导令牌"""
        try:
            token_id = request.GET.get('id')
            
            if not token_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Token ID is required'
                }, status=400)
            
            token = get_object_or_404(InitialToken, token=token_id)
            token.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Initial token deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting initial token: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def validate_bootstrap_token(request):
    """验证引导令牌有效性"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        token = data.get('token')
        
        if not token:
            return JsonResponse({
                'success': False,
                'error': 'Token is required'
            }, status=400)
        
        try:
            token_obj = InitialToken.objects.get(
                token=token,
                status__in=['ISSUED', 'TOTP_VERIFIED'],  # 未消耗的令牌
                expires_at__gt=timezone.now()
            )
            
            return JsonResponse({
                'success': True,
                'data': {
                    'valid': True,
                    'host_id': token_obj.host.id,
                    'hostname': token_obj.host.hostname,
                    'expires_at': token_obj.expires_at.isoformat(),
                    'status': token_obj.status
                }
            })
        except InitialToken.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or expired token'
            }, status=401)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error validating bootstrap token: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_totp(request):
    """TOTP验证接口 - 根据规范"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        host_id = data.get('host_id')
        totp_code = data.get('totp_code')
        
        if not host_id or not totp_code:
            return JsonResponse({
                'success': False,
                'error': 'Host ID and TOTP code are required'
            }, status=400)
        
        # 查找对应的初始令牌
        try:
            initial_tokens = InitialToken.objects.filter(
                host_id=host_id,
                status='ISSUED',  # 只处理已签发但未验证的令牌
                expires_at__gt=timezone.now()
            )
            
            if not initial_tokens.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'No valid initial token found for this host'
                }, status=404)
            
            # 尝试验证TOTP码
            verified = False
            for token_obj in initial_tokens:
                totp_secret = token_obj.generate_totp_secret()
                
                # 使用pyotp验证TOTP码
                totp = pyotp.TOTP(totp_secret)
                
                # 验证当前码和允许1个时间窗口的偏移
                current_time = int(datetime.now().timestamp())
                for offset in [-30, 0, 30]:  # 允许前后30秒的偏移
                    expected_time = current_time + offset
                    expected_code = totp.at(expected_time)
                    
                    if expected_code == totp_code:
                        # 验证成功，更新令牌状态
                        token_obj.status = 'TOTP_VERIFIED'
                        token_obj.save()
                        
                        verified = True
                        break
                
                if verified:
                    break
            
            if verified:
                return JsonResponse({
                    'success': True,
                    'message': 'TOTP verification successful'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid TOTP code'
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error verifying TOTP: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error validating TOTP: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def exchange_token(request):
    """令牌交换接口 - 根据规范"""
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'success': False,
                'error': 'Authorization header missing or invalid'
            }, status=401)
        
        access_token = auth_header.split(' ')[1]
        
        # 验证AccessToken
        try:
            initial_token = InitialToken.objects.get(
                token=access_token,
                status='TOTP_VERIFIED',  # 必须是已验证的令牌
                expires_at__gt=timezone.now()
            )
        except InitialToken.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or unauthorized access token'
            }, status=401)
        
        # 获取真实客户端IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # 原子操作：生成新的session_token，创建ActiveSession记录，并将InitialToken标记为已消耗
        from django.db import transaction
        with transaction.atomic():
            # 生成新的session_token
            session_token = str(uuid.uuid4())
            
            # 在ActiveSession表中插入记录
            ActiveSession.objects.create(
                session_token=session_token,
                host=initial_token.host,
                bound_ip=ip,
                expires_at=timezone.now() + timezone.timedelta(days=1)  # 24小时后过期
            )
            
            # 立即将InitialToken表中该记录的状态更新为CONSUMED
            initial_token.status = 'CONSUMED'
            initial_token.save()
        
        return JsonResponse({
            'success': True,
            'session_token': session_token,
            'expires_in': 86400  # 24小时（秒）
        })
        
    except Exception as e:
        logger.error(f"Error exchanging token: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def revoke_session(request):
    """吊销会话接口 - 根据规范"""
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'success': False,
                'error': 'Authorization header missing or invalid'
            }, status=401)
        
        session_token = auth_header.split(' ')[1]
        
        # 删除ActiveSession表中的对应记录
        try:
            session = ActiveSession.objects.get(session_token=session_token)
            session.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Session revoked successfully'
            })
        except ActiveSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid session token'
            }, status=401)
        
    except Exception as e:
        logger.error(f"Error revoking session: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def check_session_validity(request, session_token):
    """检查会话有效性 - 中间件辅助函数"""
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


class SessionValidationMiddleware:
    """会话验证中间件"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 检查是否需要验证会话的API端点
        if request.path.startswith('/api/') and 'session_token' in request.headers:
            session_token = request.headers.get('session_token')
            is_valid, result = check_session_validity(request, session_token)
            
            if not is_valid:
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'error': result
                }, status=403)
        
        response = self.get_response(request)
        return response