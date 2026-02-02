"""
插件系统的Django Admin配置
为每个插件提供管理界面，允许在Django后台管理插件状态
"""

from django.contrib import admin
from .models import QQVerificationConfig


@admin.register(QQVerificationConfig)
class QQVerificationConfigAdmin(admin.ModelAdmin):
    """
    QQ验证配置的Django Admin管理界面
    """
    list_display = [
        'product', 
        'host', 
        'port', 
        'group_id', 
        'enable_status', 
        'non_qq_email_handling', 
        'created_at'
    ]
    list_filter = [
        'enable_status', 
        'non_qq_email_handling', 
        'created_at',
        'product__name'  # 按产品名称过滤
    ]
    search_fields = [
        'product__name', 
        'product__display_name', 
        'host', 
        'group_id'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本配置', {
            'fields': ('product', 'host', 'port', 'token', 'group_id')
        }),
        ('功能配置', {
            'fields': ('enable_status', 'non_qq_email_handling')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        自定义外键字段的表单控件
        """
        if db_field.name == "product":
            # 可以在这里添加额外的筛选条件
            # 例如，只显示某些产品的选项
            pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# 如果需要为每个插件类型创建单独的管理界面，可以使用工厂函数
def create_plugin_admin(plugin_class):
    """
    为特定插件类型创建管理界面的工厂函数
    """
    class SpecificPluginAdmin(PluginAdmin):
        list_display = ('plugin_id', 'name', 'version', 'description', 'is_active', 'updated_at')
        
        def get_queryset(self, request):
            qs = super().get_queryset(request)
            return qs.filter(plugin_id__startswith=plugin_class.__name__.lower())
    
    # 动态注册管理类
    admin.site.register(type(
        f"{plugin_class.__name__}AdminModel",
        (PluginRecord,),
        {
            '__module__': __name__,
            'Meta': type('Meta', (), {
                'proxy': True,
                'verbose_name': f'{plugin_class.__name__} Plugin',
                'verbose_name_plural': f'{plugin_class.__name__} Plugins',
            })
        }
    ), SpecificPluginAdmin)


# 创建一个命令来同步插件状态
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    同步插件状态的管理命令
    """
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