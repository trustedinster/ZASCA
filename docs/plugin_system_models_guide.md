# 插件系统模型设计指南

## 概述

插件系统是ZASCA项目的重要组成部分，通过Django模型实现了插件的持久化管理和状态同步。本文档介绍插件系统模型的设计理念和实现方式。

## 插件系统模型结构

### 1. PluginRecord 模型

`PluginRecord`是插件系统的核心模型，用于在数据库中存储插件的基本信息和状态。

```python
class PluginRecord(models.Model):
    """插件记录模型"""
    
    plugin_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='插件ID',
        help_text='插件的唯一标识符'
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name='插件名称',
        help_text='插件的显示名称'
    )
    
    version = models.CharField(
        max_length=50,
        verbose_name='版本号',
        default='1.0.0',
        help_text='插件的版本号'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='描述',
        help_text='插件的功能描述'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用',
        help_text='插件是否处于启用状态'
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
        db_table = 'plugin_records'
        verbose_name = '插件'
        verbose_name_plural = '插件'
        ordering = ['-created_at']
        
    def __str__(self):
        status = "启用" if self.is_active else "禁用"
        return f"{self.name} ({self.plugin_id}) - {status}"
```

### 2. PluginConfiguration 模型

`PluginConfiguration`用于存储插件的配置参数，实现插件的可配置性。

```python
class PluginConfiguration(models.Model):
    """插件配置模型"""
    
    plugin = models.ForeignKey(
        PluginRecord,
        on_delete=models.CASCADE,
        related_name='configurations',
        verbose_name='关联插件'
    )
    
    key = models.CharField(
        max_length=255,
        verbose_name='配置键',
        help_text='配置项的键名'
    )
    
    value = models.TextField(
        verbose_name='配置值',
        help_text='配置项的值'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='描述',
        help_text='配置项的描述信息'
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
        db_table = 'plugin_configurations'
        verbose_name = '插件配置'
        verbose_name_plural = '插件配置'
        unique_together = [['plugin', 'key']]  # 确保每个插件的配置键唯一
```

## 模型设计特点

### 1. 状态同步机制

插件系统通过Django信号实现了内存状态与数据库状态的同步：

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PluginRecord
from . import plugin_manager

@receiver(post_save, sender=PluginRecord)
def sync_plugin_status_on_save(sender, instance, created, update_fields=None, **kwargs):
    """
    当插件记录保存时同步插件状态
    """
    # 检查是否更新了 is_active 字段
    if update_fields is None or 'is_active' in update_fields:
        try:
            if instance.is_active:
                plugin_manager.enable_plugin(instance.plugin_id)
            else:
                plugin_manager.disable_plugin(instance.plugin_id)
        except Exception as e:
            print(f"Error syncing plugin status on save: {str(e)}")
```

### 2. 避免循环调用

为了避免状态同步过程中的无限循环，采用了标志位机制：

```python
# 用于标记内部更新，避免信号循环
_internal_update = {}

@receiver(post_save, sender=PluginRecord)
def sync_plugin_status_on_save(sender, instance, created, update_fields=None, **kwargs):
    # 检查是否是内部更新，如果是则跳过
    key = f"{instance.plugin_id}_updating"
    if _internal_update.get(key):
        return
    # ... 同步逻辑 ...
```

### 3. 数据库操作优化

为避免触发信号，在直接更新数据库时使用`update`方法：

```python
def enable_plugin(self, plugin_id: str) -> bool:
    """启用插件"""
    if plugin_id in self.plugins:
        self.plugins[plugin_id].enabled = True
        
        # 同步到数据库（如果Django可用）
        plugin_model = self._get_plugin_model()
        if plugin_model:
            try:
                # 使用 update 方法直接更新数据库，避免触发信号
                rows_updated = plugin_model.objects.filter(plugin_id=plugin_id).update(is_active=True)
                if rows_updated > 0:
                    print(f"Database updated for plugin {plugin_id} (enabled)")
            except Exception as db_error:
                print(f"Error updating plugin status in database: {str(db_error)}")
        
        return True
    return False
```

## 插件接口设计

### 1. PluginInterface 基类

所有插件必须实现此接口：

```python
import abc
from typing import Any, Dict, List, Optional

class PluginInterface(abc.ABC):
    """插件接口定义"""
    
    def __init__(self, plugin_id: str, name: str, version: str, description: str = ""):
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.description = description
        self.enabled = True
        
    @property
    def metadata(self) -> Dict[str, Any]:
        """获取插件元数据"""
        return {
            'id': self.plugin_id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'enabled': self.enabled
        }
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abc.abstractmethod
    def shutdown(self) -> bool:
        """关闭插件"""
        pass
```

### 2. HookInterface 钩子接口

提供事件驱动机制：

```python
class HookInterface(abc.ABC):
    """钩子接口定义"""
    
    @abc.abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """执行钩子函数"""
        pass

class EventHook(HookInterface):
    """事件钩子实现"""
    
    def __init__(self, name: str):
        self.name = name
        self.handlers: List[callable] = []
        
    def register(self, handler: callable):
        """注册处理器"""
        if handler not in self.handlers:
            self.handlers.append(handler)
            
    def unregister(self, handler: callable):
        """注销处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
            
    def execute(self, *args, **kwargs) -> List[Any]:
        """执行所有注册的处理器"""
        results = []
        for handler in self.handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Error executing handler {handler.__name__}: {str(e)}")
                results.append(None)
        return results
```

## 管理界面集成

### 1. Django Admin 配置

插件系统与Django Admin深度集成：

```python
from django.contrib import admin
from .models import PluginRecord

@admin.register(PluginRecord)
class PluginAdmin(admin.ModelAdmin):
    """插件记录的管理界面"""
    
    list_display = ('plugin_id', 'name', 'version', 'description', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('plugin_id', 'name', 'description')
    readonly_fields = ('plugin_id', 'name', 'version', 'description', 'created_at')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('基本信息', {
            'fields': ('plugin_id', 'name', 'version', 'description')
        }),
        ('状态管理', {
            'fields': ('is_active',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """禁止手动添加插件记录，只能通过插件系统管理"""
        return False
        
    def has_delete_permission(self, request, obj=None):
        """禁止删除插件记录"""
        return False
        
    def save_model(self, request, obj, form, change):
        """保存模型时同步更新插件系统中的插件状态"""
        super().save_model(request, obj, form, change)
        
        # 从插件管理器获取插件并更新其状态
        from . import plugin_manager
        if obj.is_active:
            plugin_manager.enable_plugin(obj.plugin_id)
        else:
            plugin_manager.disable_plugin(obj.plugin_id)
```

### 2. 管理命令

提供同步插件状态的管理命令：

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """同步插件状态的管理命令"""
    help = 'Sync plugin records with plugin manager'

    def handle(self, *args, **options):
        from . import plugin_manager
        
        # 遍历所有已加载的插件并同步到数据库
        for plugin in plugin_manager.get_all_plugins():
            plugin_record, created = PluginRecord.objects.get_or_create(
                plugin_id=plugin.plugin_id,
                defaults={
                    'name': plugin.name,
                    'version': plugin.version,
                    'description': plugin.description,
                    'is_active': plugin.enabled
                }
            )
            
            if not created:
                # 更新现有记录
                plugin_record.name = plugin.name
                plugin_record.version = plugin.version
                plugin_record.description = plugin.description
                plugin_record.is_active = plugin.enabled
                plugin_record.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully synced {len(plugin_manager.get_all_plugins())} plugins')
        )
```

## 示例插件实现

### 1. 认证插件

```python
from plugins.core.base import PluginInterface


class DemoAuthPlugin(PluginInterface):
    """演示认证插件"""

    def __init__(self):
        super().__init__(
            plugin_id="demo_auth_plugin",
            name="Demo Authentication Plugin",
            version="1.0.0",
            description="演示如何在Django项目中集成认证插件"
        )
        self.users = {}
        self.active_sessions = {}

    def initialize(self) -> bool:
        print(f"初始化 {self.name}")
        self.users = {
            "admin": "secret123",
            "user": "password123",
            "guest": "guest123"
        }
        return True

    def shutdown(self) -> bool:
        print(f"关闭 {self.name}")
        self.active_sessions.clear()
        return True

    def authenticate(self, username: str, password: str) -> dict:
        """认证用户"""
        if username in self.users and self.users[username] == password:
            session_id = f"session_{username}_{hash(password)}"
            self.active_sessions[session_id] = {
                'username': username,
                'authenticated_at': __import__('datetime').datetime.now().isoformat()
            }
            return {
                'success': True,
                'session_id': session_id,
                'user': {'username': username}
            }
        else:
            return {
                'success': False,
                'error': 'Invalid credentials'
            }
```

## 最佳实践

### 1. 模型设计原则

- **单一职责**：每个模型应有明确的职责
- **数据一致性**：确保内存状态与数据库状态一致
- **性能优化**：合理使用索引和查询优化
- **安全性**：保护敏感配置信息

### 2. 插件开发规范

- **接口一致性**：遵循PluginInterface规范
- **错误处理**：妥善处理异常情况
- **资源管理**：正确管理插件生命周期
- **配置管理**：支持可配置的插件行为

### 3. 集成注意事项

- **信号处理**：避免无限循环调用
- **事务管理**：确保数据一致性
- **并发安全**：考虑多线程环境下的安全问题
- **版本兼容**：处理插件版本升级

通过这种设计，插件系统能够在保持灵活性的同时，确保与Django框架的良好集成，为系统提供强大的扩展能力。