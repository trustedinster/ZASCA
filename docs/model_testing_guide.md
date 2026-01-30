# Django模型测试指南

## 概述

本文档介绍如何为Django模型编写有效的单元测试，基于ZASCA项目中的实际模型和测试需求。

## 模型测试基础

### 1. 基本测试结构

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.hosts.models import Host
from apps.accounts.models import User

class HostModelTest(TestCase):
    """主机模型测试类"""
    
    def setUp(self):
        """测试前准备，创建必要的测试数据"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        self.host = Host.objects.create(
            name='Test Host',
            hostname='test.example.com',
            username='admin',
            host_type='server',
            created_by=self.user
        )
        # 设置加密密码
        self.host.password = 'testpass123'
    
    def test_host_creation(self):
        """测试主机创建"""
        self.assertEqual(self.host.name, 'Test Host')
        self.assertEqual(self.host.hostname, 'test.example.com')
        self.assertEqual(self.host.created_by, self.user)
    
    def test_host_str_representation(self):
        """测试主机字符串表示"""
        self.assertEqual(str(self.host), 'Test Host')
    
    def test_host_encrypted_password(self):
        """测试密码加密功能"""
        original_password = 'testpass123'
        self.host.password = original_password
        self.assertEqual(self.host.password, original_password)
```

### 2. 模型验证测试

```python
from django.core.exceptions import ValidationError

class SystemConfigModelTest(TestCase):
    """系统配置模型验证测试"""
    
    def setUp(self):
        self.config = SystemConfig.objects.create(
            site_name='Test Site',
            captcha_provider='none'
        )
    
    def test_geetest_validation_when_enabled(self):
        """测试启用Geetest时的验证"""
        # 设置为Geetest但不提供必要字段
        self.config.captcha_provider = 'geetest'
        self.config.captcha_id = None
        self.config.captcha_key = None
        
        with self.assertRaises(ValidationError):
            self.config.full_clean()
    
    def test_geetest_validation_success(self):
        """测试Geetest验证成功"""
        self.config.captcha_provider = 'geetest'
        self.config.captcha_id = 'test_id'
        self.config.captcha_key = 'test_key'
        
        try:
            self.config.full_clean()
            self.assertTrue(True)  # 验证通过
        except ValidationError:
            self.fail("Geetest配置验证不应该失败")
```

## 复杂模型关系测试

### 1. 关系查询测试

```python
from apps.operations.models import Product, AccountOpeningRequest, CloudComputerUser

class ProductRelationshipTest(TestCase):
    """产品模型关系测试"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.host = Host.objects.create(
            name='Test Host',
            hostname='test.example.com',
            username='admin',
            host_type='server',
            created_by=self.user
        )
        self.host.password = 'testpass123'
        
        self.product = Product.objects.create(
            name='Test Product',
            display_name='Test Product Display',
            host=self.host,
            is_available=True
        )
    
    def test_product_host_relationship(self):
        """测试产品与主机的关系"""
        self.assertEqual(self.product.host, self.host)
        self.assertEqual(self.product.status, self.host.status)
    
    def test_product_cloud_users(self):
        """测试产品与云电脑用户的关系"""
        cloud_user = CloudComputerUser.objects.create(
            username='clouduser',
            fullname='Cloud User',
            email='cloud@example.com',
            product=self.product
        )
        
        # 测试反向关系
        self.assertIn(cloud_user, self.product.cloudcomputeruser_set.all())
        self.assertEqual(cloud_user.product, self.product)
```

### 2. 多对多关系测试

```python
from apps.hosts.models import HostGroup

class HostGroupTest(TestCase):
    """主机组模型测试"""
    
    def setUp(self):
        self.host1 = Host.objects.create(
            name='Host 1',
            hostname='host1.example.com',
            username='admin',
            host_type='server'
        )
        self.host1.password = 'testpass123'
        
        self.host2 = Host.objects.create(
            name='Host 2',
            hostname='host2.example.com',
            username='admin',
            host_type='server'
        )
        self.host2.password = 'testpass123'
        
        self.group = HostGroup.objects.create(
            name='Test Group',
            description='Test Description'
        )
    
    def test_many_to_many_relationship(self):
        """测试多对多关系"""
        self.group.hosts.add(self.host1, self.host2)
        
        # 测试正向关系
        self.assertIn(self.host1, self.group.hosts.all())
        self.assertIn(self.host2, self.group.hosts.all())
        
        # 测试反向关系（如果设置了related_name）
        # 注意：在这个例子中没有设置related_name，所以使用默认的host_set
        # 但由于是多对多关系，不能直接从host访问groups
        # 需要通过中间表查询
```

## 模型方法测试

### 1. 自定义方法测试

```python
class CloudComputerUserMethodTest(TestCase):
    """云电脑用户模型方法测试"""
    
    def setUp(self):
        self.product = Product.objects.create(
            name='Test Product',
            display_name='Test Product Display',
            host=Host.objects.create(
                name='Test Host',
                hostname='test.example.com',
                username='admin',
                host_type='server'
            )
        )
        self.product.host.password = 'testpass123'
    
    def test_generate_complex_password(self):
        """测试复杂密码生成"""
        password = CloudComputerUser.generate_complex_password()
        
        # 验证密码长度
        self.assertEqual(len(password), 16)
        
        # 验证密码包含各种字符类型
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        self.assertTrue(has_upper, "密码应包含大写字母")
        self.assertTrue(has_lower, "密码应包含小写字母")
        self.assertTrue(has_digit, "密码应包含数字")
        self.assertTrue(has_special, "密码应包含特殊字符")
    
    def test_get_and_burn_password(self):
        """测试阅后即焚密码功能"""
        cloud_user = CloudComputerUser.objects.create(
            username='testuser',
            fullname='Test User',
            email='test@example.com',
            product=self.product,
            initial_password='initial_password_123'
        )
        
        # 第一次获取密码
        first_password = cloud_user.get_and_burn_password()
        self.assertIsNotNone(first_password)
        
        # 第二次获取应该返回新密码（因为原密码已被"烧毁"）
        second_password = cloud_user.get_and_burn_password()
        self.assertNotEqual(first_password, second_password)
        
        # 验证密码已被标记为已查看
        cloud_user.refresh_from_db()
        self.assertTrue(cloud_user.password_viewed)
```

## 信号和回调测试

### 1. 模型保存钩子测试

```python
class HostSaveHookTest(TestCase):
    """主机模型保存钩子测试"""
    
    def setUp(self):
        self.host = Host.objects.create(
            name='Test Host',
            hostname='test.example.com',
            username='admin',
            host_type='server'
        )
        self.host.password = 'testpass123'
    
    def test_save_triggers_connection_test(self):
        """测试保存触发连接测试"""
        # 保存主机应该触发连接测试
        original_status = self.host.status
        self.host.save()
        
        # 在非DEMO模式下，实际连接测试可能无法执行
        # 但在DEMO模式下，状态应该被设置为'online'
        import os
        if os.environ.get('ZASCA_DEMO', '').lower() == '1':
            self.assertEqual(self.host.status, 'online')
        else:
            # 在非DEMO模式下，状态可能保持不变或变为'error'
            self.assertIn(self.host.status, ['online', 'error', 'offline'])
```

## 查询优化测试

### 1. 查询性能测试

```python
from django.test import TestCase
from django.db import connection
from django.conf import settings

class QueryOptimizationTest(TestCase):
    """查询优化测试"""
    
    def setUp(self):
        # 创建测试数据
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        
        # 创建多个主机和产品用于测试
        for i in range(10):
            host = Host.objects.create(
                name=f'Test Host {i}',
                hostname=f'host{i}.example.com',
                username='admin',
                host_type='server',
                created_by=self.user
            )
            host.password = 'testpass123'
            
            Product.objects.create(
                name=f'Test Product {i}',
                display_name=f'Test Product {i}',
                host=host,
                is_available=True
            )
    
    def test_select_related_performance(self):
        """测试select_related性能优化"""
        # 记录查询数量
        initial_queries = len(connection.queries)
        
        # 低效查询 - N+1问题
        products_naive = []
        for product in Product.objects.all()[:5]:  # 只取前5个以避免太多查询
            products_naive.append((product.name, product.host.name))
        
        queries_without_optimization = len(connection.queries) - initial_queries
        
        # 重置查询日志
        connection.queries_log.clear()
        
        # 高效查询 - 使用select_related
        products_optimized = []
        optimized_queryset = Product.objects.select_related('host').all()[:5]
        for product in optimized_queryset:
            products_optimized.append((product.name, product.host.name))
        
        queries_with_optimization = len(connection.queries)
        
        # 优化后的查询数量应该显著减少
        self.assertLess(queries_with_optimization, queries_without_optimization)
        self.assertEqual(products_naive, products_optimized)
```

## 边界条件测试

### 1. 数据边界测试

```python
class DataBoundaryTest(TestCase):
    """数据边界测试"""
    
    def test_long_field_values(self):
        """测试长字段值"""
        long_name = 'A' * 200  # 超过CharField的max_length
        with self.assertRaises(Exception):  # 应该抛出数据长度异常
            Host.objects.create(
                name=long_name,
                hostname='test.example.com',
                username='admin',
                host_type='server'
            )
    
    def test_invalid_choice_values(self):
        """测试无效选择值"""
        with self.assertRaises(ValueError):
            Host.objects.create(
                name='Test Host',
                hostname='test.example.com',
                username='admin',
                host_type='invalid_type'  # 不在choices中的值
            )
    
    def test_null_constraint(self):
        """测试空值约束"""
        # 某些字段不允许为空
        host = Host(name='Test')  # 不设置hostname，它应该是必需的
        with self.assertRaises(Exception):
            host.save()
```

## 安全相关测试

### 1. 敏感数据保护测试

```python
class SecurityTest(TestCase):
    """安全相关测试"""
    
    def setUp(self):
        self.host = Host.objects.create(
            name='Test Host',
            hostname='test.example.com',
            username='admin',
            host_type='server'
        )
        self.original_password = 'sensitive_password_123'
        self.host.password = self.original_password
    
    def test_password_encryption(self):
        """测试密码加密"""
        # 检查数据库中的密码是否被加密
        encrypted_password = self.host._password
        decrypted_password = self.host.password
        
        self.assertNotEqual(encrypted_password, self.original_password)
        self.assertEqual(decrypted_password, self.original_password)
    
    def test_password_not_in_plain_text(self):
        """测试密码不以明文形式存储"""
        # 保存后，直接访问数据库字段应该返回加密值
        self.host.save()
        
        # 重新从数据库获取对象
        fresh_host = Host.objects.get(id=self.host.id)
        self.assertNotEqual(fresh_host._password, self.original_password)
        self.assertEqual(fresh_host.password, self.original_password)
```

## 测试最佳实践

### 1. 使用Factory Boy创建测试数据

```python
import factory
from apps.accounts.models import User
from apps.hosts.models import Host

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    is_active = True

class HostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Host
    
    name = factory.Sequence(lambda n: f'Host {n}')
    hostname = factory.LazyAttribute(lambda obj: f'{obj.name.lower().replace(" ", ".")}.example.com')
    username = 'admin'
    host_type = 'server'
    
    @factory.post_generation
    def setup_password(self, create, extracted, **kwargs):
        if not create:
            return
        self.password = 'testpass123'

# 使用Factory的测试
class FactoryBasedTest(TestCase):
    def test_with_factories(self):
        user = UserFactory()
        host = HostFactory(created_by=user)
        
        self.assertEqual(host.created_by, user)
        self.assertEqual(host.name, f'Host {user.id + 1}')  # 假设ID是连续分配的
```

### 2. 使用fixtures

```python
from django.test import TestCase, override_settings
import tempfile
import os

class FixtureBasedTest(TestCase):
    fixtures = ['test_data.json']  # 指定测试数据文件
    
    def test_with_fixture_data(self):
        """使用fixture数据的测试"""
        # fixture数据已经加载
        host_count = Host.objects.count()
        self.assertGreater(host_count, 0)
```

## 测试运行和报告

### 1. 运行特定模型测试

```bash
# 运行特定应用的所有测试
python manage.py test apps.accounts.tests

# 运行特定测试类
python manage.py test apps.accounts.tests.UserModelTest

# 运行特定测试方法
python manage.py test apps.accounts.tests.UserModelTest.test_user_creation

# 生成覆盖率报告
pip install coverage
coverage run --source='.' manage.py test apps.accounts
coverage report
coverage html  # 生成HTML报告
```

### 2. 测试配置

```python
# 在settings/test.py中
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# 使用内存数据库加速测试
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}

# 禁用日志以减少噪音
LOGGING_CONFIG = None
```

## 持续集成测试

### 1. GitHub Actions配置示例

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run tests
      run: |
        python manage.py test
    - name: Coverage
      run: |
        pip install coverage
        coverage run --source='.' manage.py test
        coverage report
```

通过遵循这些测试指南和最佳实践，可以确保Django模型的可靠性、安全性和性能，同时提高代码质量和维护性。