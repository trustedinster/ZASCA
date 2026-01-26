"""
用户管理模型
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class User(AbstractUser):
    """
    自定义用户模型

    扩展Django默认用户模型，添加额外字段
    """
    # 基本信息
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('手机号码'),
        help_text=_('用户的手机号码')
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name=_('头像'),
        help_text=_('用户头像图片')
    )

    # 状态信息
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('已验证'),
        help_text=_('用户邮箱是否已验证')
    )
    last_login_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_('最后登录IP'),
        help_text=_('用户最后一次登录的IP地址')
    )

    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间'),
        help_text=_('用户账号创建时间')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间'),
        help_text=_('用户信息最后更新时间')
    )

    class Meta:
        verbose_name = _('用户')
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        """返回用户名"""
        return self.username

    def get_full_name(self):
        """获取用户全名"""
        full_name = super().get_full_name()
        return full_name if full_name else self.username

    def update_last_login(self, request):
        """
        更新最后登录信息

        Args:
            request: Django请求对象
        """
        from utils.helpers import get_client_ip
        self.last_login = timezone.now()
        self.last_login_ip = get_client_ip(request)
        self.save(update_fields=['last_login', 'last_login_ip'])


class UserProfile(models.Model):
    """
    用户资料模型

    存储用户的详细资料信息
    """
    # 关联用户
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('用户'),
        help_text=_('关联的用户')
    )

    # 个人信息
    nickname = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('昵称'),
        help_text=_('用户昵称')
    )
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', _('男')),
            ('female', _('女')),
            ('other', _('其他')),
        ],
        blank=True,
        verbose_name=_('性别'),
        help_text=_('用户性别')
    )
    birthday = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('生日'),
        help_text=_('用户生日')
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('所在地'),
        help_text=_('用户所在地')
    )
    bio = models.TextField(
        blank=True,
        verbose_name=_('个人简介'),
        help_text=_('用户个人简介')
    )

    # 通知设置
    email_notification = models.BooleanField(
        default=True,
        verbose_name=_('邮件通知'),
        help_text=_('是否接收邮件通知')
    )
    system_notification = models.BooleanField(
        default=True,
        verbose_name=_('系统通知'),
        help_text=_('是否接收系统通知')
    )

    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间'),
        help_text=_('资料创建时间')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间'),
        help_text=_('资料最后更新时间')
    )

    class Meta:
        verbose_name = _('用户资料')
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        """返回用户昵称或用户名"""
        return self.nickname or self.user.username


class LoginLog(models.Model):
    """
    登录日志模型

    记录用户的登录历史
    """
    # 关联用户
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='login_logs',
        verbose_name=_('用户'),
        help_text=_('登录的用户')
    )

    # 登录信息
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP地址'),
        help_text=_('登录时的IP地址')
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('用户代理'),
        help_text=_('登录时的浏览器信息')
    )
    login_type = models.CharField(
        max_length=20,
        choices=[
            ('web', _('网页登录')),
            ('api', _('API登录')),
            ('other', _('其他')),
        ],
        default='web',
        verbose_name=_('登录方式'),
        help_text=_('用户的登录方式')
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', _('成功')),
            ('failed', _('失败')),
        ],
        verbose_name=_('登录状态'),
        help_text=_('登录是否成功')
    )
    failure_reason = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('失败原因'),
        help_text=_('登录失败的原因')
    )

    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('登录时间'),
        help_text=_('登录发生的时间')
    )

    class Meta:
        verbose_name = _('登录日志')
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        """返回登录信息"""
        return f'{self.user.username if self.user else "未知用户"} - {self.ip_address}'
