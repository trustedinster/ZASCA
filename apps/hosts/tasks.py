from celery import shared_task
from django.contrib.auth.models import User
from apps.hosts.models import Host
from apps.tasks.models import AsyncTask
from apps.certificates.models import ServerCertificate, ClientCertificate
import logging
import winrm

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def configure_winrm_on_host(self, host_id, cert_thumbprint=None, operator_id=None):
    """配置主机上的WinRM服务"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"配置WinRM - 主机 #{host_id}",
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
        
        # 使用现有的连接信息测试连接
        try:
            session = winrm.Session(
                f'http://{host.ip_address}:{host.port}',
                auth=(host.username, host.password)
            )
            
            # 配置WinRM服务
            ps_script = '''
            # 启用WinRM服务
            Enable-PSRemoting -Force
            
            # 配置WinRM服务为自动启动
            Set-Service -Name WinRM -StartupType Automatic
            
            # 创建HTTPS监听器
            $currentUrl = "https://" + $env:COMPUTERNAME + ":5986/wsman"
            $selectorset = @{Transport="HTTPS"}
            $resourceset = @{Port="5986"; CertificateThumbprint="%s"}
            
            # 删除现有的HTTPS监听器
            Get-WSManInstance -ResourceURI winrm/config/listener -SelectorSet $selectorset -ErrorAction SilentlyContinue | Remove-WSManInstance -ErrorAction SilentlyContinue
            
            # 创建新的HTTPS监听器
            New-WSManInstance -ResourceURI winrm/config/listener -SelectorSet $selectorset -ValueSet $resourceset
            
            # 配置防火墙规则
            if (-not (Get-NetFirewallRule -Name "WinRM-HTTPS-In-TCP-Public" -ErrorAction SilentlyContinue)) {
                New-NetFirewallRule -Name "WinRM-HTTPS-In-TCP-Public" -DisplayName "WinRM HTTPS Inbound" -Enabled True -Direction Inbound -Protocol TCP -LocalPort 5986 -Action Allow -Profile Public,Private,Domain
            }
            
            # 配置基本认证
            Set-Item -Path "WSMan:\\localhost\\Service\\AllowUnencrypted" -Value $false
            Set-Item -Path "WSMan:\\localhost\\Service\\Auth\\Basic" -Value $true
            
            # 重启WinRM服务
            Restart-Service WinRM
            ''' % (cert_thumbprint or host.certificate_thumbprint or "PLACEHOLDER_CERT_THUMBPRINT")
            
            task.progress = 30
            task.save()
            
            result = session.run_ps(ps_script)
            
            if result.status_code == 0:
                task.progress = 80
                task.save()
                
                # 更新主机状态
                host.init_status = 'ready'
                host.initialized_at = timezone.now()
                if cert_thumbprint:
                    host.certificate_thumbprint = cert_thumbprint
                host.save()
                
                task.progress = 100
                task.complete_success({
                    'status_code': result.status_code,
                    'stdout': result.std_out.decode('utf-8') if result.std_out else '',
                    'success': True
                })
                
                return {
                    'success': True,
                    'status_code': result.status_code,
                    'host_id': host_id
                }
            else:
                error_msg = result.std_err.decode('utf-8') if result.std_err else 'Unknown error'
                task.complete_failure(f"PowerShell script failed: {error_msg}")
                
                return {
                    'success': False,
                    'status_code': result.status_code,
                    'error': error_msg
                }
                
        except Exception as conn_error:
            logger.error(f"连接主机失败: {str(conn_error)}", exc_info=True)
            task.complete_failure(f"无法连接到主机: {str(conn_error)}")
            
            return {
                'success': False,
                'error': str(conn_error)
            }
        
    except Exception as e:
        logger.error(f"配置WinRM失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
        
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(bind=True)
def test_winrm_connection(self, host_id, use_certificate_auth=False):
    """测试WinRM连接"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"测试WinRM连接 - 主机 #{host_id}",
        status='running'
    )
    
    try:
        host = Host.objects.get(id=host_id)
        task.start_execution()
        
        if use_certificate_auth and host.certificate_thumbprint:
            # 使用证书认证
            import ssl
            import tempfile
            import os
            
            # 创建临时客户端证书文件用于认证
            client_cert = ClientCertificate.objects.filter(is_active=True).first()
            if not client_cert:
                # 如果没有可用的客户端证书，创建一个
                ca = host.get_ca() if hasattr(host, 'get_ca') else None
                if not ca:
                    ca, _ = CertificateAuthority.objects.get_or_create(
                        name='default-ca',
                        defaults={'name': 'default-ca', 'description': 'Default Certificate Authority'}
                    )
                    if not ca.certificate:
                        ca.generate_self_signed_cert()
                        ca.save()
                
                client_cert = ClientCertificate(
                    name=f'client-{host.hostname}',
                    ca=ca
                )
                client_cert.generate_client_cert(f'client-{host.hostname}')
                client_cert.save()
            
            # 保存证书到临时文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as cert_file:
                cert_file.write(client_cert.certificate)
                cert_file_path = cert_file.name
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as key_file:
                key_file.write(client_cert.private_key)
                key_file_path = key_file.name
            
            try:
                session = winrm.Session(
                    f'https://{host.ip_address}:5986',
                    auth=(None, None),  # 使用证书认证，不需要用户名密码
                    server_cert_validation='validate',
                    cert_pem=cert_file_path,
                    key_pem=key_file_path
                )
                
                # 执行简单命令测试连接
                result = session.run_cmd('echo "Connection Test"')
                
                success = result.status_code == 0
                
            finally:
                # 清理临时文件
                os.unlink(cert_file_path)
                os.unlink(key_file_path)
        else:
            # 使用基本认证
            session = winrm.Session(
                f'http://{host.ip_address}:{host.port}',
                auth=(host.username, host.password)
            )
            
            # 执行简单命令测试连接
            result = session.run_cmd('echo "Connection Test"')
            
            success = result.status_code == 0
        
        if success:
            task.progress = 100
            task.complete_success({
                'connected': True,
                'protocol': 'HTTPS with Certificate' if use_certificate_auth else 'HTTP with Basic Auth',
                'message': 'Connection successful'
            })
            
            return {
                'success': True,
                'connected': True,
                'protocol': 'HTTPS with Certificate' if use_certificate_auth else 'HTTP with Basic Auth'
            }
        else:
            task.complete_failure("Connection test failed")
            return {
                'success': False,
                'connected': False,
                'error': 'Connection test returned non-zero exit code'
            }
        
    except Exception as e:
        logger.error(f"测试WinRM连接失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
        
        return {
            'success': False,
            'connected': False,
            'error': str(e)
        }


@shared_task(bind=True)
def install_certificates_on_host(self, host_id, cert_pem, cert_filename, operator_id=None):
    """在主机上安装证书"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"安装证书 - 主机 #{host_id}",
        created_by_id=operator_id,
        target_object_id=host_id,
        target_content_type='hosts.Host',
        status='running'
    )
    
    try:
        host = Host.objects.get(id=host_id)
        task.start_execution()
        
        # 将证书内容写入PowerShell脚本
        ps_script = f'''
        # 创建临时目录
        $tempDir = "$env:TEMP\\ZASCA_Certs"
        if (!(Test-Path $tempDir)) {{
            New-Item -ItemType Directory -Path $tempDir -Force
        }}
        
        # 写入证书内容到临时文件
        $certContent = @"
{cert_pem}
"@
        
        $certPath = Join-Path $tempDir "{cert_filename}"
        $certContent | Out-File -FilePath $certPath -Encoding UTF8
        
        # 导入证书到受信任的根证书颁发机构存储区
        Import-Certificate -FilePath $certPath -CertStoreLocation Cert:\\LocalMachine\\Root
        
        # 导入证书到个人存储区
        Import-Certificate -FilePath $certPath -CertStoreLocation Cert:\\LocalMachine\\My
        
        Write-Output "Certificate installed successfully"
        
        # 清理临时文件
        Remove-Item $tempDir -Recurse -Force
        '''
        
        session = winrm.Session(
            f'http://{host.ip_address}:{host.port}',
            auth=(host.username, host.password)
        )
        
        result = session.run_ps(ps_script)
        
        if result.status_code == 0:
            task.progress = 100
            task.complete_success({
                'installed': True,
                'cert_filename': cert_filename,
                'output': result.std_out.decode('utf-8') if result.std_out else ''
            })
            
            return {
                'success': True,
                'installed': True
            }
        else:
            error_msg = result.std_err.decode('utf-8') if result.std_err else 'Unknown error'
            task.complete_failure(f"Certificate installation failed: {error_msg}")
            
            return {
                'success': False,
                'installed': False,
                'error': error_msg
            }
        
    except Exception as e:
        logger.error(f"安装证书失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
        
        return {
            'success': False,
            'error': str(e)
        }