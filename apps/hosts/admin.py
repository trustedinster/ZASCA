"""
主机管理后台配置
"""
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from .models import Host, HostGroup
import uuid
from datetime import timedelta
from django.utils import timezone


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

    class Media:
        js = ('/static/admin/js/bootstrap-deploy-button.js',)
        css = {
            'all': ('/static/admin/css/bootstrap-deploy-button.css',)
        }

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/generate-deploy-command/', 
                 self.admin_site.admin_view(self.generate_deploy_command), 
                 name='hosts_host_generate_deploy_command'),
        ]
        return custom_urls + urls

    def generate_deploy_command(self, request, object_id):
        """生成部署命令"""
        from django.contrib.auth.models import User
        try:
            host = Host.objects.get(pk=object_id)
            
            # 检查或创建初始令牌
            from apps.bootstrap.models import InitialToken
            import secrets
            
            # 生成新的初始令牌
            token = secrets.token_urlsafe(32)  # 生成安全的随机令牌
            expires_at = timezone.now() + timedelta(hours=24)
            
            initial_token, created = InitialToken.objects.get_or_create(
                token=token,
                defaults={
                    'host': host,
                    'expires_at': expires_at,
                    'status': 'ISSUED'
                }
            )
            
            # 构建secret数据
            from django.conf import settings
            import json
            import base64
            
            # 获取当前站点的基础URL
            current_site = request.build_absolute_uri('/')
            
            secret_data = {
                "c_side_url": current_site.rstrip('/'),
                "token": initial_token.token,
                "host_id": str(host.id),
                "hostname": host.hostname,
                "generated_at": timezone.now().isoformat(),
                "expires_at": initial_token.expires_at.isoformat()
            }
            
            # 转换为JSON并进行base64编码
            json_str = json.dumps(secret_data)
            encoded_bytes = base64.b64encode(json_str.encode('utf-8'))
            encoded_str = encoded_bytes.decode('utf-8')
            
            deploy_command = f".\h_side_init.exe \"{encoded_str}\""
            
            return JsonResponse({
                'success': True,
                'deploy_command': deploy_command,
                'secret': encoded_str,
                'expires_at': initial_token.expires_at.isoformat(),
                'message': f'{"新" if created else "现有"}引导令牌已生成，将在24小时后过期'
            })
            
        except Host.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '主机不存在'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """重写change_view以添加额外上下文"""
        extra_context = extra_context or {}
        extra_context['show_deploy_button'] = True
        return super().change_view(request, object_id, form_url, extra_context)

    def deploy_command_button(self, obj):
        """部署命令按钮"""
        if obj:
            button_html = format_html(
                '<button type="button" class="btn btn-outline-primary" id="get-deploy-command-btn" '
                'data-host-id="{}" onclick="showDeployCommand({}, \'{}\')">获取部署命令</button>',
                obj.pk, obj.pk, obj.name
            )
            return button_html
        return ""
    
    deploy_command_button.short_description = "部署操作"

    def save_model(self, request, obj, form, change):
        """
        重写save_model方法，确保每次保存时都会测试连接
        """
        # 如果提供了新密码，则使用setter更新加密存储
        # 注意：这里再次处理密码是为了确保即使在Admin中也能正确加密存储
        if form.cleaned_data.get('password'):
            obj.password = form.cleaned_data['password']
        
        # 调用父类方法保存模型
        super().save_model(request, obj, form, change)
        
        # 测试连接
        # 对于新主机，执行连接测试
        # 对于现有主机，如果密码被更新了，也执行连接测试以验证密码是否有效
        should_test_connection = not change  # 新增主机
        if change and 'password' in form.changed_data:  # 更新主机且密码被修改
            should_test_connection = True
        
        if should_test_connection:
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