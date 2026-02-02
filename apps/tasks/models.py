from django.db import models
from django.utils import timezone


class AsyncTask(models.Model):
    """异步任务状态跟踪模型"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]

    task_id = models.CharField(max_length=255, unique=True, verbose_name="任务ID")
    name = models.CharField(max_length=255, verbose_name="任务名称")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="任务状态"
    )
    created_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    progress = models.IntegerField(default=0, verbose_name="进度百分比")  # 进度百分比 0-100
    result = models.JSONField(null=True, blank=True, verbose_name="任务结果")  # 任务结果
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")
    target_object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="目标对象ID")
    target_content_type = models.CharField(max_length=100, null=True, blank=True, verbose_name="目标对象类型")

    class Meta:
        verbose_name = "异步任务"
        verbose_name_plural = "异步任务"
        db_table = "async_task"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.status}"

    def start_execution(self):
        """标记任务开始执行"""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save()

    def complete_success(self, result_data=None):
        """标记任务执行成功"""
        self.status = 'success'
        self.completed_at = timezone.now()
        self.progress = 100
        if result_data:
            self.result = result_data
        self.save()

    def complete_failure(self, error_msg):
        """标记任务执行失败"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_msg
        self.save()

    def cancel_task(self):
        """取消任务"""
        self.status = 'cancelled'
        self.completed_at = timezone.now()
        self.save()

    @property
    def duration(self):
        """任务执行时长"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None


class TaskProgress(models.Model):
    """任务进度详情模型"""
    task = models.ForeignKey(AsyncTask, on_delete=models.CASCADE, related_name='progress_updates')
    progress = models.IntegerField(verbose_name="进度百分比")
    message = models.TextField(blank=True, null=True, verbose_name="进度消息")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="时间戳")

    class Meta:
        verbose_name = "任务进度"
        verbose_name_plural = "任务进度"
        db_table = "task_progress"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.task.name} - {self.progress}%"