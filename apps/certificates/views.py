from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import permission_required
from .models import ServerCertificate, CertificateAuthority, ClientCertificate
from apps.hosts.models import Host
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404
import json
import logging
from datetime import datetime
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def issue_server_certificate(request):
    """签发服务器证书API"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        hostname = data.get('hostname')
        san_names = data.get('san_names', [])  # Subject Alternative Names
        ca_name = data.get('ca_name', 'default-ca')
        
        if not hostname:
            return JsonResponse({
                'success': False,
                'error': 'Hostname is required'
            }, status=400)
        
        # 获取或创建CA
        ca, created = CertificateAuthority.objects.get_or_create(
            name=ca_name,
            defaults={
                'name': ca_name,
                'description': f'Default CA for {ca_name}'
            }
        )
        if created:
            ca.generate_self_signed_cert()
            ca.save()
            logger.info(f"Created new CA: {ca_name}")
        
        # 检查是否已存在证书且未被吊销
        cert, created = ServerCertificate.objects.get_or_create(
            hostname=hostname,
            defaults={
                'hostname': hostname,
                'ca': ca
            }
        )
        
        if created or cert.is_revoked:
            # 生成新证书或重新生成已吊销的证书
            cert.generate_server_cert(hostname, san_names)
            cert.is_revoked = False  # 确保证书未被吊销
            cert.save()
            logger.info(f"Issued new server certificate for {hostname}")
        elif cert.expires_at < datetime.utcnow():
            # 证书已过期，重新生成
            cert.generate_server_cert(hostname, san_names)
            cert.save()
            logger.info(f"Renewed expired server certificate for {hostname}")
        
        return JsonResponse({
            'success': True,
            'data': {
                'ca_cert': ca.certificate,
                'server_cert': cert.certificate,
                'server_key': cert.private_key,
                'pfx_data': cert.pfx_data,
                'thumbprint': cert.thumbprint,
                'expires_at': cert.expires_at.isoformat()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error issuing server certificate: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def issue_client_certificate(request):
    """签发客户端证书API"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name')
        user_id = data.get('user_id')
        description = data.get('description', '')
        ca_name = data.get('ca_name', 'default-ca')
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Certificate name is required'
            }, status=400)
        
        # 获取或创建CA
        ca, created = CertificateAuthority.objects.get_or_create(
            name=ca_name,
            defaults={
                'name': ca_name,
                'description': f'Default CA for {ca_name}'
            }
        )
        if created:
            ca.generate_self_signed_cert()
            ca.save()
        
        # 获取用户对象（如果提供了user_id）
        user = None
        if user_id:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'User not found'
                }, status=404)
        
        # 创建或更新客户端证书
        cert, created = ClientCertificate.objects.get_or_create(
            name=name,
            defaults={
                'name': name,
                'ca': ca,
                'assigned_to_user': user,
                'description': description
            }
        )
        
        if created or not cert.certificate or cert.expires_at < datetime.utcnow():
            # 生成新证书或更新过期证书
            cert.generate_client_cert(name, user, description)
            cert.save()
            logger.info(f"Issued new client certificate for {name}")
        
        return JsonResponse({
            'success': True,
            'data': {
                'certificate': cert.certificate,
                'private_key': cert.private_key,
                'thumbprint': cert.thumbprint,
                'expires_at': cert.expires_at.isoformat()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error issuing client certificate: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def validate_certificate_request(request):
    """验证证书请求 - 验证主机认证令牌"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        hostname = data.get('hostname')
        token = data.get('token')  # 主机认证令牌
        
        if not hostname or not token:
            return JsonResponse({
                'success': False,
                'error': 'Hostname and token are required'
            }, status=400)
        
        # 验证令牌 - 检查主机是否存在且令牌有效
        host = Host.objects.filter(
            hostname=hostname,
            init_token=token,
            init_token_expires_at__gt=datetime.now()
        ).first()
        
        if not host:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or expired token'
            }, status=401)
        
        # 验证通过，返回相关信息
        return JsonResponse({
            'success': True,
            'data': {
                'hostname': hostname,
                'host_id': host.id,
                'valid': True
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error validating certificate request: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_ca_certificate(request):
    """获取CA根证书"""
    try:
        ca_name = request.GET.get('ca_name', 'default-ca')
        
        try:
            ca = CertificateAuthority.objects.get(name=ca_name, is_active=True)
            return JsonResponse({
                'success': True,
                'data': {
                    'ca_cert': ca.certificate,
                    'expires_at': ca.expires_at.isoformat()
                }
            })
        except CertificateAuthority.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'CA {ca_name} not found or not active'
            }, status=404)
        
    except Exception as e:
        logger.error(f"Error getting CA certificate: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


class CertificateManagementView(View):
    """证书管理视图类 - 需要管理员权限"""
    
    @method_decorator(permission_required('certificates.view_certificateauthority'))
    def get(self, request):
        """获取证书列表"""
        try:
            cert_type = request.GET.get('type', 'all')  # ca, server, client, all
            
            result = {'success': True, 'data': {}}
            
            if cert_type in ['all', 'ca']:
                cas = CertificateAuthority.objects.all()
                result['data']['cas'] = [
                    {
                        'id': ca.id,
                        'name': ca.name,
                        'created_at': ca.created_at.isoformat(),
                        'expires_at': ca.expires_at.isoformat(),
                        'is_active': ca.is_active
                    }
                    for ca in cas
                ]
            
            if cert_type in ['all', 'server']:
                servers = ServerCertificate.objects.select_related('ca').all()
                result['data']['servers'] = [
                    {
                        'id': cert.id,
                        'hostname': cert.hostname,
                        'ca_name': cert.ca.name,
                        'thumbprint': cert.thumbprint,
                        'created_at': cert.created_at.isoformat(),
                        'expires_at': cert.expires_at.isoformat(),
                        'is_revoked': cert.is_revoked
                    }
                    for cert in servers
                ]
            
            if cert_type in ['all', 'client']:
                clients = ClientCertificate.objects.select_related('ca', 'assigned_to_user').all()
                result['data']['clients'] = [
                    {
                        'id': cert.id,
                        'name': cert.name,
                        'ca_name': cert.ca.name,
                        'assigned_to_user': cert.assigned_to_user.username if cert.assigned_to_user else None,
                        'thumbprint': cert.thumbprint,
                        'created_at': cert.created_at.isoformat(),
                        'expires_at': cert.expires_at.isoformat(),
                        'is_active': cert.is_active
                    }
                    for cert in clients
                ]
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error getting certificates: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    @method_decorator(permission_required('certificates.delete_servercertificate'))
    def delete(self, request):
        """吊销或删除证书"""
        try:
            cert_id = request.GET.get('id')
            cert_type = request.GET.get('type', 'server')  # server, client
            
            if not cert_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Certificate ID is required'
                }, status=400)
            
            if cert_type == 'server':
                cert = get_object_or_404(ServerCertificate, id=cert_id)
                cert.revoke("Revoked by admin")
            elif cert_type == 'client':
                cert = get_object_or_404(ClientCertificate, id=cert_id)
                cert.is_active = False
                cert.save()
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid certificate type'
                }, status=400)
            
            return JsonResponse({
                'success': True,
                'message': f'{cert_type.title()} certificate revoked successfully'
            })
            
        except Exception as e:
            logger.error(f"Error revoking certificate: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def renew_certificate(request):
    """续订证书"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        cert_id = data.get('cert_id')
        cert_type = data.get('type', 'server')  # server, client
        
        if not cert_id:
            return JsonResponse({
                'success': False,
                'error': 'Certificate ID is required'
            }, status=400)
        
        if cert_type == 'server':
            cert = get_object_or_404(ServerCertificate, id=cert_id)
            # 重新生成证书
            cert.generate_server_cert(cert.hostname)
            cert.save()
        elif cert_type == 'client':
            cert = get_object_or_404(ClientCertificate, id=cert_id)
            cert.generate_client_cert(cert.name, cert.assigned_to_user, cert.description)
            cert.save()
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid certificate type'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': f'{cert_type.title()} certificate renewed successfully',
            'data': {
                'expires_at': cert.expires_at.isoformat()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error renewing certificate: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)