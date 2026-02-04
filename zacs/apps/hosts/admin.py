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

    def name_display(self, obj):
        """显示主机名称带颜色标识"""
        color_map = {
            'online': '#10b981',
            'offline': '#ef4444',
            'error': '#f59e0b'
        }
        color = color_map.get(obj.status, '#6b7280')
        return format_html(
            '<span style="color: {}">{}</span>',
            color,
            obj.name
        )
    name_display.short_description = '名称'

    def status_display(self, obj):
        """显示状态带图标"""
        status_map = {
            'online': ('🟢', '在线'),
            'offline': ('🔴', '离线'),
            'error': ('🟡', '错误')
        }
        icon, text = status_map.get(obj.status, ('⚪', obj.get_status_display()))
        return format_html('{} <strong>{}</strong>', icon, text)
    status_display.short_description = '状态'

    def ssl_badge(self, obj):
        """显示SSL状态图标"""
        if obj.use_ssl:
            return format_html('<span class="badge bg-success">🔒 SSL</span>')
        return format_html('<span class="badge bg-secondary">HTTP</span>')
    ssl_badge.short_description = 'SSL'

    def cert_validation(self, obj):
        """显示证书验证状态"""
        if obj.use_ssl:
            if obj.server_cert_validation == 'validate':
                return format_html('<span class="text-success">✓ 验证</span>')
            return format_html('<span class="text-warning">⚠ 忽略</span>')
        return '-'
    cert_validation.short_description = '证书验证'

    def password_encrypted(self, obj):
        """显示密码已加密"""
        return format_html('<span class="text-muted">🔐 已加密存储</span>')
    password_encrypted.short_description = '密码状态'

    # 新增的管理动作
    @admin.action(description='批量测试连接')
    def test_connections(self, request, queryset):
        """批量测试主机连接"""
        success_count = 0
        error_count = 0

        for host in queryset:
            try:
                result = host.test_connection()
                if result and result.success:
                    success_count += 1
                    host.status = 'online'
                    host.last_test_timestamp = timezone.now()
                    host.last_test_result = 'Connection successful'
                else:
                    error_count += 1
                    host.status = 'error'
                    host.last_test_timestamp = timezone.now()
                    host.last_test_result = result.std_err if result else 'Connection failed'
                host.save()
            except Exception as e:
                error_count += 1
                host.status = 'error'
                host.last_test_timestamp = timezone.now()
                host.last_test_result = str(e)
                host.save()
                self.message_user(request, f"主机 {host.name} 测试失败: {str(e)}", messages.WARNING)

        self.message_user(
            request,
            f'连接测试完成，成功: {success_count}，失败: {error_count}/{queryset.count()}',
            messages.SUCCESS if success_count > 0 else messages.WARNING
        )

    @admin.action(description='启用SSL加密')
    def enable_ssl(self, request, queryset):
        """启用SSL加密"""
        updated = queryset.update(use_ssl=True)
        self.message_user(request, f'已为 {updated} 台主机启用SSL加密', messages.SUCCESS)

    @admin.action(description='禁用SSL')
    def disable_ssl(self, request, queryset):
        """禁用SSL连接"""
        updated = queryset.update(use_ssl=False, server_cert_validation='ignore')
        self.message_user(request, f'已为 {updated} 台主机禁用SSL', messages.WARNING)

    @admin.action(description='启用证书验证')
    def enable_cert_validation(self, request, queryset):
        """启用证书验证"""
        ssl_hosts = queryset.filter(use_ssl=True)
        updated = ssl_hosts.update(server_cert_validation='validate')

        if updated > 0:
            self.message_user(request, f'已为 {updated} 台启用SSL的主机启用证书验证', messages.SUCCESS)

        # 警告没有启用SSL的主机
        no_ssl_count = queryset.filter(use_ssl=False).count()
        if no_ssl_count > 0:
            self.message_user(request, f'警告: 有 {no_ssl_count} 台主机未启用SSL，证书验证无效', messages.WARNING)

    @admin.action(description='导出主机清单')
    def export_host_list(self, request, queryset):
        """导出主机列表为CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="hosts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', '名称', '主机地址', '连接类型', '主机类型', '状态', 'SSL',
            '证书验证', '端口', 'RDP端口', 'OS版本', '创建时间',
            '最后测试时间', '最后测试结果', '创建者', '备注'
        ])

        for host in queryset:
            writer.writerow([
                host.id, host.name, host.hostname, host.get_connection_type_display(),
                host.get_host_type_display(), host.get_status_display(),
                '启用' if host.use_ssl else '禁用', host.get_server_cert_validation_display(),
                host.port, host.rdp_port, host.os_version,
                host.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                host.last_test_timestamp.strftime('%Y-%m-%d %H:%M:%S') if host.last_test_timestamp else '',
                host.last_test_result or '',
                host.created_by.username if host.created_by else '',
                host.description
            ])

        self.message_user(request, f'已导出 {queryset.count()} 台主机清单', messages.SUCCESS)
        return response

    def last_status_check(self, obj):
        """显示最后状态检查时间"""
        if obj.last_test_timestamp:
            now = timezone.now()
            diff = now - obj.last_test_timestamp
            if diff < timedelta(minutes=1):
                return '刚刚'
            elif diff < timedelta(hours=1):
                return f'{int(diff.total_seconds() / 60)} 分钟前'
            elif diff < timedelta(days=1):
                return f'{int(diff.total_seconds() / 3600)} 小时前'
            else:
                return obj.last_test_timestamp.strftime('%Y-%m-%d %H:%M')
        return '未检查'
    last_status_check.short_description = '最后检查'


@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    """增强版主机管理后台"""

    form = HostAdminForm
    list_display = ('name_display', 'hostname', 'connection_type', 'port', 'username', 'host_type', 'status_display', 'ssl_badge', 'cert_validation', 'last_status_check', 'created_at')
    list_filter = ('status', 'host_type', 'connection_type', 'created_at', 'use_ssl', 'server_cert_validation')
    search_fields = ('name', 'hostname', 'description', 'username')
    list_per_page = 20
    actions = ['test_connections', 'sync_host_info', 'export_host_list', 'enable_ssl', 'disable_ssl', 'enable_cert_validation']
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'password_encrypted', 'last_test_timestamp')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'hostname', 'connection_type', 'port', 'rdp_port', 'use_ssl', 'description')
        }),
        ('认证信息', {
            'fields': ('username', 'password', 'password_encrypted'),
            'description': '请输入主机的认证信息'
        }),
        ('证书配置', {
            'fields': ('server_cert_validation', 'ca_cert_path', 'client_cert_path', 'client_key_path'),
            'description': 'SSL/TLS 证书验证配置（仅在使用SSL时生效）'
        }),
        ('主机信息', {
            'fields': ('host_type', 'os_version', 'status', 'last_test_timestamp', 'last_test_result')
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