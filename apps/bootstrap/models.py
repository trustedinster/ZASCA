from django.db import models
from apps.hosts.models import Host
import uuid
from django.utils import timezone
from datetime import timedelta
import random
from django.conf import settings


class InitialToken(models.Model):
    """初始配置令牌表 - 基于配对码的简化认证机制"""
    STATUS_CHOICES = [
        ('ISSUED', '已签发'),
        ('PAIRED', '已配对'),
        ('CONSUMED', '已消耗'),
    ]
    
    token = models.CharField(max_length=255, primary_key=True, verbose_name="AccessToken")
    host = models.ForeignKey(Host, on_delete=models.CASCADE, verbose_name="关联的主机")
    expires_at = models.DateTimeField(verbose_name="AccessToken过期时间")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ISSUED', verbose_name="状态")
    pairing_code = models.CharField(max_length=6, verbose_name="配对码", blank=True, null=True)  # 6位数字配对码
    pairing_code_expires_at = models.DateTimeField(verbose_name="配对码过期时间", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "初始令牌"
        verbose_name_plural = "初始令牌"
        db_table = "initial_token"

    def generate_pairing_code(self):
        """生成6位数字配对码"""
        # 生成6位随机数字（000000-999999）
        code = f"{random.randint(0, 999999):06d}"
        self.pairing_code = code
        self.pairing_code_expires_at = timezone.now() + timedelta(minutes=5)  # 5分钟有效期
        self.save()
        return code

    def verify_pairing_code(self, input_code):
        """验证配对码是否正确且未过期"""
        if not self.pairing_code or not self.pairing_code_expires_at:
            return False
        
        # 检查是否过期
        if timezone.now() > self.pairing_code_expires_at:
            return False
        
        # 检查配对码是否正确
        if self.pairing_code != input_code:
            return False
        
        # 验证成功，更新状态
        self.status = 'PAIRED'
        self.pairing_code = None  # 清除配对码，一次性使用
        self.pairing_code_expires_at = None
        self.save()
        return True


class ActiveSession(models.Model):
    """活动会话表 - 基于配对码认证的会话管理"""
    session_token = models.CharField(max_length=255, primary_key=True, verbose_name="临时凭证")
    host = models.ForeignKey(Host, on_delete=models.CASCADE, verbose_name="关联的主机")
    bound_ip = models.GenericIPAddressField(verbose_name="绑定的请求源IP")
    expires_at = models.DateTimeField(verbose_name="会话过期时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "活动会话"
        verbose_name_plural = "活动会话"
        db_table = "active_session"