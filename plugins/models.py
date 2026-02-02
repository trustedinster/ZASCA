"""
插件系统的Django模型
用于在数据库中存储插件信息和状态
"""

from django.db import models
from apps.operations.models import Product  # 导入Product模型
import logging

logger = logging.getLogger(__name__)


class QQVerificationConfig(models.Model):
    """
    QQ验证插件配置模型
    用于存储QQ群验证插件的配置信息，与产品关联
    """
    
    # 邮箱后缀处理策略
    EMAIL_SUFFIX_HANDLING_CHOICES = [
        ('default_allow', '默认符合'),
        ('default_deny', '默认不符合'),
        ('manual_review', '等待人工处理'),
    ]
    
    # 启用状态
    ENABLE_STATUS_CHOICES = [
        ('disabled', '禁用'),
        ('enabled_require_group', '启用-要求入群'),
        ('enabled_old_six_mode', '启用-老六模式'),
        ('enabled_both', '启用-两种模式'),
    ]
    
    # 与Product模型的外键关联
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        verbose_name='关联产品',
        help_text='此QQ验证配置关联的产品',
        related_name='qq_verification_config'
    )
    
    # 基本配置
    host = models.CharField(
        max_length=255,
        verbose_name='机器人服务器地址',
        help_text='QQ机器人服务器的主机地址'
    )
    
    port = models.CharField(
        max_length=20,
        verbose_name='机器人服务器端口',
        help_text='QQ机器人服务器的端口号'
    )
    
    token = models.CharField(
        max_length=255,
        verbose_name='访问令牌',
        help_text='用于认证的访问令牌'
    )
    
    group_id = models.CharField(
        max_length=20,
        verbose_name='验证群号',
        help_text='用于验证QQ号是否在群内的群号'
    )
    
    # 验证启用状态
    enable_status = models.CharField(
        max_length=25,  # 增加长度以适应选项值
        choices=ENABLE_STATUS_CHOICES,
        default='disabled',
        verbose_name='启用状态',
        help_text='QQ验证功能的启用状态'
    )
    
    # 非QQ邮箱后缀处理策略
    non_qq_email_handling = models.CharField(
        max_length=20,
        choices=EMAIL_SUFFIX_HANDLING_CHOICES,
        default='default_deny',
        verbose_name='非QQ邮箱处理策略',
        help_text='当用户使用非QQ邮箱时的处理策略'
    )
    
    # 创建和更新时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'QQ验证配置'
        verbose_name_plural = 'QQ验证配置'
        # 确保每个产品只有一条配置记录
        unique_together = ['product']

    def __str__(self):
        return f"{self.product.display_name} - QQ验证配置"

    @property
    def is_require_group_enabled(self):
        """是否启用要求入群模式"""
        result = self.enable_status in ['enabled_require_group', 'enabled_both']
        logger.debug(f"QQ验证配置 - 产品 {self.product.display_name} ({self.product.id}) 入群要求状态: {result}")
        return result

    @property
    def is_old_six_mode_enabled(self):
        """是否启用老六模式"""
        result = self.enable_status in ['enabled_old_six_mode', 'enabled_both']
        logger.debug(f"QQ验证配置 - 产品 {self.product.display_name} ({self.product.id}) 老六模式状态: {result}")
        return result


class PluginRecord(models.Model):
    """
    插件记录模型
    用于跟踪系统中安装的插件及其状态
    """
    plugin_id = models.CharField(max_length=100, unique=True, verbose_name='插件ID', help_text='插件的唯一标识符')
    name = models.CharField(max_length=200, verbose_name='插件名称', help_text='插件的显示名称')
    version = models.CharField(max_length=50, verbose_name='版本号', help_text='插件的版本号')
    description = models.TextField(blank=True, verbose_name='描述', help_text='插件的详细描述')
    is_active = models.BooleanField(default=True, verbose_name='是否激活', help_text='插件是否处于激活状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '插件记录'
        verbose_name_plural = '插件记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} v{self.version}"


class PluginConfiguration(models.Model):
    """
    插件配置模型
    用于存储插件的配置参数
    """
    plugin = models.ForeignKey(PluginRecord, on_delete=models.CASCADE, verbose_name='插件', 
                              help_text='配置所属的插件')
    key = models.CharField(max_length=200, verbose_name='配置键', help_text='配置参数的键名')
    value = models.TextField(verbose_name='配置值', help_text='配置参数的值')
    description = models.TextField(blank=True, verbose_name='描述', help_text='配置项的描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '插件配置'
        verbose_name_plural = '插件配置'
        unique_together = [['plugin', 'key']]  # 每个插件的每个配置键只能有一个值
        constraints = [
            models.UniqueConstraint(fields=['plugin', 'key'], name='unique_plugin_key')
        ]

    def __str__(self):
        return f"{self.plugin.name}: {self.key}"