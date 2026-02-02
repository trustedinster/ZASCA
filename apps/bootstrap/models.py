from django.db import models
from apps.hosts.models import Host
import uuid
from django.utils import timezone
from datetime import timedelta
import hashlib
import hmac
import base64
from django.conf import settings


class InitialToken(models.Model):
    """初始配置令牌表 - 根据规范定义"""
    STATUS_CHOICES = [
        ('ISSUED', '已签发'),
        ('TOTP_VERIFIED', '已验证'),
        ('CONSUMED', '已消耗'),
    ]
    
    token = models.CharField(max_length=255, primary_key=True, verbose_name="AccessToken")
    host = models.ForeignKey(Host, on_delete=models.CASCADE, verbose_name="关联的主机")
    expires_at = models.DateTimeField(verbose_name="AccessToken过期时间")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ISSUED', verbose_name="状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "初始令牌"
        verbose_name_plural = "初始令牌"
        db_table = "initial_token"

    def generate_totp_secret(self):
        """根据规范生成TOTP密钥"""
        input_string = f"{self.token}|{self.host.id}|{self.expires_at.isoformat()}"
        
        # 使用共享静态盐进行HMAC-SHA256计算
        shared_salt = getattr(settings, 'BOOTSTRAP_SHARED_SALT', 'MY_SECRET_2024')
        raw_hash = hmac.new(
            shared_salt.encode('utf-8'), 
            input_string.encode('utf-8'), 
            hashlib.sha256
        ).digest()
        
        # 取前20个字节进行Base32编码
        truncated_hash = raw_hash[:20]
        totp_secret = base64.b32encode(truncated_hash).decode('utf-8').rstrip('=')
        
        return totp_secret


class ActiveSession(models.Model):
    """活动会话表 - 根据规范定义"""
    session_token = models.CharField(max_length=255, primary_key=True, verbose_name="临时凭证")
    host = models.ForeignKey(Host, on_delete=models.CASCADE, verbose_name="关联的主机")
    bound_ip = models.GenericIPAddressField(verbose_name="绑定的请求源IP")
    expires_at = models.DateTimeField(verbose_name="24小时后的过期时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "活动会话"
        verbose_name_plural = "活动会话"
        db_table = "active_session"