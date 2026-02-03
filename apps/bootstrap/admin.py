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
    list_display = ('short_token', 'host_link', 'status', 'pairing_code_display', 'created_at', 'expires_at', 'is_expired_display', 'actions_column')
    list_filter = ('status', 'created_at', 'expires_at')
    search_fields = ('token', 'host__name', 'host__hostname', 'pairing_code')
    readonly_fields = ('token', 'created_at', 'pairing_code_info')
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

    def pairing_code_display(self, obj):
        """显示配对码状态"""
        if obj.pairing_code and obj.pairing_code_expires_at:
            now = timezone.now()
            if now > obj.pairing_code_expires_at:
                return format_html('<span style="color: red;">已过期</span>')
            else:
                remaining = obj.pairing_code_expires_at - now
                minutes = int(remaining.total_seconds() // 60)
                return format_html(
                    '<div class="pairing-code-display" style="background: #e3f2fd; padding: 4px 8px; border-radius: 4px; display: inline-block;">'
                    '<strong>{}</strong><br><small>剩余{}分钟</small></div>', 
                    obj.pairing_code, minutes
                )
        elif obj.status == 'ISSUED':
            return format_html('<span style="color: orange;">未生成</span>')
        else:
            return format_html('<span style="color: green;">已使用</span>')
    pairing_code_display.short_description = '配对码状态'

    def pairing_code_info(self, obj):
        """显示配对码详细信息"""
        if obj.pairing_code and obj.pairing_code_expires_at:
            now = timezone.now()
            if now <= obj.pairing_code_expires_at:
                remaining = obj.pairing_code_expires_at - now
                minutes = int(remaining.total_seconds() // 60)
                seconds = int(remaining.total_seconds() % 60)
                return format_html(
                    '<div style="padding: 10px; background: #e3f2fd; border-left: 4px solid #2196f3; margin: 10px 0;">'
                    '<h4 style="margin: 0 0 10px 0;">🔐 当前配对码</h4>'
                    '<div style="font-size: 2em; font-weight: bold; color: #1976d2; letter-spacing: 3px;">{}</div>'
                    '<div style="margin-top: 8px; color: #666;">有效期剩余: {}分{}秒</div>'
                    '<div style="margin-top: 5px; font-size: 0.9em; color: #888;">过期时间: {}</div>'
                    '</div>',
                    obj.pairing_code, minutes, seconds, obj.pairing_code_expires_at.strftime('%Y-%m-%d %H:%M:%S')
                )
            else:
                return format_html('<div style="color: red; padding: 10px;">⚠️ 配对码已过期</div>')
        else:
            return format_html('<div style="color: #666; padding: 10px;">ℹ️ 暂无有效配对码</div>')
    pairing_code_info.short_description = "配对码信息"

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
        
        # 复制配置按钮
        html_parts.append(format_html(
            '<button class="btn btn-outline-primary btn-sm copy-btn" '
            'data-value="{}" onclick="copyToClipboard(this)" title="复制Base64配置字符串">📋 复制配置</button>',
            encoded_str
        ))
        
        # 刷新配对码按钮（仅对ISSUED状态）
        if obj.status == 'ISSUED':
            html_parts.append(format_html(
                '&nbsp;<button class="btn btn-outline-warning btn-sm" '
                'onclick="refreshPairingCode({})" title="刷新配对码">🔄 刷新码</button>',
                obj.token
            ))
        
        # 查看详情按钮
        html_parts.append(format_html(
            '&nbsp;<a href="{}" class="btn btn-outline-info btn-sm" title="查看详情">👁️ 详情</a>',
            reverse('admin:bootstrap_initialtoken_change', args=[obj.token])
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
            path('<str:object_id>/refresh-pairing-code/', 
                 self.admin_site.admin_view(self.refresh_pairing_code), 
                 name='bootstrap_initialtoken_refresh_pairing_code'),
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
            
            # 生成配对码
            pairing_code = initial_token.generate_pairing_code()
            
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
                    'pairing_code': pairing_code
                }
            })
            
        except Host.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Host not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def refresh_pairing_code(self, request, object_id):
        """刷新配对码"""
        try:
            token_obj = InitialToken.objects.get(token=object_id)
            if token_obj.status != 'ISSUED':
                return JsonResponse({
                    'success': False, 
                    'error': 'Cannot refresh pairing code for paired or consumed tokens'
                }, status=400)
            
            # 生成新的配对码
            pairing_code = token_obj.generate_pairing_code()
            
            return JsonResponse({
                'success': True,
                'pairing_code': pairing_code,
                'expires_in_minutes': 5
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


# 已隐藏主机引导系统的模型注册
# admin.site.register(InitialToken, InitialTokenAdmin)
# admin.site.register(ActiveSession, ActiveSessionAdmin)


# 添加JavaScript和CSS到静态文件
# 我们需要创建相应的静态文件
