from django.db import models
import logging

logger = logging.getLogger(__name__)


class PluginRecord(models.Model):
    plugin_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='插件ID',
        help_text='插件的唯一标识符',
    )
    name = models.CharField(
        max_length=200,
        verbose_name='插件名称',
        help_text='插件的显示名称',
    )
    version = models.CharField(
        max_length=50,
        verbose_name='版本号',
        help_text='插件的版本号',
    )
    description = models.TextField(
        blank=True, verbose_name='描述',
        help_text='插件的详细描述',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否激活',
        help_text='插件是否处于激活状态',
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='更新时间'
    )

    class Meta:
        verbose_name = '插件记录'
        verbose_name_plural = '插件记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} v{self.version}"


class PluginConfiguration(models.Model):
    plugin = models.ForeignKey(
        PluginRecord,
        on_delete=models.CASCADE,
        verbose_name='插件',
        help_text='配置所属的插件',
    )
    key = models.CharField(
        max_length=200,
        verbose_name='配置键',
        help_text='配置参数的键名',
    )
    value = models.TextField(
        verbose_name='配置值',
        help_text='配置参数的值',
    )
    description = models.TextField(
        blank=True,
        verbose_name='描述',
        help_text='配置项的描述',
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='更新时间'
    )

    class Meta:
        verbose_name = '插件配置'
        verbose_name_plural = '插件配置'
        unique_together = [['plugin', 'key']]
        constraints = [
            models.UniqueConstraint(
                fields=['plugin', 'key'],
                name='unique_plugin_key',
            )
        ]

    def __str__(self):
        return f"{self.plugin.name}: {self.key}"
