# Django模型编写指南

## 概述

Django模型(Model)是数据抽象层，定义了数据的结构、行为和关系。模型本质上是Python类，继承自`django.db.models.Model`，每个属性对应数据库中的一个字段。

## 基础概念

### 1. 模型定义

每个模型都是一个Python类，继承自`django.db.models.Model`或其子类：

```python
from django.db import models

class MyModel(models.Model):
    field_name = models.CharField(max_length=100)
```

### 2. 字段类型

Django提供了多种字段类型来满足不同数据需求：

- `CharField`: 字符串字段，需要指定`max_length`
- `TextField`: 长文本字段
- `IntegerField`: 整数字段
- `DateTimeField`: 日期时间字段
- `BooleanField`: 布尔字段
- `ForeignKey`: 外键关系
- `ManyToManyField`: 多对多关系
- `JSONField`: JSON数据字段
- `GenericIPAddressField`: IP地址字段
- `ImageField`: 图片字段

## 模型字段选项

### 通用字段选项

```python
class MyModel(models.Model):
    # verbose_name: 字段的可读名称
    name = models.CharField(
        max_length=100,
        verbose_name='姓名',
        help_text='用户的真实姓名'
    )
    
    # blank: 是否允许为空字符串
    description = models.TextField(
        blank=True,  # 在表单中允许为空
        null=True    # 在数据库中允许为NULL
    )
    
    # null: 是否允许数据库中为NULL
    age = models.IntegerField(
        null=True,
        blank=True
    )
    
    # default: 默认值
    created_at = models.DateTimeField(
        auto_now_add=True,  # 第次创建时自动设置
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,      # 每次保存时自动更新
        verbose_name='更新时间'
    )
    
    # choices: 选择选项
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
```

### 字段验证

Django提供多种方式验证数据：

```python
from django.core.validators import MinValueValidator, MaxValueValidator

class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    rating = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
```

## 模型元数据 (Meta)

通过内部`Meta`类配置模型的元数据：

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    class Meta:
        # 数据库表名
        db_table = 'my_articles'
        
        # 人类可读的单数和复数名称
        verbose_name = '文章'
        verbose_name_plural = '文章'
        
        # 排序规则
        ordering = ['-created_at']  # 按创建时间倒序
        
        # 索引配置
        indexes = [
            models.Index(fields=['title']),           # 单字段索引
            models.Index(fields=['title', 'author']), # 复合索引
            models.Index(fields=['-created_at']),     # 降序索引
        ]
        
        # 唯一约束
        unique_together = [['title', 'author']]      # 联合唯一约束
```

## 模型关系

### 一对一关系 (OneToOneField)

```python
class User(models.Model):
    username = models.CharField(max_length=100)

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,  # 级联删除
        related_name='profile'      # 反向查询名称
    )
    bio = models.TextField()
```

### 一对多关系 (ForeignKey)

```python
class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name='books'  # 反向查询名称
    )
```

### 多对多关系 (ManyToManyField)

```python
class Student(models.Model):
    name = models.CharField(max_length=100)

class Course(models.Model):
    name = models.CharField(max_length=100)
    students = models.ManyToManyField(
        Student,
        related_name='courses',
        through='Enrollment'  # 指定中间模型
    )

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrollment_date = models.DateField()
```

## 模型方法

### 1. 特殊方法

```python
class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        """返回对象的字符串表示"""
        return self.title
    
    def get_absolute_url(self):
        """返回对象的URL"""
        from django.urls import reverse
        return reverse('article_detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        """自定义保存方法"""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
```

### 2. 自定义方法

```python
class Order(models.Model):
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    
    def calculate_tax(self):
        """计算税费"""
        return self.total_amount * 0.1
    
    def is_paid(self):
        """检查订单是否已支付"""
        return self.status == 'paid'
    
    def get_total_with_tax(self):
        """获取含税总价"""
        return self.total_amount + self.calculate_tax()
```

## 属性和描述符

对于需要特殊处理的字段，可以使用属性(property)：

```python
class User(models.Model):
    _password = models.CharField(max_length=255, db_column='password')
    
    @property
    def password(self):
        """获取解密后的密码"""
        from django.core.signing import Signer
        signer = Signer()
        try:
            return signer.unsign(self._password)
        except:
            # 如果解密失败，说明可能是未加密的旧数据
            return self._password

    @password.setter
    def password(self, raw_password):
        """设置并加密密码"""
        from django.core.signing import Signer
        signer = Signer()
        self._password = signer.sign(raw_password)
```

## 模型验证

### 字段级验证

```python
from django.core.exceptions import ValidationError

class Person(models.Model):
    age = models.IntegerField()
    
    def clean(self):
        """模型级别的验证"""
        super().clean()
        if self.age < 0:
            raise ValidationError({'age': '年龄不能为负数'})
        if self.age > 150:
            raise ValidationError({'age': '年龄不能超过150岁'})
```

### 自定义验证器

```python
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# 自定义验证器
def validate_even(value):
    if value % 2 != 0:
        raise ValidationError(
            '%(value)s 不是偶数',
            params={'value': value},
        )

class MyModel(models.Model):
    even_number = models.IntegerField(validators=[validate_even])
    
    # 使用内置验证器
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="电话号码格式不正确"
    )
    phone = models.CharField(validators=[phone_regex], max_length=17)
```

## 查询优化

### 索引设置

```python
class User(models.Model):
    email = models.EmailField()
    created_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            # 为经常查询的字段创建索引
            models.Index(fields=['email']),
            models.Index(fields=['-created_at']),
            # 为复合查询创建索引
            models.Index(fields=['email', 'created_at']),
        ]
```

### 数据库约束

```python
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name='price_gte_0'
            ),
        ]
```

## 实际项目示例

基于ZASCA项目中的模型，以下是一些最佳实践示例：

### 1. 自定义用户模型

```python
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """自定义用户模型"""
    
    # 扩展字段
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
    
    # 状态字段
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('已验证'),
        help_text=_('用户邮箱是否已验证')
    )
    
    # 时间字段
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
        return self.username
```

### 2. 系统配置模型

```python
class SystemConfig(models.Model):
    """系统配置模型"""
    
    # SMTP配置
    smtp_host = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='SMTP服务器',
        help_text='SMTP服务器地址，如smtp.gmail.com'
    )
    smtp_port = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='SMTP端口',
        help_text='SMTP服务器端口，通常为587或465'
    )
    
    # 验证码配置
    captcha_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='验证码 ID',
        help_text='验证码服务的公共ID'
    )
    
    # 验证码提供器选择
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
        verbose_name='验证码提供器',
        help_text='选择要启用的验证码提供器（只能选择其一）'
    )
    
    # 其他配置
    site_name = models.CharField(
        max_length=100,
        default='ZASCA',
        verbose_name='站点名称',
        help_text='系统显示的站点名称'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    class Meta:
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'
    
    def __str__(self):
        return f'{self.site_name} 配置'
    
    def clean(self):
        """模型级验证"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        provider = getattr(self, 'captcha_provider', 'none')
        if provider in ['geetest', 'turnstile']:
            if not (self.captcha_id and self.captcha_key):
                errors['captcha_id'] = f'启用 {self.get_captcha_provider_display()} 时必须填写验证码 ID 和密钥。'
                errors['captcha_key'] = f'启用 {self.get_captcha_provider_display()} 时必须填写验证码 ID 和密钥。'
        
        if errors:
            raise ValidationError(errors)
```

### 3. 主机模型（带加密字段）

```python
class Host(models.Model):
    """主机模型"""
    
    HOST_TYPE_CHOICES = [
        ('server', '服务器'),
        ('workstation', '工作站'),
        ('laptop', '笔记本'),
        ('desktop', '台式机'),
    ]
    
    CONNECTION_TYPE_CHOICES = [
        ('winrm', 'WinRM'),
        ('ssh', 'SSH'),
        ('localwinserver', '本地WinServer'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='主机名称')
    hostname = models.CharField(max_length=255, verbose_name='主机地址')
    connection_type = models.CharField(
        max_length=20, 
        choices=CONNECTION_TYPE_CHOICES, 
        default='winrm', 
        verbose_name='连接类型'
    )
    port = models.IntegerField(default=5985, verbose_name='连接端口')
    username = models.CharField(max_length=100, verbose_name='用户名')
    _password = models.CharField(max_length=255, verbose_name='密码', db_column='password')
    host_type = models.CharField(max_length=20, choices=HOST_TYPE_CHOICES, verbose_name='主机类型')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '主机'
        verbose_name_plural = '主机'
        db_table = 'hosts_host'

    def __str__(self):
        return self.name

    @property
    def password(self):
        """获取解密后的密码"""
        from django.core.signing import Signer
        signer = Signer()
        try:
            return signer.unsign(self._password)
        except:
            # 如果解密失败，说明可能是未加密的旧数据
            return self._password

    @password.setter
    def password(self, raw_password):
        """设置并加密密码"""
        from django.core.signing import Signer
        signer = Signer()
        self._password = signer.sign(raw_password)
```

## 模型最佳实践

### 1. 性能优化

- 为经常查询的字段创建数据库索引
- 使用`select_related`和`prefetch_related`优化查询
- 避免在循环中执行数据库查询
- 使用`only()`和`defer()`减少不必要的字段加载

### 2. 数据安全

- 对敏感数据进行加密存储
- 使用Django的验证机制确保数据完整性
- 避免SQL注入，使用ORM查询而非原生SQL

### 3. 代码组织

- 为每个应用创建独立的models.py文件
- 使用有意义的模型和字段名称
- 添加适当的注释和文档字符串
- 合理使用模型继承

### 4. 数据库迁移

- 在修改模型后及时创建和应用迁移
- 测试迁移在不同环境中的兼容性
- 保留重要的历史迁移文件

## 常见陷阱和注意事项

1. **外键关系**：注意`on_delete`参数的选择
2. **字段命名**：避免使用Django保留字
3. **null vs blank**：理解两者的区别和用途
4. **模型继承**：选择合适的继承方式（抽象基类、多表继承、代理模型）
5. **性能问题**：避免N+1查询问题
6. **并发安全**：在高并发环境下考虑数据一致性

遵循这些指南和最佳实践，可以帮助您编写高效、安全、易维护的Django模型。