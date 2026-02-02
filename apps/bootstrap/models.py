from django.db import models
from apps.hosts.models import Host
import uuid
from django.utils import timezone
from datetime import timedelta
import hashlib
import hmac
import struct
import time
import base64
import json


class BootstrapToken(models.Model):
    """主机引导令牌模型"""
    token = models.CharField(max_length=255, unique=True, verbose_name="引导令牌")
    host = models.OneToOneField(Host, on_delete=models.CASCADE, verbose_name="关联主机", null=True, blank=True)
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
    
    # 新增字段：用于TOTP类似的验证
    pairing_code = models.CharField(max_length=8, unique=True, null=True, blank=True, verbose_name="配对码")
    pairing_code_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="配对码过期时间")
    is_paired = models.BooleanField(default=False, verbose_name="是否已配对")
    paired_at = models.DateTimeField(null=True, blank=True, verbose_name="配对时间")
    
    # 用于TOTP的密钥
    totp_secret = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="TOTP密钥")
    
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
        # 如果没有配对码，则生成一个
        if not self.pairing_code:
            self.pairing_code = self.generate_pairing_code()
            self.pairing_code_expires_at = timezone.now() + timedelta(minutes=10)  # 配对码10分钟过期
        # 如果没有TOTP密钥，则生成一个
        if not self.totp_secret:
            self.totp_secret = self.generate_totp_secret()
        super().save(*args, **kwargs)
    
    def generate_totp_secret(self):
        """生成TOTP使用的密钥"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def generate_pairing_code(self):
        """生成6位数字配对码"""
        import random
        return str(random.randint(100000, 999999)).zfill(6)
    
    def is_pairing_code_expired(self):
        """检查配对码是否过期"""
        if not self.pairing_code_expires_at:
            return True
        return self.pairing_code_expires_at < timezone.now()
    
    def is_pairing_valid(self):
        """检查配对是否有效（未过期且未配对）"""
        return not self.is_pairing_code_expired() and not self.is_paired
    
    def mark_as_paired(self, user=None):
        """标记为已配对"""
        self.is_paired = True
        self.paired_at = timezone.now()
        if user:
            self.used_by = user
        self.save()
    
    def generate_bootstrap_secret(self, c_side_url):
        """生成包含必要信息的bootstrap secret，用于H端初始化"""
        # 创建包含必要信息的数据结构
        secret_data = {
            'c_side_url': c_side_url,
            'token': self.token,
            'totp_secret': self.totp_secret,
            'created_at': int(self.created_at.timestamp()),
            'expires_at': int(self.expires_at.timestamp())
        }
        
        # 将数据转换为JSON并编码为base64
        json_data = json.dumps(secret_data)
        base64_data = base64.b64encode(json_data.encode()).decode()
        return base64_data
    
    def generate_current_totp_code(self):
        """生成当前的TOTP代码"""
        # 使用TOTP算法生成当前时间窗口的代码
        secret = self.totp_secret
        # 将密钥标准化为适合HMAC的格式
        secret_bytes = secret.encode('utf-8')
        
        # 计算时间计数器 (T0 = 0, Time Step = 30秒)
        time_step = 30
        counter = int(time.time() // time_step)
        
        # 将counter转换为8字节的big-endian格式
        counter_bytes = struct.pack('>Q', counter)
        
        # 计算HMAC-SHA1哈希
        h = hmac.new(base64.b32encode(secret_bytes.upper()), counter_bytes, hashlib.sha1).digest()
        
        # 动态截断
        offset = h[-1] & 0x0F
        binary = ((h[offset] & 0x7F) << 24 |
                  (h[offset + 1] & 0xFF) << 16 |
                  (h[offset + 2] & 0xFF) << 8 |
                  (h[offset + 3] & 0xFF))
        
        # 生成6位数字代码
        otp = binary % (10 ** 6)
        return f"{otp:06d}"

    def __str__(self):
        if self.host:
            return f"Bootstrap Token for {self.host.hostname} (Code: {self.pairing_code})"
        else:
            return f"Bootstrap Token (Code: {self.pairing_code})"