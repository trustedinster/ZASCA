"""
主机管理后台配置
"""
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Host, HostGroup


class HostAdminForm(forms.ModelForm):
    """自定义Host表单，用于处理密码字段"""
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        required=False,
        help_text="留空则不修改密码",
        label="密码"
    )

    class Meta:
        model = Host
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 如果编辑现有对象，清空密码字段，不显示原密码
        if self.instance.pk:
            self.fields['password'].help_text = "留空则不修改密码。为安全起见，此处不显示原密码。"

    def save(self, commit=True):
        # 如果提供了新密码，则使用setter更新加密存储
        if self.cleaned_data.get('password'):
            self.instance.password = self.cleaned_data['password']
        return super().save(commit)


@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    """主机管理后台"""

    form = HostAdminForm
    list_display = ('name', 'hostname', 'port', 'username', 'host_type', 'status', 'created_at')
    list_filter = ('status', 'host_type', 'created_at', 'use_ssl')
    search_fields = ('name', 'hostname', 'username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'hostname', 'connection_type', 'port', 'rdp_port', 'use_ssl')
        }),
        ('认证信息', {
            'fields': ('username', 'password'),
            'description': '请输入主机的认证信息'
        }),
        ('主机信息', {
            'fields': ('host_type', 'os_version', 'status', 'description')
        }),
        ('创建信息', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        重写save_model方法，确保每次保存时都会测试连接
        """
        # 调用父类方法保存模型
        super().save_model(request, obj, form, change)
        # 测试连接
        try:
            obj.test_connection()
            messages.success(request, f"主机 {obj.name} 保存成功，状态已更新为 {dict(obj.STATUS_CHOICES)[obj.status]}")
        except Exception as e:
            messages.warning(request, f"主机 {obj.name} 保存成功，但连接测试失败: {str(e)}")

    def delete_model(self, request, obj):
        """
        重写delete_model方法，确保删除主机前处理相关联的对象
        """
        # 导入相关模型
        from apps.operations.models import Product, PublicHostInfo
        
        # 删除关联的 Product 对象
        Product.objects.filter(host=obj).delete()
        
        # 删除关联的 PublicHostInfo 对象
        PublicHostInfo.objects.filter(internal_host=obj).delete()
        
        # 删除主机本身
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """
        重写delete_queryset方法，处理批量删除时的外键约束问题
        """
        from apps.operations.models import Product, PublicHostInfo
        
        # 逐个处理每个要删除的主机，确保先删除相关联的对象
        for obj in queryset:
            # 删除关联的 Product 对象
            Product.objects.filter(host=obj).delete()
            
            # 删除关联的 PublicHostInfo 对象
            PublicHostInfo.objects.filter(internal_host=obj).delete()
        
        # 执行批量删除
        super().delete_queryset(request, queryset)


@admin.register(HostGroup)
class HostGroupAdmin(admin.ModelAdmin):
    """主机组管理后台"""

    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('hosts',)

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description')
        }),
        ('主机', {
            'fields': ('hosts',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )