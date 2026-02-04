from celery import shared_task
from django.contrib.auth.models import User
from apps.operations.models import AccountOpeningRequest, CloudComputerUser
from apps.hosts.models import Host
from apps.tasks.models import AsyncTask
from apps.certificates.models import ClientCertificate
import logging
import winrm
import random
import string

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_opening_request(self, request_id, operator_id):
    """异步处理开户请求"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"处理开户请求 #{request_id}",
        created_by_id=operator_id,
        target_object_id=request_id,
        target_content_type='operations.AccountOpeningRequest',
        status='running'
    )
    
    try:
        request_obj = AccountOpeningRequest.objects.get(id=request_id)
        task.start_execution()
        
        # 更新进度
        task.progress = 10
        task.save()
        
        # 记录进度
        from apps.tasks.models import TaskProgress
        TaskProgress.objects.create(
            task=task,
            progress=10,
            message="开始处理开户请求"
        )
        
        # 选择合适的主机
        available_host = Host.objects.filter(
            is_active=True,
            init_status='ready'  # 确保主机已准备好
        ).first()
        
        if not available_host:
            raise Exception("没有可用的主机资源")
        
        task.progress = 30
        task.save()
        
        TaskProgress.objects.create(
            task=task,
            progress=30,
            message="找到可用主机"
        )
        
        # 创建Windows用户
        from utils.winrm_client import SecureWinRMClient
        
        # 生成用户名和密码
        username = request_obj.username
        password = request_obj.generate_temp_password()  # 使用模型方法生成密码
        
        # 使用WinRM创建用户
        ps_command = f"""
        $securePassword = ConvertTo-SecureString "{password}" -AsPlainText -Force
        $userExists = Get-LocalUser -Name "{username}" -ErrorAction SilentlyContinue
        if ($userExists) {{
            Write-Output "User {username} already exists, updating password..."
            Set-LocalUser -Name "{username}" -Password $securePassword
        }} else {{
            New-LocalUser -Name "{username}" -Password $securePassword -FullName "{getattr(request_obj, 'full_name', username)}" -Description "Cloud computer user"
            Add-LocalGroupMember -Group "Remote Desktop Users" -Member "{username}"
        }}
        Write-Output "User {username} created/updated successfully"
        """
        
        task.progress = 50
        task.save()
        
        TaskProgress.objects.create(
            task=task,
            progress=50,
            message="执行PowerShell命令创建用户"
        )
        
        # 连接到主机并执行命令
        client = SecureWinRMClient(available_host)
        session = client.connect_with_certificate()
        result = session.run_ps(ps_command)
        
        if result.status_code != 0:
            error_msg = result.std_err.decode('utf-8') if result.std_err else 'Unknown error'
            raise Exception(f"创建用户失败: {error_msg}")
        
        task.progress = 70
        task.save()
        
        TaskProgress.objects.create(
            task=task,
            progress=70,
            message="用户创建成功"
        )
        
        # 关联用户到主机
        request_obj.host = available_host
        request_obj.windows_username = username
        request_obj.windows_password = password  # 应该加密存储
        request_obj.status = 'approved'
        request_obj.save()
        
        # 创建CloudComputerUser记录
        cloud_user, created = CloudComputerUser.objects.get_or_create(
            account_opening_request=request_obj,
            defaults={
                'windows_username': username,
                'host': available_host,
                'status': 'active'
            }
        )
        if not created:
            cloud_user.windows_username = username
            cloud_user.host = available_host
            cloud_user.status = 'active'
            cloud_user.save()
        
        task.progress = 90
        task.save()
        
        TaskProgress.objects.create(
            task=task,
            progress=90,
            message="更新请求状态"
        )
        
        task.progress = 100
        task.complete_success({
            'host': available_host.hostname,
            'username': username,
            'success': True,
            'cloud_user_id': cloud_user.id
        })
        
        TaskProgress.objects.create(
            task=task,
            progress=100,
            message="开户请求处理完成"
        )
        
        return {
            'success': True,
            'host': available_host.hostname,
            'username': username,
            'cloud_user_id': cloud_user.id
        }
        
    except Exception as e:
        logger.error(f"处理开户请求失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
        
        # 如果部分操作已完成，可能需要回滚
        try:
            rollback_opening_request(request_id)
        except Exception as rollback_error:
            logger.error(f"回滚开户请求失败: {str(rollback_error)}", exc_info=True)
        
        return {
            'success': False,
            'error': str(e)
        }


def rollback_opening_request(request_id):
    """回滚已执行的操作"""
    try:
        request_obj = AccountOpeningRequest.objects.get(id=request_id)
        if request_obj.host and request_obj.windows_username:
            # 通过WinRM删除已创建的用户
            from utils.winrm_client import SecureWinRMClient
            client = SecureWinRMClient(request_obj.host)
            
            ps_command = f'Disable-LocalUser -Name "{request_obj.windows_username}" -ErrorAction SilentlyContinue'
            result = client.connect_with_certificate().run_ps(ps_command)
            
            if result.status_code == 0:
                logger.info(f"已禁用用户 {request_obj.windows_username}")
            else:
                logger.warning(f"禁用用户失败: {result.std_err.decode('utf-8')}")
        
        # 重置请求状态
        request_obj.status = 'pending'
        request_obj.save()
        
    except Exception as e:
        logger.error(f"回滚操作失败: {str(e)}")


@shared_task(bind=True)
def reset_user_password(self, user_id, operator_id):
    """异步重置用户密码"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"重置用户密码 - 用户 #{user_id}",
        created_by_id=operator_id,
        target_object_id=user_id,
        target_content_type='operations.CloudComputerUser',
        status='running'
    )
    
    try:
        user = CloudComputerUser.objects.get(id=user_id)
        task.start_execution()
        
        # 生成新密码
        new_password = generate_secure_password()
        
        # 通过WinRM重置密码
        from utils.winrm_client import SecureWinRMClient
        client = SecureWinRMClient(user.host)
        
        ps_command = f"""
        $securePassword = ConvertTo-SecureString "{new_password}" -AsPlainText -Force
        Set-LocalUser -Name "{user.windows_username}" -Password $securePassword
        Write-Output "Password reset for user {user.windows_username}"
        """
        
        result = client.connect_with_certificate().run_ps(ps_command)
        
        if result.status_code != 0:
            error_msg = result.std_err.decode('utf-8') if result.std_err else 'Unknown error'
            raise Exception(f"重置密码失败: {error_msg}")
        
        # 更新数据库中的密码（应该加密存储）
        user.account_opening_request.windows_password = new_password
        user.account_opening_request.save()
        
        task.progress = 100
        task.complete_success({
            'success': True,
            'message': '密码重置成功',
            'username': user.windows_username
        })
        
        return {
            'success': True,
            'message': '密码重置成功',
            'username': user.windows_username
        }
        
    except Exception as e:
        logger.error(f"重置密码失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
        
        return {
            'success': False,
            'error': str(e)
        }


def generate_secure_password(length=12):
    """生成安全密码"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(characters) for i in range(length))
    return password


@shared_task(bind=True)
def batch_process_opening_requests(self, request_ids, operator_id):
    """批量处理开户请求"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"批量处理开户请求 ({len(request_ids)}个)",
        created_by_id=operator_id,
        status='running'
    )
    
    try:
        task.start_execution()
        
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        total_requests = len(request_ids)
        
        for idx, request_id in enumerate(request_ids):
            try:
                # 更新进度
                progress = int((idx / total_requests) * 80) + 10  # 10% 到 90%
                task.progress = progress
                task.save()
                
                # 处理单个请求
                result = process_opening_request.delay(request_id, operator_id).get()
                
                results['processed'] += 1
                if result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'request_id': request_id,
                        'error': result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'request_id': request_id,
                    'error': str(e)
                })
        
        task.progress = 100
        task.complete_success(results)
        
        return results
        
    except Exception as e:
        logger.error(f"批量处理开户请求失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
        
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(bind=True)
def cleanup_inactive_users(self, days_inactive=30):
    """清理非活跃用户"""
    task = AsyncTask.objects.create(
        task_id=self.request.id,
        name=f"清理非活跃用户 (超过{days_inactive}天未使用)",
        status='running'
    )
    
    try:
        task.start_execution()
        
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days_inactive)
        
        inactive_users = CloudComputerUser.objects.filter(
            last_login__lt=cutoff_date,
            status='active'
        )
        
        cleaned_count = 0
        for user in inactive_users:
            # 禁用用户账户
            from utils.winrm_client import SecureWinRMClient
            client = SecureWinRMClient(user.host)
            
            ps_command = f'Disable-LocalUser -Name "{user.windows_username}"'
            result = client.connect_with_certificate().run_ps(ps_command)
            
            if result.status_code == 0:
                user.status = 'disabled'
                user.save()
                cleaned_count += 1
            else:
                logger.warning(f"无法禁用用户 {user.windows_username}: {result.std_err.decode('utf-8')}")
        
        task.progress = 100
        task.complete_success({
            'cleaned_users': cleaned_count,
            'total_inactive': inactive_users.count()
        })
        
        return {
            'success': True,
            'cleaned_users': cleaned_count,
            'total_inactive': inactive_users.count()
        }
        
    except Exception as e:
        logger.error(f"清理非活跃用户失败: {str(e)}", exc_info=True)
        task.complete_failure(str(e))
        
        return {
            'success': False,
            'error': str(e)
        }