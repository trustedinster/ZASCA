"""
增强版的仪表板模型
添加更多统计和配置功能
"""
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from datetime import timedelta


class SystemStatsEnhanced(models.Model):
    """扩展的系统统计信息"""

    # 系统负载指标
    cpu_usage = models.FloatField(default=0.0, verbose_name='CPU使用率')
    memory_usage = models.FloatField(default=0.0, verbose_name='内存使用率')
    disk_usage = models.FloatField(default=0.0, verbose_name='磁盘使用率')

    # 网络指标
    network_in = models.BigIntegerField(default=0, verbose_name='网络入流量')
    network_out = models.BigIntegerField(default=0, verbose_name='网络出流量')

    # 用户活动指标
    active_sessions = models.IntegerField(default=0, verbose_name='活跃会话数')
    total_requests = models.IntegerField(default=0, verbose_name='总请求数')
    failed_requests = models.IntegerField(default=0, verbose_name='失败请求数')

    # 性能指标
    avg_response_time = models.FloatField(default=0.0, verbose_name='平均响应时间(ms)')
    p50_response_time = models.FloatField(default=0.0, verbose_name='50分位响应时间')
    p95_response_time = models.FloatField(default=0.0, verbose_name='95分位响应时间')
    p99_response_time = models.FloatField(default=0.0, verbose_name='99分位响应时间')

    # 存储指标
    storage_used = models.BigIntegerField(default=0, verbose_name='已用存储')
    storage_limit = models.BigIntegerField(default=0, verbose_name='存储限制')

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间戳')

    class Meta:
        verbose_name = '系统统计(增强)'
        verbose_name_plural = '系统统计(增强)'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"系统统计 - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    @property
    def network_utilization(self):
        """网络利用率"""
        # 这里可以添加更复杂的网络利用率计算逻辑
        return min(100.0, (self.network_in + self.network_out) / 1024 / 1024)  # MB估算

    @property
    def storage_utilization(self):
        """存储利用率百分比"""
        if self.storage_limit > 0:
            return (self.storage_used / self.storage_limit) * 100
        return 0.0

    @property
    def success_rate(self):
        """请求成功率"""
        if self.total_requests > 0:
            return ((self.total_requests - self.failed_requests) / self.total_requests) * 100
        return 100.0


class DashboardWidgetEnhanced(models.Model):
    """增强版仪表板部件"""

    WIDGET_TYPES = [
        ('line-chart', '折线图'),
        ('bar-chart', '柱状图'),
        ('pie-chart', '饼图'),
        ('gauge', '仪表盘'),
        ('stat', '统计卡片'),
        ('table', '表格'),
        ('progress', '进度条'),
    ]

    STATUS_CHOICES = [
        ('active', '活跃'),
        ('inactive', '不活跃'),
        ('hidden', '隐藏'),
    ]

    name = models.CharField(max_length=100, verbose_name='部件名称')
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES, verbose_name='部件类型')
    description = models.TextField(blank=True, verbose_name='描述')

    # 数据源配置
    data_source = models.CharField(max_length=100, verbose_name='数据源')
    data_query = models.TextField(default='', verbose_name='数据查询')
    refresh_interval = models.IntegerField(default=30, verbose_name='刷新间隔(秒)')

    # 可视化配置
    position = models.IntegerField(default=0, verbose_name='位置')
    size_x = models.IntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(12)], verbose_name='宽度')
    size_y = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(10)], verbose_name='高度')

    # 显示配置
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    is_public = models.BooleanField(default=True, verbose_name='是否公开')
    show_title = models.BooleanField(default=True, verbose_name='显示标题')
    show_legend = models.BooleanField(default=True, verbose_name='显示图例')

    # 样式配置
    color_scheme = models.TextField(default='{}', verbose_name='配色方案')
    custom_css = models.TextField(blank=True, verbose_name='自定义CSS')

    # 权限配置
    allowed_roles = models.JSONField(default=list, blank=True, verbose_name='允许的角色')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '仪表板部件(增强)'
        verbose_name_plural = '仪表板部件(增强)'
        ordering = ['position', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_widget_type_display()})"


class UserActivityEnhanced(models.Model):
    """增强版用户活动记录"""

    ACTION_TYPES = [
        ('login', '登录'),
        ('logout', '登出'),
        ('view', '查看'),
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('export', '导出'),
        ('import', '导入'),
        ('approve', '审批'),
        ('reject', '拒绝'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, verbose_name='用户')
    action = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name='操作类型')

    # 资源信息
    resource_type = models.CharField(max_length=50, verbose_name='资源类型')
    resource_id = models.CharField(max_length=100, blank=True, verbose_name='资源ID')
    resource_name = models.CharField(max_length=200, blank=True, verbose_name='资源名称')

    # 详细数据
    changes = models.JSONField(default=dict, blank=True, verbose_name='变更数据')
    old_values = models.JSONField(default=dict, blank=True, verbose_name='旧值')
    new_values = models.JSONField(default=dict, blank=True, verbose_name='新值')

    # 上下文信息
    client_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='客户端IP')
    user_agent = models.TextField(blank=True, verbose_name='用户代理')
    session_id = models.CharField(max_length=255, blank=True, verbose_name='会话ID')
    request_id = models.CharField(max_length=255, blank=True, verbose_name='请求ID')

    # 性能数据
    response_time = models.FloatField(null=True, blank=True, verbose_name='响应时间(ms)')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    timestamp = models.DateTimeField(default=timezone.now, verbose_name='操作时间')

    class Meta:
        verbose_name = '用户活动(增强)'
        verbose_name_plural = '用户活动(增强)'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['resource_type', 'timestamp']),
            models.Index(fields=['session_id', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.resource_type}"

    @classmethod
    def log_activity(cls, user, action, resource_type, resource_id=None, resource_name=None,
                     changes=None, old_values=None, new_values=None, ip_address=None,
                     user_agent=None, session_id=None, request_id=None, response_time=None,
                     error_message=None):
        """记录用户活动的便捷方法"""
        cls.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            changes=changes or {},
            old_values=old_values or {},
            new_values=new_values or {},
            client_ip=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            request_id=request_id,
            response_time=response_time,
            error_message=error_message
        )


class SecurityEvent(models.Model):
    """安全事件模型"""

    EVENT_TYPES = [
        ('login_failed', '登录失败'),
        ('brute_force', '暴力破解'),
        ('account_locked', '账户锁定'),
        ('password_changed', '密码修改'),
        ('session_hijacked', '会话劫持'),
        ('unusual_activity', '异常活动'),
        ('privilege_escalation', '权限提升'),
        ('data_breach', '数据泄露'),
        ('api_abuse', 'API滥用'),
    ]

    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, verbose_name='事件类型')
    user = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='用户')

    # 事件详情
    title = models.CharField(max_length=200, verbose_name='标题')
    description = models.TextField(verbose_name='描述')
    severity = models.CharField(max_length=10, choices=[
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '严重'),
    ], default='medium', verbose_name='严重性')

    # 位置信息
    client_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='客户端IP')
    country = models.CharField(max_length=100, blank=True, verbose_name='国家')
    city = models.CharField(max_length=100, blank=True, verbose_name='城市')
    user_agent = models.TextField(blank=True, verbose_name='用户代理')

    # 事件处理
    is_resolved = models.BooleanField(default=False, verbose_name='已解决')
    resolved_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='resolved_security_events', verbose_name='解决者')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='解决时间')
    resolution_notes = models.TextField(blank=True, verbose_name='解决备注')

    # 处理措施
    actions_taken = models.JSONField(default=list, blank=True, verbose_name='采取的措施')

    # 相关数据
    related_objects = models.JSONField(default=dict, blank=True, verbose_name='相关对象')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')

    detected_at = models.DateTimeField(default=timezone.now, verbose_name='检测时间')

    # 自动阻止相关
    blocked_until = models.DateTimeField(null=True, blank=True, verbose_name='阻止直到')

    class Meta:
        verbose_name = '安全事件'
        verbose_name_plural = '安全事件'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['event_type', 'detected_at']),
            models.Index(fields=['severity', 'is_resolved']),
            models.Index(fields=['user', 'detected_at']),
            models.Index(fields=['client_ip', 'detected_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_severity_display()}"

    @property
    def is_blocked(self):
        """检查是否被自动阻止"""
        if self.blocked_until:
            return timezone.now() < self.blocked_until
        return False

    def resolve(self, user, notes="", actions=None):
        """解决安全事件"""
        self.is_resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        if actions:
            self.actions_taken.extend(actions)
        self.save()

    def block(self, duration_hours=24):
        """临时阻止"""
        self.blocked_until = timezone.now() + timedelta(hours=duration_hours)
        self.save()