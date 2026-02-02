from django.db import models
from apps.hosts.models import Host
import uuid
from django.utils import timezone
from datetime import timedelta


class BootstrapToken(models.Model):
    """主机引导令牌模型"""
    token = models.CharField(max_length=255, unique=True, verbose_name="引导令牌")
    host = models.OneToOneField(Host, on_delete=models.CASCADE, verbose_name="关联主机")
    created_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    expires_at = models.DateTimeField(verbose_name="过期时间")
    is_used = models.BooleanField(default=False, verbose_name="是否已使用")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="使用时间")
    used_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='used_bootstrap_tokens',
        verbose_name="使用者"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="备注")

    class Meta:
        verbose_name = "引导令牌"
        verbose_name_plural = "引导令牌"
        db_table = "bootstrap_token"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid.uuid4())
        # 确保在创建时如果没有设置过期时间，则设置默认值
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        """检查令牌是否已过期"""
        return self.expires_at < timezone.now()

    def is_valid(self):
        """检查令牌是否有效（未过期且未使用）"""
        return not self.is_expired() and not self.is_used

    def mark_as_used(self, user=None):
        """标记令牌为已使用"""
        self.is_used = True
        self.used_at = timezone.now()
        self.used_by = user
        self.save()

    def __str__(self):
        return f"Bootstrap Token for {self.host.hostname}"