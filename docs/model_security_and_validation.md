# Django模型安全与验证指南

## 概述

本文档介绍Django模型的安全实践和验证机制，基于ZASCA项目中的实际安全措施和验证实现。

## 模型安全最佳实践

### 1. 敏感数据保护

#### 密码加密存储

```python
from django.core.signing import Signer

class Host(models.Model):
    """主机模型 - 演示敏感数据加密存储"""
    
    # 使用内部字段名存储加密数据
    _password = models.CharField(max_length=255, verbose_name='密码', db_column='password')
    
    @property
    def password(self):
        """
        获取解密后的密码
        注意：此属性不应在模板或日志中直接使用
        """
        signer = Signer()
        try:
            return signer.unsign(self._password)
        except:
            # 如果解密失败，说明可能是未加密的旧数据
            return self._password

    @password.setter
    def password(self, raw_password):
        """
        设置并加密密码
        """
        signer = Signer()
        self._password = signer.sign(raw_password)
```

#### 安全的密码生成

```python
import secrets
import string

class CloudComputerUser(models.Model):
    """云电脑用户模型 - 演示安全密码生成"""
    
    initial_password = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='初始密码'
    )
    
    @staticmethod
    def generate_complex_password(length=16):
        """
        生成复杂密码
        
        Args:
            length: 密码长度，默认为16位
        
        Returns:
            生成的复杂密码
        """
        # 包含大写字母、小写字母、数字和特殊字符
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        # 确保至少包含每种类型的字符
        while True:
            password = ''.join(secrets.choice(alphabet) for i in range(length))
            
            # 检查是否包含所需类型的字符
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
            
            if has_upper and has_lower and has_digit and has_special:
                return password
    
    def get_and_burn_password(self):
        """
        获取并销毁密码 - 实现阅后即焚功能
        """
        from django.utils import timezone
        
        # 如果密码从未被查看过（首次访问），返回初始密码并标记为已查看
        if not self.password_viewed and self.initial_password:
            password = self.initial_password
            
            # 标记密码已被查看并清空存储的密码
            self.password_viewed = True
            self.password_viewed_at = timezone.now()
            self.initial_password = ''  # 清空密码
            self.save(update_fields=['password_viewed', 'password_viewed_at', 'initial_password'])
            
            return password
        else:
            # 如果已经查看过密码（即后续访问），生成新密码但不存储
            new_password = CloudComputerUser.generate_complex_password()
            # 通过远程命令重置Windows用户密码
            self.reset_windows_password(new_password)
            return new_password
```

### 2. 输入验证

#### 模型级验证

```python
from django.core.exceptions import ValidationError

class SystemConfig(models.Model):
    """系统配置模型 - 演示模型级验证"""
    
    # 验证码配置
    captcha_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='验证码 ID'
    )
    
    captcha_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='验证码密钥'
    )

    # 验证码提供器
    CAPTCHA_PROVIDERS = (
        ('none', '无'),
        ('geetest', 'Geetest (极验 v4)'),
        ('turnstile', 'Cloudflare Turnstile'),
        ('local', '本地图片验证码'),
    )
    captcha_provider = models.CharField(
        max_length=32,
        choices=CAPTCHA_PROVIDERS,
        default='none',
        verbose_name='验证码提供器'
    )

    def clean(self):
        """Model-level validation: Validate that when a provider is enabled, its required keys are present."""
        errors = {}
        
        # Provider-based validation (captcha_provider is primary selector)
        provider = getattr(self, 'captcha_provider', 'none')
        if provider in ['geetest', 'turnstile']:
            if not (self.captcha_id and self.captcha_key):
                errors['captcha_id'] = f'启用 {self.get_captcha_provider_display()} 时必须填写验证码 ID 和密钥。'
                errors['captcha_key'] = f'启用 {self.get_captcha_provider_display()} 时必须填写验证码 ID 和密钥。'
        elif provider == 'local':
            # local provider requires no external keys
            pass
        else:
            # none - no validation needed
            pass

        if errors:
            raise ValidationError(errors)
```

#### 自定义验证器

```python
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator

class EmailSuffixListValidator(BaseValidator):
    """邮箱后缀列表验证器"""
    
    def __call__(self, value):
        if value:
            suffixes = [suffix.strip() for suffix in value.split('\n') if suffix.strip()]
            for suffix in suffixes:
                if not suffix.startswith('@'):
                    raise ValidationError(f'邮箱后缀必须以@开头: {suffix}')
                if '@@' in suffix:
                    raise ValidationError(f'邮箱后缀格式不正确: {suffix}')

class SystemConfig(models.Model):
    """系统配置模型 - 使用自定义验证器"""
    
    email_suffix_list = models.TextField(
        blank=True,
        null=True,
        verbose_name='邮箱后缀列表',
        help_text='允许或禁止的邮箱后缀列表，每行一个后缀，例如：\n@example.com\n@gmail.com\n@company.com',
        validators=[EmailSuffixListValidator()]  # 添加自定义验证器
    )
```

### 3. 字段级安全

#### 敏感字段保护

```python
class LoginLog(models.Model):
    """登录日志模型 - 演示敏感字段保护"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='login_logs',
        verbose_name='用户'
    )
    
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    user_agent = models.TextField(blank=True, verbose_name='用户代理')
    
    # 避免在模型中直接存储敏感信息
    # 而是在需要时动态处理
    
    class Meta:
        # 控制数据访问权限
        permissions = [
            ("view_sensitive_login_logs", "Can view sensitive login logs"),
            ("delete_login_logs", "Can delete login logs"),
        ]
```

## 验证层次结构

### 1. 字段级验证

```python
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

class Host(models.Model):
    """主机模型 - 字段级验证示例"""
    
    # 正则表达式验证
    hostname_validator = RegexValidator(
        regex=r'^[\w\.-]+$',
        message='主机名只能包含字母、数字、点和连字符'
    )
    hostname = models.CharField(
        max_length=255,
        verbose_name='主机地址',
        validators=[hostname_validator]
    )
    
    # 数值范围验证
    port = models.IntegerField(
        default=5985,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name='连接端口'
    )
    
    rdp_port = models.IntegerField(
        default=3389,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name='RDP端口'
    )
    
    # 选择验证
    HOST_TYPE_CHOICES = [
        ('server', '服务器'),
        ('workstation', '工作站'),
        ('laptop', '笔记本'),
        ('desktop', '台式机'),
    ]
    host_type = models.CharField(
        max_length=20,
        choices=HOST_TYPE_CHOICES,
        verbose_name='主机类型'
    )
```

### 2. 模型级验证

```python
class AccountOpeningRequest(models.Model):
    """开户申请模型 - 模型级验证示例"""
    
    # 基本字段
    username = models.CharField(max_length=150, verbose_name='用户名')
    user_fullname = models.CharField(max_length=200, verbose_name='用户姓名')
    user_email = models.EmailField(verbose_name='用户邮箱')
    
    # 关联字段
    target_product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        verbose_name='目标产品',
        null=True,
        blank=True
    )
    
    def clean(self):
        """模型级验证"""
        from django.core.exceptions import ValidationError
        
        # 自定义业务逻辑验证
        if self.target_product and not self.target_product.is_available:
            raise ValidationError({
                'target_product': '选择的产品当前不可用'
            })
        
        # 用户名格式验证
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,29}$', self.username):
            raise ValidationError({
                'username': '用户名必须以字母开头，包含3-30个字母、数字或下划线'
            })
        
        # 邮箱域名检查（基于系统配置）
        from .models import SystemConfig
        config = SystemConfig.get_config()
        if config.email_suffix_mode == 'whitelist':
            domain = self.user_email.split('@')[1] if '@' in self.user_email else ''
            allowed_domains = [suffix.strip()[1:] for suffix in config.email_suffix_list.split('\n') if suffix.strip().startswith('@')]
            if domain and domain not in allowed_domains:
                raise ValidationError({
                    'user_email': f'邮箱域名 @{domain} 不在允许列表中'
                })

    def save(self, *args, **kwargs):
        """重写保存方法，执行验证和业务逻辑"""
        # 在保存前执行验证
        self.full_clean()  # 执行所有验证
        super().save(*args, **kwargs)
```

### 3. 应用级验证

```python
class SystemConfig(models.Model):
    """系统配置模型 - 应用级验证"""
    
    # ... 其他字段 ...
    
    def get_captcha_config(self, scene=None):
        """
        获取指定场景的验证码配置，如果没有为场景单独配置，则使用全局配置
        :param scene: 场景标识符 ('login', 'register', 'email', None)
        :return: (provider, captcha_id, captcha_key)
        """
        if scene == 'login':
            provider = self.login_captcha_provider or self.captcha_provider
            captcha_id = self.login_captcha_id or self.captcha_id
            captcha_key = self.login_captcha_key or self.captcha_key
        elif scene == 'register':
            provider = self.register_captcha_provider or self.captcha_provider
            captcha_id = self.register_captcha_id or self.captcha_id
            captcha_key = self.register_captcha_key or self.captcha_key
        elif scene == 'email':
            provider = self.email_captcha_provider or self.captcha_provider
            captcha_id = self.email_captcha_id or self.captcha_id
            captcha_key = self.email_captcha_key or self.captcha_key
        else:
            # 全局配置
            provider = self.captcha_provider
            captcha_id = self.captcha_id
            captcha_key = self.captcha_key

        # 应用级验证：确保配置完整
        if provider and provider != 'none':
            if not (captcha_id and captcha_key):
                raise ValueError(f'场景 {scene or "全局"} 的 {provider} 配置不完整')
        
        return provider, captcha_id, captcha_key
```

## 安全控制

### 1. 数据访问控制

```python
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

class Host(models.Model):
    """主机模型 - 数据访问控制"""
    
    name = models.CharField(max_length=100, verbose_name='主机名称')
    hostname = models.CharField(max_length=255, verbose_name='主机地址')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='创建者'
    )
    
    class Meta:
        verbose_name = '主机'
        verbose_name_plural = '主机'
        # 定义自定义权限
        permissions = [
            ("can_connect_to_host", "Can connect to host"),
            ("can_manage_hosts", "Can manage all hosts"),
            ("can_view_host_credentials", "Can view host credentials"),
        ]
    
    def can_user_access(self, user):
        """检查用户是否有访问权限"""
        # 超级用户拥有所有权限
        if user.is_superuser:
            return True
        
        # 创建者可以访问自己创建的主机
        if self.created_by == user:
            return True
        
        # 拥有全局管理权限的用户可以访问
        if user.has_perm('hosts.can_manage_hosts'):
            return True
        
        return False
```

### 2. 数据脱敏

```python
class Host(models.Model):
    """主机模型 - 数据脱敏"""
    
    # ... 字段定义 ...
    
    def to_dict_safe(self, include_credentials=False):
        """安全的序列化方法"""
        data = {
            'id': self.id,
            'name': self.name,
            'hostname': self.hostname,
            'host_type': self.host_type,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
        
        # 只有在明确要求时才包含凭证信息
        if include_credentials:
            # 即使包含凭证，也应该进行额外的安全处理
            data['credentials'] = {
                'username': self.username,
                'password': self.password  # 注意：实际应用中不应返回密码
            }
        
        return data
    
    def __str__(self):
        """安全的字符串表示"""
        return f"Host({self.name})"
```

## 验证错误处理

### 1. 统一错误处理

```python
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class SecureModelMixin:
    """安全模型混入类 - 提供统一的验证错误处理"""
    
    def full_clean(self, exclude=None, validate_unique=True):
        """重写完整清理方法，提供统一的错误处理"""
        try:
            super().full_clean(exclude, validate_unique)
        except ValidationError as e:
            # 记录验证错误
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Model validation failed for {self.__class__.__name__}: {e}")
            
            # 重新抛出异常
            raise
    
    def save(self, *args, **kwargs):
        """重写保存方法，包含验证和错误处理"""
        # 验证数据
        self.full_clean()
        
        # 执行保存
        super().save(*args, **kwargs)
        
        # 记录成功保存
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Saved {self.__class__.__name__} with id {self.id}")

class Host(SecureModelMixin, models.Model):
    """使用安全混入类的主机模型"""
    # ... 字段定义 ...
```

### 2. 验证上下文

```python
class AccountOpeningRequest(models.Model):
    """开户申请模型 - 验证上下文"""
    
    # ... 字段定义 ...
    
    def validate_for_scene(self, scene='creation'):
        """根据场景进行验证"""
        errors = {}
        
        if scene in ['creation', 'modification']:
            # 创建和修改时的验证
            if not self.username:
                errors['username'] = _('用户名不能为空')
            
            if not self.user_email:
                errors['user_email'] = _('用户邮箱不能为空')
        
        if scene == 'approval':
            # 审核时的验证
            if not self.target_product:
                errors['target_product'] = _('必须指定目标产品')
            
            if self.status != 'pending':
                errors['status'] = _('只有待审核状态的申请才能被批准')
        
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)
```

## 安全审计

### 1. 操作日志

```python
class AuditMixin(models.Model):
    """审计混入类"""
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name='创建者'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name='最后更新者'
    )
    
    class Meta:
        abstract = True

class Host(AuditMixin, models.Model):
    """带审计功能的主机模型"""
    # ... 字段定义 ...
    
    def save(self, *args, **kwargs):
        """重写保存方法，记录操作用户"""
        # 注意：需要在视图层传入request.user
        request = kwargs.pop('request', None)
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if not self.pk:  # 新建
                self.created_by = request.user
            self.updated_by = request.user
        
        super().save(*args, **kwargs)
```

### 2. 安全监控

```python
class SecurityMonitorMixin:
    """安全监控混入类"""
    
    def save(self, *args, **kwargs):
        """保存时进行安全检查"""
        # 执行基类保存
        super().save(*args, **kwargs)
        
        # 安全监控
        self._security_audit()
    
    def _security_audit(self):
        """安全审计"""
        import logging
        logger = logging.getLogger('security')
        
        # 记录敏感操作
        if hasattr(self, '_password') or hasattr(self, 'api_key'):
            logger.info(f"Sensitive data updated for {self.__class__.__name__} #{self.id}")
        
        # 检查异常模式
        if hasattr(self, 'status') and self.status == 'disabled':
            logger.warning(f"Account disabled: {self.__class__.__name__} #{self.id}")

class User(SecurityMonitorMixin, AbstractUser):
    """带安全监控的用户模型"""
    # ... 字段定义 ...
```

## 最佳实践总结

1. **数据加密**：敏感数据必须加密存储
2. **输入验证**：多层次验证机制
3. **权限控制**：细粒度的访问控制
4. **审计日志**：记录重要操作
5. **错误处理**：安全的错误信息处理
6. **数据脱敏**：避免敏感信息泄露
7. **安全监控**：实时监控安全事件

通过实施这些安全措施和验证机制，可以构建更加安全可靠的Django应用。