from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from django.views import View
from .models import BootstrapToken
from apps.hosts.models import Host
from apps.certificates.models import CertificateAuthority, ServerCertificate
from apps.tasks.models import AsyncTask
from apps.bootstrap.tasks import generate_bootstrap_config, initialize_host_bootstrap
from django.shortcuts import get_object_or_404
import json
import logging
from datetime import datetime

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
        
        # 验证引导令牌
        try:
            token_obj = BootstrapToken.objects.get(
                token=auth_token,
                is_used=False,
                expires_at__gt=datetime.now()
            )
        except BootstrapToken.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or expired bootstrap token'
            }, status=401)
        
        # 验证主机是否匹配令牌
        if token_obj.host.hostname != hostname:
            return JsonResponse({
                'success': False,
                'error': 'Hostname does not match the token'
            }, status=400)
        
        # 标记令牌为已使用
        token_obj.mark_as_used()
        
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
                'data': config_result['config']
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
def create_bootstrap_token(request):
    """创建引导令牌API"""
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
        
        # 创建引导令牌
        from datetime import timedelta
        from django.utils import timezone
        
        token = BootstrapToken.objects.create(
            host=host,
            created_by=operator,
            expires_at=timezone.now() + timedelta(hours=expire_hours)
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'token': token.token,
                'expires_at': token.expires_at.isoformat(),
                'host_id': host.id,
                'hostname': host.hostname
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating bootstrap token: {str(e)}", exc_info=True)
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
                bootstrap_token = BootstrapToken.objects.get(token=token)
                host = bootstrap_token.host
            except BootstrapToken.DoesNotExist:
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
                'init_status': host.init_status,
                'initialized_at': host.initialized_at.isoformat() if host.initialized_at else None,
                'certificate_thumbprint': host.certificate_thumbprint,
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
    
    @method_decorator(permission_required('bootstrap.view_bootstraptoken'))
    def get(self, request):
        """获取引导令牌列表"""
        try:
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)  # 最大100条每页
            status_filter = request.GET.get('status')  # pending, used, expired, all
            
            queryset = BootstrapToken.objects.select_related('host', 'created_by').all()
            
            # 状态过滤
            if status_filter == 'pending':
                from django.utils import timezone
                queryset = queryset.filter(is_used=False, expires_at__gt=timezone.now())
            elif status_filter == 'used':
                queryset = queryset.filter(is_used=True)
            elif status_filter == 'expired':
                from django.utils import timezone
                queryset = queryset.filter(expires_at__lt=timezone.now(), is_used=False)
            elif status_filter != 'all':
                # 默认显示未使用且未过期的
                from django.utils import timezone
                queryset = queryset.filter(is_used=False, expires_at__gt=timezone.now())
            
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
                            'id': token.id,
                            'token': token.token,
                            'hostname': token.host.hostname,
                            'host_id': token.host.id,
                            'created_by': token.created_by.username if token.created_by else 'System',
                            'created_at': token.created_at.isoformat(),
                            'expires_at': token.expires_at.isoformat(),
                            'is_used': token.is_used,
                            'used_at': token.used_at.isoformat() if token.used_at else None,
                            'used_by': token.used_by.username if token.used_by else None,
                            'is_expired': token.is_expired()
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
    
    @method_decorator(permission_required('bootstrap.delete_bootstraptoken'))
    def delete(self, request):
        """删除引导令牌"""
        try:
            token_id = request.GET.get('id')
            
            if not token_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Token ID is required'
                }, status=400)
            
            token = get_object_or_404(BootstrapToken, id=token_id)
            token.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Bootstrap token deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting bootstrap token: {str(e)}", exc_info=True)
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
            token_obj = BootstrapToken.objects.get(
                token=token,
                is_used=False,
                expires_at__gt=datetime.now()
            )
            
            return JsonResponse({
                'success': True,
                'data': {
                    'valid': True,
                    'host_id': token_obj.host.id,
                    'hostname': token_obj.host.hostname,
                    'expires_at': token_obj.expires_at.isoformat()
                }
            })
        except BootstrapToken.DoesNotExist:
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