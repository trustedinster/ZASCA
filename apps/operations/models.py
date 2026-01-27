"""
操作记录模型
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class PublicHostInfo(models.Model):
    """
    公开主机信息模型

    用于在前端展示主机信息，而不暴露敏感信息
    """
    # 内部主机关联
    internal_host = models.OneToOneField(
        'hosts.Host',
        on_delete=models.CASCADE,
        verbose_name=_('内部主机'),
        help_text=_('关联的内部主机')
    )
    
    # 显示信息
    display_name = models.CharField(
        max_length=200,
        verbose_name=_('显示名称'),
        help_text=_('在前端展示的主机名称')
    )
    display_description = models.TextField(
        blank=True,
        verbose_name=_('显示描述'),
        help_text=_('在前端展示的主机描述，支持Markdown格式')
    )
    
    # 连接信息（对外公开的部分）
    display_hostname = models.CharField(
        max_length=255,
        verbose_name=_('显示地址'),
        help_text=_('在前端展示的主机地址')
    )
    display_rdp_port = models.IntegerField(
        default=3389,
        verbose_name=_('显示RDP端口'),
        help_text=_('在前端展示的RDP端口')
    )
    
    # 可用性
    is_available = models.BooleanField(
        default=True,
        verbose_name=_('是否可用'),
        help_text=_('是否在前端展示此主机')
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间')
    )

    class Meta:
        verbose_name = _('公开主机信息')
        verbose_name_plural = _('公开主机信息')
        indexes = [
            models.Index(fields=['is_available']),
            models.Index(fields=['internal_host']),
        ]

    def __str__(self):
        return self.display_name


class SystemTask(models.Model):
    """
    系统任务模型

    记录系统中的异步任务，如批量操作、定时任务等
    """
    # 任务信息
    name = models.CharField(
        max_length=200,
        verbose_name=_('任务名称'),
        help_text=_('任务的名称')
    )
    task_type = models.CharField(
        max_length=100,
        verbose_name=_('任务类型'),
        help_text=_('任务的类型，如batch_create_user等')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('任务描述'),
        help_text=_('任务的详细描述')
    )

    # 执行信息
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', _('等待中')),
            ('running', _('执行中')),
            ('success', _('成功')),
            ('failed', _('失败')),
            ('cancelled', _('已取消')),
        ],
        default='pending',
        verbose_name=_('任务状态'),
        help_text=_('任务的执行状态')
    )
    progress = models.IntegerField(
        default=0,
        verbose_name=_('执行进度'),
        help_text=_('任务执行进度，0-100')
    )
    result = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('执行结果'),
        help_text=_('任务执行的结果信息')
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('错误信息'),
        help_text=_('任务执行失败时的错误信息')
    )

    # 关联信息
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks',
        verbose_name=_('创建者'),
        help_text=_('创建该任务的用户')
    )

    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间'),
        help_text=_('任务创建时间')
    )
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('开始时间'),
        help_text=_('任务开始执行的时间')
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('完成时间'),
        help_text=_('任务完成的时间')
    )

    class Meta:
        verbose_name = _('系统任务')
        verbose_name_plural = _('系统任务')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['task_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        """返回任务名称"""
        return self.name

    def update_progress(self, progress):
        """
        更新任务进度

        Args:
            progress: 进度值，0-100
        """
        self.progress = min(max(progress, 0), 100)
        self.save(update_fields=['progress'])

    def start(self):
        """开始执行任务"""
        from django.utils import timezone
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def complete(self, result=None):
        """
        完成任务

        Args:
            result: 执行结果
        """
        from django.utils import timezone
        self.status = 'success'
        self.completed_at = timezone.now()
        self.progress = 100
        if result:
            self.result = result
        self.save(update_fields=['status', 'completed_at', 'progress', 'result'])

    def fail(self, error_message):
        """
        任务失败

        Args:
            error_message: 错误信息
        """
        from django.utils import timezone
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])

    def cancel(self):
        """取消任务"""
        from django.utils import timezone
        self.status = 'cancelled'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])


class Product(models.Model):
    """
    产品模型

    代表面向用户的产品，一个主机可以对应多个产品
    """
    # 产品基本信息
    name = models.CharField(
        max_length=200,
        verbose_name=_('产品名称'),
        help_text=_('面向用户展示的产品名称')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('产品描述'),
        help_text=_('产品的详细描述，支持Markdown格式')
    )
    display_name = models.CharField(
        max_length=200,
        verbose_name=_('显示名称'),
        help_text=_('在前端展示的产品名称')
    )
    display_description = models.TextField(
        blank=True,
        verbose_name=_('显示描述'),
        help_text=_('在前端展示的产品描述，支持Markdown格式')
    )
    
    # 关联主机
    host = models.ForeignKey(
        'hosts.Host',
        on_delete=models.CASCADE,
        verbose_name=_('关联主机'),
        help_text=_('此产品运行所在的主机')
    )
    
    # 产品配置
    rdp_port = models.IntegerField(
        default=3389,
        verbose_name=_('RDP端口'),
        help_text=_('用户连接时使用的RDP端口')
    )
    display_hostname = models.CharField(
        max_length=255,
        verbose_name=_('显示地址'),
        help_text=_('在前端展示的产品访问地址')
    )
    
    # 产品状态
    is_available = models.BooleanField(
        default=True,
        verbose_name=_('是否可用'),
        help_text=_('是否在前端展示此产品')
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间')
    )

    class Meta:
        verbose_name = _('产品')
        verbose_name_plural = _('产品')
        indexes = [
            models.Index(fields=['is_available']),
            models.Index(fields=['host']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.display_name

    @property
    def status(self):
        """
        产品状态，继承自主机状态
        """
        return self.host.status

    @property
    def hostname(self):
        """
        产品主机名，使用显示地址
        """
        return self.display_hostname


class AccountOpeningRequest(models.Model):
    """
    用户开户申请模型

    用于记录用户提交的开户申请信息
    """
    # 申请人信息
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='account_opening_requests',
        verbose_name=_('申请人'),
        help_text=_('提交开户申请的用户')
    )
    contact_email = models.EmailField(
        verbose_name=_('联系邮箱'),
        help_text=_('申请人联系方式')
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('联系电话'),
        help_text=_('申请人联系电话')
    )

    # 开户信息
    username = models.CharField(
        max_length=150,
        verbose_name=_('用户名'),
        help_text=_('希望在云电脑上创建的用户名')
    )
    user_fullname = models.CharField(
        max_length=200,
        verbose_name=_('用户姓名'),
        help_text=_('用户真实姓名')
    )
    user_email = models.EmailField(
        verbose_name=_('用户邮箱'),
        help_text=_('用户邮箱地址')
    )
    user_description = models.TextField(
        blank=True,
        verbose_name=_('用户描述'),
        help_text=_('关于该用户的附加信息')
    )

    # 用户指定的密码（可选）
    requested_password = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name=_('用户指定密码'),
        help_text=_('用户希望设置的初始密码，留空则系统生成')
    )

    # 目标产品（替代原来的target_host）
    target_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name=_('目标产品'),
        help_text=_('要在哪个产品上创建用户'),
        null=True,
        blank=True
    )

    # 审核信息
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', _('待审核')),
            ('approved', _('已批准')),
            ('rejected', _('已拒绝')),
            ('processing', _('处理中')),
            ('completed', _('已完成')),
            ('failed', _('失败')),
        ],
        default='pending',
        verbose_name=_('申请状态'),
        help_text=_('开户申请的当前状态')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_account_requests',
        verbose_name=_('审核人'),
        help_text=_('批准此申请的管理员')
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('审核时间'),
        help_text=_('申请被审核的时间')
    )
    approval_notes = models.TextField(
        blank=True,
        verbose_name=_('审核备注'),
        help_text=_('审核时的备注信息')
    )

    # 结果信息
    cloud_user_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('云电脑用户ID'),
        help_text=_('在云电脑上实际创建的用户ID')
    )
    cloud_user_password = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('云电脑用户密码'),
        help_text=_('为用户设置的初始密码')
    )
    result_message = models.TextField(
        blank=True,
        verbose_name=_('结果信息'),
        help_text=_('开户操作的结果信息')
    )

    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间'),
        help_text=_('申请创建时间')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间'),
        help_text=_('申请信息最后更新时间')
    )

    class Meta:
        verbose_name = _('开户申请')
        verbose_name_plural = _('开户申请')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['applicant']),
            models.Index(fields=['status']),
            models.Index(fields=['target_product']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.username} - {self.target_product.display_name}'

    def approve(self, approver, notes=''):
        """
        批准开户申请

        Args:
            approver: 批准申请的管理员
            notes: 审核备注
        """
        self.status = 'approved'
        self.approved_by = approver
        self.approval_date = timezone.now()
        self.approval_notes = notes
        # 不直接调用save，而是通过super().save()让重写的save方法处理后续操作
        super().save()

    def reject(self, approver, notes=''):
        """
        拒绝开户申请

        Args:
            approver: 拒绝申请的管理员
            notes: 审核备注
        """
        self.status = 'rejected'
        self.approved_by = approver
        self.approval_date = timezone.now()
        self.approval_notes = notes
        self.save()

    def start_processing(self):
        """
        开始处理开户申请
        """
        self.status = 'processing'
        self.save()

    def complete(self, cloud_user_id, cloud_user_password, result_message=''):
        """
        完成开户申请

        Args:
            cloud_user_id: 在云电脑上创建的用户ID
            cloud_user_password: 用户初始密码（出于安全考虑，不会存储）
            result_message: 结果信息
        """
        self.status = 'completed'
        self.cloud_user_id = cloud_user_id
        # 出于安全考虑，不存储用户密码明文
        # self.cloud_user_password = cloud_user_password
        self.result_message = result_message
        self.save()

    def fail(self, result_message=''):
        """
        开户申请失败

        Args:
            result_message: 失败原因
        """
        self.status = 'failed'
        self.result_message = result_message
        self.save()

    def save(self, *args, **kwargs):
        """
        重写save方法，当状态变为'approved'时自动处理用户创建
        """
        # 检查是否是状态从'pending'变更为'approved'
        old_instance = None
        if self.pk:  # 如果是更新操作
            try:
                old_instance = AccountOpeningRequest.objects.get(pk=self.pk)
            except AccountOpeningRequest.DoesNotExist:
                pass

        # 调用父类的save方法保存数据
        super().save(*args, **kwargs)

        # 如果状态从'pending'变更为'approved'，则自动处理用户创建
        # 仅当 old_instance 存在且状态发生变化时才执行
        if (old_instance and 
            old_instance.status == 'pending' and 
            self.status == 'approved'):
            self.auto_process_creation()

    def auto_process_creation(self):
        """
        自动处理用户创建
        当申请被批准时调用此方法
        """
        try:
            from utils.winrm_client import WinrmClient
            import secrets
            import string
            import os
            
            # 连接到产品关联的主机
            product = self.target_product
            host = product.host
            
            # 如果是DEMO模式，不执行实际的WinRM操作
            if os.environ.get('ZASCA_DEMO', '').lower() == '1':
                # 在DEMO模式下模拟创建用户
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'DEMO模式: 模拟创建用户 {self.username} 在产品 {product.display_name}')
                
                # 使用用户指定的密码，如果没有指定则生成简单密码
                if self.requested_password:
                    password = self.requested_password
                else:
                    password = 'DemoPass123!'  # 在DEMO模式下使用简单密码
                
                # 模拟成功创建用户
                self.status = 'completed'
                self.result_message = f"用户 {self.username} 已在DEMO模式下成功创建（模拟）"
                self.save(update_fields=['status', 'result_message'])
                
                # 创建云电脑用户记录
                cloud_user, created = CloudComputerUser.objects.get_or_create(
                    username=self.username,
                    product=self.target_product,
                    defaults={
                        'fullname': self.user_fullname,
                        'email': self.user_email,
                        'description': self.user_description,
                        'created_from_request': self
                    }
                )
                
                return
            
            # 非DEMO模式下正常执行
            client = WinrmClient(
                hostname=host.hostname,
                port=host.port,
                username=host.username,
                password=host.password,
                use_ssl=host.use_ssl
            )
            
            # 使用用户指定的密码，如果没有指定则生成符合密码策略的随机密码
            if self.requested_password:
                password = self.requested_password
            else:
                # 使用WinRM客户端生成符合密码策略的强密码
                password = client.generate_strong_password()
            
            # 创建用户命令 (PowerShell)
            create_user_cmd = f'''
            $Password = ConvertTo-SecureString "{password}" -AsPlainText -Force
            New-LocalUser -Name "{self.username}" -Password $Password -FullName "{self.user_fullname}" -Description "{self.user_description}"
            Add-LocalGroupMember -Group "Users" -Member "{self.username}"
            '''
            
            result = client.execute_powershell(create_user_cmd)
            
            if result.status_code == 0:
                # 成功创建用户
                self.status = 'completed'
                # 出于安全考虑，不存储用户密码明文
                self.result_message = f"用户 {self.username} 已成功创建"
                self.save(update_fields=['status', 'result_message'])
                
                # 创建云电脑用户记录
                cloud_user, created = CloudComputerUser.objects.get_or_create(
                    username=self.username,
                    product=self.target_product,  # 修改为关联产品
                    defaults={
                        'fullname': self.user_fullname,
                        'email': self.user_email,
                        'description': self.user_description,
                        'created_from_request': self
                    }
                )
            else:
                # 创建用户失败
                error_msg = result.std_err if result.std_err else '未知错误'
                self.status = 'failed'
                self.result_message = f"创建用户失败: {error_msg}"
                self.save(update_fields=['status', 'result_message'])
        except Exception as e:
            # 处理异常
            error_msg = str(e)
            self.status = 'failed'
            self.result_message = f"处理过程中出现异常: {error_msg}"
            self.save(update_fields=['status', 'result_message'])


class CloudComputerUser(models.Model):
    """
    云电脑用户模型

    记录在各个云电脑产品上创建的用户信息
    """
    # 用户信息
    username = models.CharField(
        max_length=150,
        verbose_name=_('用户名'),
        help_text=_('在云电脑上的用户名')
    )
    fullname = models.CharField(
        max_length=200,
        verbose_name=_('用户姓名'),
        help_text=_('用户真实姓名')
    )
    email = models.EmailField(
        verbose_name=_('用户邮箱'),
        help_text=_('用户邮箱地址')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('用户描述'),
        help_text=_('关于该用户的附加信息')
    )

    # 关联的产品（替代原来的host）
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name=_('所属产品'),
        help_text=_('该用户所属的云电脑产品')
    )

    # 状态信息
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', _('激活')),
            ('inactive', _('未激活')),
            ('disabled', _('已禁用')),
            ('deleted', _('已删除')),
        ],
        default='active',
        verbose_name=_('用户状态'),
        help_text=_('用户在云电脑上的状态')
    )

    # 权限信息
    is_admin = models.BooleanField(
        default=False,
        verbose_name=_('管理员权限'),
        help_text=_('是否具有管理员权限')
    )
    groups = models.TextField(
        blank=True,
        verbose_name=_('用户组'),
        help_text=_('用户所属的组（逗号分隔）')
    )

    # 创建信息
    created_from_request = models.ForeignKey(
        AccountOpeningRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('来源申请'),
        help_text=_('创建此用户的开户申请')
    )

    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间'),
        help_text=_('用户在云电脑上创建的时间')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间'),
        help_text=_('信息最后更新时间')
    )

    class Meta:
        verbose_name = _('云电脑用户')
        verbose_name_plural = _('云电脑用户')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['username']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        unique_together = [['product', 'username']]  # 确保同一产品上用户名唯一

    def __str__(self):
        return f'{self.username}@{self.product.display_name}'

    def activate(self):
        """
        激活用户
        """
        self.status = 'active'
        self.save(update_fields=['status', 'updated_at'])

    def deactivate(self):
        """
        禁用用户
        """
        self.status = 'inactive'
        self.save(update_fields=['status', 'updated_at'])

    def disable(self):
        """
        删除用户
        """
        self.status = 'disabled'
        self.save(update_fields=['status', 'updated_at'])

    def delete_user(self):
        """
        标记用户为已删除
        """
        self.status = 'deleted'
        self.save(update_fields=['status', 'updated_at'])

    def save(self, *args, **kwargs):
        """
        重写save方法，当状态改变时自动执行相应操作
        """
        # 检查是否是更新操作
        old_instance = None
        if self.pk:
            try:
                old_instance = CloudComputerUser.objects.get(pk=self.pk)
            except CloudComputerUser.DoesNotExist:
                pass

        # 调用父类的save方法保存数据
        super().save(*args, **kwargs)

        # 如果是状态更新，执行相应操作
        if old_instance:
            # 如果状态变为'disabled'（已禁用），则禁用用户
            if old_instance.status != 'disabled' and self.status == 'disabled':
                self.disable_remote_user()
            # 如果状态变为'active'（已激活）且之前是'disabled'，则启用用户
            elif old_instance.status == 'disabled' and self.status == 'active':
                self.enable_remote_user()
            # 如果状态变为'deleted'（已删除），则删除远程用户
            elif old_instance.status != 'deleted' and self.status == 'deleted':
                self.delete_remote_user()

    def disable_remote_user(self):
        """
        在远程主机上禁用用户
        """
        import os
        if os.environ.get('ZASCA_DEMO', '').lower() == '1':
            # 在DEMO模式下，不执行实际操作
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'DEMO模式: 模拟禁用用户 {self.username} 在产品 {self.product.display_name}')
            return
        
        try:
            from utils.winrm_client import WinrmClient
            
            # 连接到产品关联的主机
            product = self.product
            host = product.host
            client = WinrmClient(
                hostname=host.hostname,
                port=host.port,
                username=host.username,
                password=host.password,
                use_ssl=host.use_ssl
            )
            
            # 禁用用户的PowerShell命令
            disable_user_cmd = f'''
            Disable-LocalUser -Name "{self.username}"
            Write-Output "User {self.username} disabled successfully"
            '''
            
            result = client.execute_powershell(disable_user_cmd)
            if result.status_code != 0:
                error_msg = result.std_err if result.std_err else 'Unknown error'
                print(f"Failed to disable user {self.username} on host {host.name}: {error_msg}")
        except Exception as e:
            print(f"Error disabling user {self.username} on host {host.name}: {str(e)}")

    def enable_remote_user(self):
        """
        在远程主机上启用用户
        """
        import os
        if os.environ.get('ZASCA_DEMO', '').lower() == '1':
            # 在DEMO模式下，不执行实际操作
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'DEMO模式: 模拟启用用户 {self.username} 在产品 {self.product.display_name}')
            return
        
        try:
            from utils.winrm_client import WinrmClient
            
            # 连接到产品关联的主机
            product = self.product
            host = product.host
            client = WinrmClient(
                hostname=host.hostname,
                port=host.port,
                username=host.username,
                password=host.password,
                use_ssl=host.use_ssl
            )
            
            # 启用用户的PowerShell命令
            enable_user_cmd = f'''
            Enable-LocalUser -Name "{self.username}"
            Write-Output "User {self.username} enabled successfully"
            '''
            
            result = client.execute_powershell(enable_user_cmd)
            if result.status_code != 0:
                error_msg = result.std_err if result.std_err else 'Unknown error'
                print(f"Failed to enable user {self.username} on host {host.name}: {error_msg}")
        except Exception as e:
            print(f"Error enabling user {self.username} on host {host.name}: {str(e)}")

    def delete_remote_user(self):
        """
        在远程主机上删除用户
        """
        import os
        if os.environ.get('ZASCA_DEMO', '').lower() == '1':
            # 在DEMO模式下，不执行实际操作
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'DEMO模式: 模拟删除用户 {self.username} 在产品 {self.product.display_name}')
            return
        
        try:
            from utils.winrm_client import WinrmClient
            
            # 连接到产品关联的主机
            product = self.product
            host = product.host
            client = WinrmClient(
                hostname=host.hostname,
                port=host.port,
                username=host.username,
                password=host.password,
                use_ssl=host.use_ssl
            )
            
            # 删除用户的PowerShell命令
            delete_user_cmd = f'''
            Remove-LocalUser -Name "{self.username}"
            Write-Output "User {self.username} deleted successfully"
            '''
            
            result = client.execute_powershell(delete_user_cmd)
            if result.status_code != 0:
                error_msg = result.std_err if result.std_err else 'Unknown error'
                print(f"Failed to delete user {self.username} on host {host.name}: {error_msg}")
        except Exception as e:
            print(f"Error deleting user {self.username} on host {host.name}: {str(e)}")