from django.db import models
from django.conf import settings


class SyncLog(models.Model):
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='beta_push_logs',
        verbose_name='用户',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态',
    )
    task_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Celery任务ID',
    )
    records_pushed = models.IntegerField(
        default=0,
        verbose_name='推送记录数',
    )
    records_skipped = models.IntegerField(
        default=0,
        verbose_name='跳过记录数',
    )
    records_failed = models.IntegerField(
        default=0,
        verbose_name='失败记录数',
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='错误信息',
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='开始时间',
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )

    class Meta:
        verbose_name = 'Beta推送日志'
        verbose_name_plural = 'Beta推送日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'Beta推送({self.user.username}) - {self.get_status_display()}'
