# Django模型关系与查询优化指南

## 概述

本文档基于ZASCA项目中的实际模型关系，介绍Django模型之间的关系设计和查询优化的最佳实践。

## 模型关系详解

### 1. ForeignKey (一对多关系)

#### 基本用法

```python
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Host(models.Model):
    name = models.CharField(max_length=100, verbose_name='主机名称')
    # 创建者与用户模型关联
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # 当用户被删除时，设置为NULL
        null=True,
        blank=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
```

#### 反向关系

```python
# 在User模型上可以通过related_name访问相关主机
# user.host_set.all()  # 使用默认的反向关系名
# 如果设置了related_name='created_hosts'，则使用：
# user.created_hosts.all()

class User(AbstractUser):
    # 自定义用户模型
    pass

# 查询示例
def get_user_hosts(user_id):
    user = User.objects.get(id=user_id)
    # 使用反向关系查询用户创建的所有主机
    hosts = user.created_hosts.all()  # 假设related_name='created_hosts'
    return hosts
```

### 2. OneToOneField (一对一关系)

```python
class User(models.Model):
    username = models.CharField(max_length=100)

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',  # 通过user.profile访问
        verbose_name='用户'
    )
    nickname = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)

# 使用示例
def get_user_profile(user_id):
    user = User.objects.get(id=user_id)
    profile = user.profile  # 直接访问，不需要.all()
    return profile
```

### 3. ManyToManyField (多对多关系)

```python
class Host(models.Model):
    name = models.CharField(max_length=100)

class HostGroup(models.Model):
    name = models.CharField(max_length=100)
    # 主机与主机组的多对多关系
    hosts = models.ManyToManyField(
        Host,
        blank=True,
        verbose_name='主机'
    )
```

### 4. 复杂关系示例 (ZASCA项目)

```python
# 产品模型 - 连接主机和云电脑用户
class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name='产品名称')
    # 关联主机
    host = models.ForeignKey(
        'hosts.Host',  # 引用其他应用的模型
        on_delete=models.CASCADE,
        verbose_name='关联主机'
    )
    is_available = models.BooleanField(default=True, verbose_name='是否可用')

# 云电脑用户模型
class CloudComputerUser(models.Model):
    username = models.CharField(max_length=150, verbose_name='用户名')
    # 关联产品
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='所属产品'
    )
    # 关联开户申请
    created_from_request = models.ForeignKey(
        'AccountOpeningRequest',  # 另一个模型
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='来源申请'
    )

# 开户申请模型
class AccountOpeningRequest(models.Model):
    # 申请人
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account_opening_requests',
        verbose_name='申请人'
    )
    # 目标产品
    target_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='目标产品',
        null=True,
        blank=True
    )
```

## 查询优化技术

### 1. select_related (正向外键查询优化)

```python
# 低效查询 - N+1问题
def get_hosts_with_creator_naive():
    hosts = Host.objects.all()
    for host in hosts:
        print(host.created_by.username)  # 每次循环都查询数据库

# 优化查询 - 使用select_related
def get_hosts_with_creator_optimized():
    # 一次性JOIN查询，避免N+1问题
    hosts = Host.objects.select_related('created_by').all()
    for host in hosts:
        print(host.created_by.username)  # 不需要额外查询
```

### 2. prefetch_related (反向外键和多对多查询优化)

```python
# 低效查询
def get_host_groups_with_hosts_naive():
    groups = HostGroup.objects.all()
    for group in groups:
        for host in group.hosts.all():  # 每次循环都查询数据库
            print(host.name)

# 优化查询 - 使用prefetch_related
def get_host_groups_with_hosts_optimized():
    # 一次性查询所有相关主机，避免N+1问题
    groups = HostGroup.objects.prefetch_related('hosts').all()
    for group in groups:
        for host in group.hosts.all():  # 从缓存中获取
            print(host.name)
```

### 3. 复杂查询优化示例 (ZASCA项目)

```python
# 获取用户及其开户申请和关联的产品信息
def get_user_applications_with_details(user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # 复杂查询优化
    applications = AccountOpeningRequest.objects.select_related(
        'applicant',           # 申请人信息
        'target_product',      # 目标产品
        'target_product__host', # 产品关联的主机
        'approved_by'          # 审核人信息
    ).prefetch_related(
        'target_product__cloudcomputeruser_set'  # 产品下的云电脑用户
    ).filter(applicant_id=user_id)
    
    return applications

# 获取产品及其所有相关信息
def get_product_with_all_relations(product_id):
    product = Product.objects.select_related(
        'host'                 # 关联主机
    ).prefetch_related(
        'cloudcomputeruser_set',      # 产品下的云电脑用户
        'accountopeningrequest_set'   # 相关的开户申请
    ).get(id=product_id)
    
    return product
```

## 数据库索引策略

### 1. 单字段索引

```python
class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),           # 查询用户活动时优化
            models.Index(fields=['activity_type']),  # 按活动类型筛选时优化
            models.Index(fields=['ip_address']),     # 按IP地址查询时优化
            models.Index(fields=['created_at']),     # 按时间排序时优化
        ]
```

### 2. 复合索引

```python
class SystemStats(models.Model):
    STATS_TYPES = (
        ('user_count', '用户数量'),
        ('host_count', '主机数量'),
    )
    
    stats_type = models.CharField(max_length=50, choices=STATS_TYPES)
    stats_value = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['stats_type', 'created_at']),  # 按类型和时间查询时优化
            models.Index(fields=['created_at', 'stats_type']),  # 按时间范围和类型查询时优化
        ]
```

### 3. 降序索引

```python
class SystemTask(models.Model):
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),     # 按最新时间倒序查询优化
            models.Index(fields=['status', '-created_at']),  # 按状态和最新时间查询优化
        ]
```

## 高级查询技巧

### 1. Q对象复杂查询

```python
from django.db.models import Q

def search_hosts(search_term):
    """搜索主机，支持名称和主机名模糊匹配"""
    hosts = Host.objects.filter(
        Q(name__icontains=search_term) | 
        Q(hostname__icontains=search_term)
    )
    return hosts

def get_active_products_by_user_or_host(user_id, host_ids):
    """获取用户创建或在指定主机上的可用产品"""
    products = Product.objects.filter(
        Q(host__created_by_id=user_id) | 
        Q(host_id__in=host_ids),
        is_available=True
    ).select_related('host')
    return products
```

### 2. F表达式更新

```python
from django.db.models import F

def increment_host_stats(host_id):
    """增加主机统计信息"""
    Host.objects.filter(id=host_id).update(
        connection_count=F('connection_count') + 1
    )
```

### 3. 聚合查询

```python
from django.db.models import Count, Avg, Sum

def get_system_statistics():
    """获取系统统计信息"""
    stats = {
        'total_users': User.objects.count(),
        'total_hosts': Host.objects.count(),
        'active_hosts': Host.objects.filter(status='online').count(),
        'hosts_by_type': Host.objects.values('host_type').annotate(
            count=Count('id')
        ),
        'products_by_host': Host.objects.annotate(
            product_count=Count('product')
        ).filter(product_count__gt=0)
    }
    return stats
```

## 性能监控和调试

### 1. 查询调试

```python
# 启用查询日志
import logging
logging.basicConfig()
logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

# 或在settings.py中配置
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    }
}
```

### 2. 查询优化检查

```python
from django.db import connection
from django.conf import settings

def debug_queries(view_func):
    """装饰器：打印视图执行的查询"""
    def wrapper(*args, **kwargs):
        initial_queries = len(connection.queries)
        result = view_func(*args, **kwargs)
        total_queries = len(connection.queries)
        
        print(f"Queries executed: {total_queries - initial_queries}")
        for query in connection.queries[initial_queries:]:
            print(query['sql'])
        
        return result
    return wrapper
```

## 实际项目应用示例

### 1. 用户活动跟踪查询优化

```python
class UserActivity(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name='用户'
    )
    activity_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '用户活动'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', '-created_at']),  # 常见查询模式优化
        ]

def get_user_recent_activities(user_id, days=7):
    """获取用户近期活动"""
    from datetime import timedelta
    from django.utils import timezone
    
    since_date = timezone.now() - timedelta(days=days)
    
    activities = UserActivity.objects.select_related(
        'user'
    ).filter(
        user_id=user_id,
        created_at__gte=since_date
    ).order_by('-created_at')[:50]  # 限制结果数量
    
    return activities
```

### 2. 系统任务查询优化

```python
class SystemTask(models.Model):
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20)
    progress = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['created_by', 'status']),  # 常见联合查询优化
        ]

def get_pending_tasks_for_user(user_id):
    """获取用户的待处理任务"""
    tasks = SystemTask.objects.filter(
        created_by_id=user_id,
        status='pending'
    ).select_related('created_by').order_by('-created_at')
    
    return tasks
```

## 最佳实践总结

1. **避免N+1查询**：使用`select_related`和`prefetch_related`
2. **合理使用索引**：为经常查询的字段创建索引
3. **限制查询结果**：使用`[:limit]`限制结果数量
4. **批量操作**：使用`bulk_create`、`bulk_update`进行批量操作
5. **查询分析**：定期检查慢查询日志
6. **缓存策略**：对频繁查询的数据使用缓存
7. **数据库设计**：合理的范式设计减少冗余查询

通过遵循这些最佳实践，可以显著提高Django应用的数据库查询性能，提升用户体验。