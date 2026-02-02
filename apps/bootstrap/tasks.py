from celery import shared_task
from django.contrib.auth.models import User
from apps.bootstrap.models import BootstrapToken
from apps.hosts.models import Host
from apps.certificates.models import ServerCertificate, CertificateAuthority
from apps.tasks.models import AsyncTask
from apps.hosts.tasks import configure_winrm_on_host
import logging
import uuid
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def initialize_host_bootstrap(self, host_id, operator_id):
    """主机初始化引导任务"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"主机初始化引导 #{host_id}",
        created_by_id=operator_id,
        target_object_id=host_id,
        target_content_type='hosts.Host',
        status='running'
    )
    
    try:
        host = Host.objects.get(id=host_id)
        task.start_execution()
        
        # 更新进度
        task.progress = 10
        task.save()
        
        # 1. 生成初始化令牌
        bootstrap_token = BootstrapToken.objects.create(
            host=host,
            expires_at=timezone.now() + timedelta(hours=24),  # 24小时有效期
            created_by_id=operator_id
        )
        
        task.progress = 20
        task.save()
        
        # 记录进度
        from apps.tasks.models import TaskProgress
        TaskProgress.objects.create(
            task=task,
            progress=20,
            message="生成初始化令牌"
        )
        
        # 2. 为该主机生成服务器证书
        ca, created = CertificateAuthority.objects.get_or_create(
            name='default-ca',
            defaults={'name': 'default-ca', 'description': 'Default Certificate Authority'}
        )
        if created:
            ca.generate_self_signed_cert()
            ca.save()
        
        cert, created = ServerCertificate.objects.get_or_create(
            hostname=host.hostname,
            defaults={
                'hostname': host.hostname,
                'ca': ca
            }
        )
        
        if created or cert.is_revoked:
            cert.generate_server_cert(host.hostname, [host.ip_address])
            cert.is_revoked = False
            cert.save()
        
        task.progress = 40
        task.save()
        
        TaskProgress.objects.create(
            task=task,
            progress=40,
            message="生成服务器证书"
        )
        
        # 3. 更新主机状态为初始化中
        host.init_status = 'initializing'
        host.init_token = bootstrap_token.token
        host.init_token_expires_at = bootstrap_token.expires_at
        host.save()
        
        task.progress = 60
        task.save()
        
        TaskProgress.objects.create(
            task=task,
            progress=60,
            message="更新主机状态"
        )
        
        # 4. 触发WinRM配置任务
        configure_winrm_result = configure_winrm_on_host.delay(
            host_id=host.id,
            cert_thumbprint=cert.thumbprint,
            operator_id=operator_id
        )
        
        task.progress = 80
        task.save()
        
        TaskProgress.objects.create(
            task=task,
            progress=80,
            message="启动WinRM配置任务"
        )
        
        # 等待WinRM配置完成
        configure_result = configure_winrm_result.get(timeout=300)  # 最多等待5分钟
        
        if configure_result.get('success'):
            host.init_status = 'ready'
            host.certificate_thumbprint = cert.thumbprint
            host.initialized_at = timezone.now()
            host.save()
            
            task.progress = 100
            task.complete_success({
                'host_id': host.id,
                'hostname': host.hostname,
                'cert_thumbprint': cert.thumbprint,
                'configure_result': configure_result
            })
            
            TaskProgress.objects.create(
                task=task,
                progress=100,
                message="主机初始化完成"
            )
        else:
            task.complete_failure(f"WinRM配置失败: {configure_result.get('error')}")
            
    except Exception as e:
        logger.error(f"主机初始化引导失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
    
    return {
        'task_id': task.task_id,
        'success': task.status == 'success',
        'host_id': host_id if 'host' in locals() else None
    }


@shared_task(bind=True)
def generate_bootstrap_config(self, hostname, ip_address, operator_id):
    """生成主机引导配置"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"生成引导配置 - {hostname}",
        created_by_id=operator_id,
        status='running'
    )
    
    try:
        task.start_execution()
        
        # 获取或创建CA
        ca, created = CertificateAuthority.objects.get_or_create(
            name='default-ca',
            defaults={'name': 'default-ca', 'description': 'Default Certificate Authority'}
        )
        if created:
            ca.generate_self_signed_cert()
            ca.save()
        
        # 生成服务器证书
        cert, created = ServerCertificate.objects.get_or_create(
            hostname=hostname,
            defaults={
                'hostname': hostname,
                'ca': ca
            }
        )
        
        if created or cert.is_revoked:
            cert.generate_server_cert(hostname, [ip_address])
            cert.is_revoked = False
            cert.save()
        
        task.progress = 50
        task.save()
        
        # 准备配置数据
        config_data = {
            'ca_cert': ca.certificate,
            'server_cert': cert.certificate,
            'server_key': cert.private_key,
            'pfx_data': cert.pfx_data,
            'thumbprint': cert.thumbprint,
            'winrm_config': {
                'port': 5986,
                'certificate_subject': f'CN={hostname}',
                'auth_methods': ['Certificate', 'Basic']
            },
            'firewall_rules': [
                {
                    'name': 'WinRM-HTTPS-In-TCP',
                    'port': 5986,
                    'protocol': 'TCP',
                    'direction': 'Inbound'
                }
            ],
            'cleanup_commands': [
                'del temp_cert.pfx',
                'del bootstrap_script.py'
            ]
        }
        
        task.progress = 100
        task.complete_success(config_data)
        
        return {
            'success': True,
            'config': config_data
        }
        
    except Exception as e:
        logger.error(f"生成引导配置失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
        return {
            'success': False,
            'error': str(e)
        }