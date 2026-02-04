from django.db import models
from apps.hosts.models import Host
from apps.operations.models import AccountOpeningRequest, CloudComputerUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class AuditLog(models.Model):
    """审计日志模型"""
    ACTION_CHOICES = [
        ('create_user', '创建用户'),
        ('delete_user', '删除用户'),
        ('reset_password', '重置密码'),
        ('connect_host', '连接主机'),
        ('modify_host', '修改主机'),
        ('view_password', '查看密码'),
        ('approve_request', '审批请求'),
        ('reject_request', '拒绝请求'),
        ('bootstrap_host', '初始化主机'),
        ('issue_cert', '签发证书'),
        ('revoke_cert', '吊销证书'),
        ('create_host', '创建主机'),
        ('delete_host', '删除主机'),
        ('update_host', '更新主机'),
        ('process_opening_request', '处理开户请求'),
        ('batch_process_requests', '批量处理请求'),
        ('login', '用户登录'),
        ('logout', '用户登出'),
        ('view_audit_log', '查看审计日志'),
        ('admin_action', '管理员操作'),
    ]

    user = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="操作用户"
    )
    host = models.ForeignKey(
        Host, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="操作主机"
    )
    action = models.CharField(
        max_length=50, 
        choices=ACTION_CHOICES,
        verbose_name="操作类型"
    )
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name="操作IP地址"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")
    success = models.BooleanField(default=True, verbose_name="操作成功")
    details = models.JSONField(default=dict, verbose_name="操作详情")  # 存储具体操作详情
    result = models.TextField(null=True, blank=True, verbose_name="操作结果")
    
    # 通用外键，用于关联各种模型
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="关联对象类型"
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="关联对象ID"
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "审计日志"
        verbose_name_plural = "审计日志"
        db_table = "audit_log"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['host', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        host_str = f" on {self.host.hostname}" if self.host else ""
        return f"[{self.timestamp}] {user_str}{host_str} - {self.action}"


class SensitiveOperation(models.Model):
    """敏感操作记录"""
    operation_type = models.CharField(max_length=50, verbose_name="操作类型")
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, verbose_name="操作用户")
    target = models.CharField(max_length=255, verbose_name="操作目标")  # 目标对象描述
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")
    ip_address = models.GenericIPAddressField(verbose_name="操作IP")
    justification = models.TextField(verbose_name="操作理由")  # 必须提供操作理由
    approved_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='approved_sensitive_ops',
        verbose_name="批准人"
    )
    approved_at = models.DateTimeField(null=True, verbose_name="批准时间")
    result = models.TextField(null=True, blank=True, verbose_name="操作结果")
    
    class Meta:
        verbose_name = "敏感操作"
        verbose_name_plural = "敏感操作"
        db_table = "sensitive_operation"
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.user.username} - {self.operation_type} on {self.target}"


class SecurityEvent(models.Model):
    """安全事件模型"""
    SEVERITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    ]
    
    EVENT_TYPE_CHOICES = [
        ('unauthorized_access', '未授权访问'),
        ('failed_login', '登录失败'),
        ('suspicious_activity', '可疑活动'),
        ('data_exposure', '数据暴露风险'),
        ('privilege_escalation', '权限提升尝试'),
        ('cert_compromise', '证书泄露'),
        ('brute_force', '暴力破解'),
    ]

    event_type = models.CharField(
        max_length=50, 
        choices=EVENT_TYPE_CHOICES,
        verbose_name="事件类型"
    )
    severity = models.CharField(
        max_length=10, 
        choices=SEVERITY_CHOICES, 
        default='medium',
        verbose_name="严重程度"
    )
    user = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="关联用户"
    )
    ip_address = models.GenericIPAddressField(verbose_name="事件IP")
    description = models.TextField(verbose_name="事件描述")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="发生时间")
    resolved = models.BooleanField(default=False, verbose_name="已解决")
    resolved_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='resolved_security_events',
        verbose_name="解决人"
    )
    resolved_at = models.DateTimeField(null=True, verbose_name="解决时间")
    resolution_notes = models.TextField(null=True, blank=True, verbose_name="解决备注")

    class Meta:
        verbose_name = "安全事件"
        verbose_name_plural = "安全事件"
        db_table = "security_event"
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.event_type} - {self.timestamp}"


class SessionActivity(models.Model):
    """会话活动记录"""
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, verbose_name="用户")
    session_key = models.CharField(max_length=40, verbose_name="会话密钥")
    ip_address = models.GenericIPAddressField(verbose_name="IP地址")
    user_agent = models.TextField(verbose_name="用户代理")
    login_time = models.DateTimeField(auto_now_add=True, verbose_name="登录时间")
    logout_time = models.DateTimeField(null=True, blank=True, verbose_name="登出时间")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")

    class Meta:
        verbose_name = "会话活动"
        verbose_name_plural = "会话活动"
        db_table = "session_activity"
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.username} - {self.session_key[:8]} - {self.login_time}"