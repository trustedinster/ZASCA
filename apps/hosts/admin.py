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
        widget=forms.PasswordInput(),
        required=False,
        help_text="留空则不修改密码"
    )

    class Meta:
        model = Host
        fields = '__all__'

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
            'fields': ('name', 'hostname', 'port', 'rdp_port', 'use_ssl')
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