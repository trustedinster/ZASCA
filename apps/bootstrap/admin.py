from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import InitialToken, ActiveSession
from apps.hosts.models import Host
from django.contrib.auth import get_user_model
from django.utils import timezone
import secrets
import json
import base64
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
import pyotp


User = get_user_model()


class InitialTokenAdmin(admin.ModelAdmin):
    """初始令牌管理后台"""
    list_display = ('short_token', 'host_link', 'status', 'created_at', 'expires_at', 'is_expired_display', 'actions_column')
    list_filter = ('status', 'created_at', 'expires_at')
    search_fields = ('token', 'host__name', 'host__hostname')
    readonly_fields = ('token', 'created_at', 'totp_secret_display')
    exclude = ('host',)  # 在表单中排除host字段，通过弹窗选择
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('host')

    def short_token(self, obj):
        """显示令牌的简短版本"""
        return obj.token[:12] + '...' if len(obj.token) > 12 else obj.token
    short_token.short_description = '令牌(简短)'

    def host_link(self, obj):
        """生成主机链接"""
        url = reverse('admin:hosts_host_change', args=[obj.host.id])
        return format_html('<a href="{}">{}</a>', url, obj.host.name)
    host_link.short_description = '主机'

    def is_expired_display(self, obj):
        """显示是否过期"""
        expired = obj.expires_at < timezone.now()
        color = 'red' if expired else 'green'
        return format_html('<span style="color: {};">{}</span>', color, '是' if expired else '否')
    is_expired_display.short_description = '已过期'

    def totp_secret_display(self, obj):
        """显示TOTP密钥（用于调试）"""
        if obj.status == 'ISSUED':  # 只在未验证时显示
            secret = obj.generate_totp_secret()
            return format_html('<code>{}</code>', secret)
        else:
            return "已验证或已消耗，密钥不再显示"
    totp_secret_display.short_description = "TOTP密钥"

    def actions_column(self, obj):
        """操作列"""
        html_parts = []
        
        # 生成配置字符串
        current_site = 'http://localhost:8000'  # 实际应用中需要动态获取
        secret_data = {
            "c_side_url": current_site,
            "token": obj.token,
            "host_id": str(obj.host.id),
            "hostname": obj.host.hostname,
            "generated_at": timezone.now().isoformat(),
            "expires_at": obj.expires_at.isoformat()
        }
        
        json_str = json.dumps(secret_data)
        encoded_bytes = base64.b64encode(json_str.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        
        html_parts.append(format_html(
            '<button class="btn btn-outline-primary btn-sm copy-btn" '
            'data-value="{}" onclick="copyToClipboard(this)">复制配置</button>',
            encoded_str
        ))
        
        return format_html('<div>{}</div>', format_html(''.join(html_parts)))
    actions_column.short_description = '操作'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('generate-token/', 
                 self.admin_site.admin_view(self.generate_token), 
                 name='bootstrap_initialtoken_generate_token'),
            path('<int:object_id>/regenerate-totp-secret/', 
                 self.admin_site.admin_view(self.regenerate_totp_secret), 
                 name='bootstrap_initialtoken_regenerate_totp_secret'),
        ]
        return custom_urls + urls

    def generate_token(self, request):
        """生成新的初始令牌"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=405)
        
        try:
            data = json.loads(request.body.decode('utf-8'))
            host_id = data.get('host_id')
            expire_hours = int(data.get('expire_hours', 24))
            
            if not host_id:
                return JsonResponse({'success': False, 'error': 'Host ID is required'}, status=400)
            
            # 获取主机
            host = Host.objects.get(id=host_id)
            
            # 生成新的令牌
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=expire_hours)
            
            initial_token = InitialToken.objects.create(
                token=token,
                host=host,
                expires_at=expires_at,
                status='ISSUED'
            )
            
            # 计算TOTP密钥
            totp_secret = initial_token.generate_totp_secret()
            
            # 生成配置字符串
            current_site = request.build_absolute_uri('/').rstrip('/')
            secret_data = {
                "c_side_url": current_site,
                "token": initial_token.token,
                "host_id": str(host.id),
                "hostname": host.hostname,
                "generated_at": timezone.now().isoformat(),
                "expires_at": initial_token.expires_at.isoformat()
            }
            
            json_str = json.dumps(secret_data)
            encoded_bytes = base64.b64encode(json_str.encode('utf-8'))
            encoded_str = encoded_bytes.decode('utf-8')
            
            return JsonResponse({
                'success': True,
                'data': {
                    'token': initial_token.token,
                    'host_id': host.id,
                    'hostname': host.hostname,
                    'expires_at': initial_token.expires_at.isoformat(),
                    'config_string': encoded_str,
                    'totp_secret': totp_secret
                }
            })
            
        except Host.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Host not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def regenerate_totp_secret(self, request, object_id):
        """重新生成TOTP密钥"""
        try:
            token_obj = InitialToken.objects.get(id=object_id)
            if token_obj.status != 'ISSUED':
                return JsonResponse({
                    'success': False, 
                    'error': 'Cannot regenerate TOTP secret for verified or consumed tokens'
                }, status=400)
            
            totp_secret = token_obj.generate_totp_secret()
            
            return JsonResponse({
                'success': True,
                'totp_secret': totp_secret
            })
        except InitialToken.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Token not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    class Media:
        js = ('admin/js/bootstrap_admin.js',)
        css = {
            'all': ('admin/css/bootstrap_admin.css',)
        }


class ActiveSessionAdmin(admin.ModelAdmin):
    """活动会话管理后台"""
    list_display = ('session_token_short', 'host_link', 'bound_ip', 'expires_at', 'is_expired_display', 'created_at')
    list_filter = ('expires_at', 'created_at')
    search_fields = ('session_token', 'host__name', 'host__hostname', 'bound_ip')
    readonly_fields = ('session_token', 'host', 'bound_ip', 'expires_at', 'created_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('host')

    def session_token_short(self, obj):
        """显示会话令牌的简短版本"""
        return obj.session_token[:12] + '...' if len(obj.session_token) > 12 else obj.session_token
    session_token_short.short_description = '会话令牌(简短)'

    def host_link(self, obj):
        """生成主机链接"""
        url = reverse('admin:hosts_host_change', args=[obj.host.id])
        return format_html('<a href="{}">{}</a>', url, obj.host.name)
    host_link.short_description = '主机'

    def is_expired_display(self, obj):
        """显示是否过期"""
        expired = obj.expires_at < timezone.now()
        color = 'red' if expired else 'green'
        return format_html('<span style="color: {};">{}</span>', color, '是' if expired else '否')
    is_expired_display.short_description = '已过期'


# 注册模型
admin.site.register(InitialToken, InitialTokenAdmin)
admin.site.register(ActiveSession, ActiveSessionAdmin)


# 添加JavaScript和CSS到静态文件
# 我们需要创建相应的静态文件