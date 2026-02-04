"""
主题系统后台管理

优化设计：
1. ThemeConfig 使用 singleton 模式
2. 颜色字段使用 ColorPicker 预览
3. 提供主题预览和一键重置功能
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.cache import cache
from .models import ThemeConfig, PageContent, WidgetLayout


class ThemeConfigAdmin(admin.ModelAdmin):
    """主题配置后台管理 - 单例模式"""

    list_display = ['active_theme_display', 'mobile_status', 'updated_at', 'actions_column']
    readonly_fields = ['updated_at', 'color_preview', 'branding_preview']

    fieldsets = (
        ('主题选择', {
            'fields': ('active_theme',),
            'description': '选择系统使用的主题风格'
        }),
        ('品牌资源', {
            'fields': ('branding', 'branding_preview'),
            'description': '上传品牌相关资源（JSON格式：{"logo": "/path/to/logo.png", "favicon": "/path/to/favicon.ico"}）'
        }),
        ('自定义颜色', {
            'fields': ('custom_colors', 'color_preview'),
            'description': 'JSON格式：{"primary": "#6750A4", "secondary": "#625B71"}'
        }),
        ('高级设置', {
            'fields': ('css_overrides', 'enable_mobile_optimization'),
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """只允许一条配置记录"""
        return not ThemeConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """禁止删除配置"""
        return False

    def active_theme_display(self, obj):
        """显示当前主题带图标"""
        theme_icons = {
            'material-design-3': '🎨',
            'neumorphism': '💎',
        }
        icon = theme_icons.get(obj.active_theme, '🖌️')
        return format_html(
            '{} <strong>{}</strong>',
            icon, obj.get_active_theme_display()
        )
    active_theme_display.short_description = '当前主题'

    def mobile_status(self, obj):
        """显示移动端适配状态"""
        if obj.enable_mobile_optimization:
            return format_html('<span style="color: #10b981;">✓ 已启用</span>')
        return format_html('<span style="color: #6b7280;">✗ 未启用</span>')
    mobile_status.short_description = '移动端优化'

    def color_preview(self, obj):
        """颜色预览"""
        if not obj.custom_colors:
            return '未设置自定义颜色'

        html_parts = ['<div style="display: flex; gap: 10px; flex-wrap: wrap;">']
        for key, value in obj.custom_colors.items():
            html_parts.append(
                f'<div style="text-align: center;">'
                f'<div style="width: 40px; height: 40px; background: {value}; '
                f'border-radius: 8px; border: 1px solid #ddd;"></div>'
                f'<small>{key}</small></div>'
            )
        html_parts.append('</div>')
        return format_html(''.join(html_parts))
    color_preview.short_description = '颜色预览'

    def branding_preview(self, obj):
        """品牌资源预览"""
        if not obj.branding:
            return '未设置品牌资源'

        html_parts = ['<div style="display: flex; gap: 20px; align-items: center;">']
        for key, path in obj.branding.items():
            if path:
                html_parts.append(
                    f'<div><strong>{key}:</strong><br>'
                    f'<img src="{path}" style="max-height: 50px; max-width: 150px;"></div>'
                )
        html_parts.append('</div>')
        return format_html(''.join(html_parts))
    branding_preview.short_description = '品牌资源预览'

    def actions_column(self, obj):
        """操作按钮列"""
        clear_cache_url = reverse('admin:themes_themeconfig_clear_cache')
        return format_html(
            '<a class="button" href="{}">清除缓存</a>',
            clear_cache_url
        )
    actions_column.short_description = '操作'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('clear-cache/',
                 self.admin_site.admin_view(self.clear_cache_view),
                 name='themes_themeconfig_clear_cache'),
        ]
        return custom_urls + urls

    def clear_cache_view(self, request):
        """清除主题缓存"""
        ThemeConfig.invalidate_cache()
        cache.delete_pattern('page_content_*') if hasattr(cache, 'delete_pattern') else None
        messages.success(request, '主题缓存已清除')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        messages.info(request, '主题配置已更新，缓存已自动清除')


@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    """页面内容后台管理"""

    list_display = ['position_display', 'title', 'is_enabled', 'content_preview', 'updated_at']
    list_filter = ['is_enabled', 'position']
    list_editable = ['is_enabled']
    search_fields = ['title', 'content']
    readonly_fields = ['updated_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('position', 'title', 'is_enabled')
        }),
        ('内容', {
            'fields': ('content',),
            'description': '支持 HTML 格式'
        }),
        ('元数据', {
            'fields': ('metadata',),
            'classes': ('collapse',),
            'description': 'JSON格式额外配置'
        }),
        ('系统信息', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def position_display(self, obj):
        """位置显示带图标"""
        position_icons = {
            'login_welcome': '👋',
            'login_subtitle': '📝',
            'dashboard_notice': '📢',
            'footer_text': '📄',
            'footer_copyright': '©️',
            'maintenance_message': '🔧',
            'register_terms': '📜',
        }
        icon = position_icons.get(obj.position, '📌')
        return format_html('{} {}', icon, obj.get_position_display())
    position_display.short_description = '位置'

    def content_preview(self, obj):
        """内容预览（截断）"""
        if obj.content:
            preview = obj.content[:50]
            if len(obj.content) > 50:
                preview += '...'
            return preview
        return '-'
    content_preview.short_description = '内容预览'


@admin.register(WidgetLayout)
class WidgetLayoutAdmin(admin.ModelAdmin):
    """组件布局后台管理"""

    list_display = ['widget_type', 'display_order', 'column_span', 'row_span', 'is_visible', 'responsive_display']
    list_filter = ['is_visible', 'column_span']
    list_editable = ['display_order', 'column_span', 'is_visible']
    ordering = ['display_order']

    fieldsets = (
        ('组件信息', {
            'fields': ('widget_type',)
        }),
        ('布局设置', {
            'fields': ('display_order', 'column_span', 'row_span', 'is_visible')
        }),
        ('响应式配置', {
            'fields': ('responsive',),
            'description': 'JSON格式：{"mobile": true, "tablet": true, "desktop": true}'
        }),
    )

    def responsive_display(self, obj):
        """响应式配置显示"""
        if not obj.responsive:
            return '默认'

        icons = []
        if obj.get_responsive('mobile'):
            icons.append('📱')
        if obj.get_responsive('tablet'):
            icons.append('📱')  # tablet icon
        if obj.get_responsive('desktop'):
            icons.append('🖥️')
        return ' '.join(icons) if icons else '隐藏'
    responsive_display.short_description = '设备可见性'


# 注册 ThemeConfig（单例处理）
admin.site.register(ThemeConfig, ThemeConfigAdmin)
