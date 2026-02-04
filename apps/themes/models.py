"""
主题系统数据模型

优化设计原则：
1. 使用 JSONField 存储灵活配置，减少字段膨胀
2. 利用 Django 缓存机制，避免重复查询
3. 单例模式通过 get_or_create 实现，无需强制 pk=1
"""
from django.db import models
from django.core.cache import cache
from django.utils import timezone


class ThemeConfig(models.Model):
    """
    主题配置模型（单例）

    存储全局主题设置、品牌资源和自定义 CSS 变量
    使用缓存优化查询性能
    """

    THEME_CHOICES = [
        ('material-design-3', 'Material Design 3'),
        ('neumorphism', '新拟态'),
    ]

    CACHE_KEY = 'theme_config_singleton'
    CACHE_TIMEOUT = 3600  # 1小时缓存

    # 基础主题设置
    active_theme = models.CharField(
        '当前主题',
        max_length=50,
        choices=THEME_CHOICES,
        default='material-design-3',
        db_index=True
    )

    # 品牌资源 - 使用单一 JSONField 存储路径
    # 结构: {"logo": "path", "logo_dark": "path", "favicon": "path", "login_bg": "path"}
    branding = models.JSONField(
        '品牌资源',
        default=dict,
        blank=True,
        help_text='存储品牌资源路径：logo, logo_dark, favicon, login_bg'
    )

    # 自定义颜色 - JSONField 存储所有颜色变量
    # 结构: {"primary": "#xxx", "secondary": "#xxx", "accent": "#xxx", ...}
    custom_colors = models.JSONField(
        '自定义颜色',
        default=dict,
        blank=True,
        help_text='自定义 CSS 颜色变量'
    )

    # 高级 CSS 变量覆盖
    css_overrides = models.TextField(
        '自定义 CSS',
        blank=True,
        help_text='自定义 CSS 样式覆盖'
    )

    # 移动端适配开关
    enable_mobile_optimization = models.BooleanField(
        '启用移动端优化',
        default=True
    )

    # 时间戳
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '主题配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'主题配置 - {self.get_active_theme_display()}'

    def save(self, *args, **kwargs):
        """保存时清除缓存"""
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):
        """删除时清除缓存"""
        cache.delete(self.CACHE_KEY)
        super().delete(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """
        获取配置单例（带缓存）

        Returns:
            ThemeConfig: 配置实例
        """
        config = cache.get(cls.CACHE_KEY)
        if config is None:
            config, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, config, cls.CACHE_TIMEOUT)
        return config

    @classmethod
    def invalidate_cache(cls):
        """手动清除缓存"""
        cache.delete(cls.CACHE_KEY)

    def get_branding(self, key, default=''):
        """安全获取品牌资源路径"""
        return self.branding.get(key, default) if self.branding else default

    def get_color(self, key, default=None):
        """安全获取自定义颜色"""
        return self.custom_colors.get(key, default) if self.custom_colors else default

    def generate_css_variables(self):
        """
        生成 CSS 变量字符串

        Returns:
            str: CSS 变量定义
        """
        if not self.custom_colors:
            return ''

        lines = [':root {']
        for key, value in self.custom_colors.items():
            css_key = f'--theme-{key.replace("_", "-")}'
            lines.append(f'  {css_key}: {value};')
        lines.append('}')
        return '\n'.join(lines)


class PageContent(models.Model):
    """
    可编辑页面内容

    使用 position 作为唯一标识符，支持多语言扩展
    """

    POSITION_CHOICES = [
        ('login_welcome', '登录页欢迎语'),
        ('login_subtitle', '登录页副标题'),
        ('dashboard_notice', '仪表盘公告'),
        ('footer_text', '页脚文字'),
        ('footer_copyright', '版权信息'),
        ('maintenance_message', '维护提示'),
        ('register_terms', '注册条款'),
    ]

    CACHE_KEY_PREFIX = 'page_content_'
    CACHE_TIMEOUT = 3600

    position = models.CharField(
        '位置标识',
        max_length=50,
        choices=POSITION_CHOICES,
        unique=True,
        db_index=True
    )
    title = models.CharField(
        '标题',
        max_length=200,
        blank=True
    )
    content = models.TextField(
        '内容',
        blank=True,
        help_text='支持 HTML 格式'
    )
    is_enabled = models.BooleanField(
        '是否启用',
        default=True,
        db_index=True
    )
    # 元数据 - 存储额外配置
    metadata = models.JSONField(
        '元数据',
        default=dict,
        blank=True,
        help_text='存储额外配置：icon, color, link 等'
    )
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '页面内容'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['position', 'is_enabled']),
        ]

    def __str__(self):
        return f'{self.get_position_display()}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'{self.CACHE_KEY_PREFIX}{self.position}')
        cache.delete(f'{self.CACHE_KEY_PREFIX}all')

    def delete(self, *args, **kwargs):
        cache.delete(f'{self.CACHE_KEY_PREFIX}{self.position}')
        cache.delete(f'{self.CACHE_KEY_PREFIX}all')
        super().delete(*args, **kwargs)

    @classmethod
    def get_content(cls, position, default=''):
        """
        获取指定位置的内容（带缓存）

        Args:
            position: 位置标识
            default: 默认值

        Returns:
            str: 内容文本
        """
        cache_key = f'{cls.CACHE_KEY_PREFIX}{position}'
        result = cache.get(cache_key)

        if result is None:
            try:
                obj = cls.objects.get(position=position, is_enabled=True)
                result = obj.content
            except cls.DoesNotExist:
                result = default
            cache.set(cache_key, result, cls.CACHE_TIMEOUT)

        return result

    @classmethod
    def get_all_enabled(cls):
        """
        获取所有启用的内容（带缓存）

        Returns:
            dict: {position: PageContent}
        """
        cache_key = f'{cls.CACHE_KEY_PREFIX}all'
        result = cache.get(cache_key)

        if result is None:
            result = {
                obj.position: obj
                for obj in cls.objects.filter(is_enabled=True)
            }
            cache.set(cache_key, result, cls.CACHE_TIMEOUT)

        return result


class WidgetLayout(models.Model):
    """
    仪表盘组件布局配置

    与 dashboard.DashboardWidget 配合使用，提供布局控制
    此模型只存储布局信息，不复制组件数据
    """

    # 关联到 dashboard.DashboardWidget 的 widget_type
    widget_type = models.CharField(
        '组件类型',
        max_length=50,
        unique=True,
        db_index=True
    )

    # 布局配置
    display_order = models.PositiveIntegerField(
        '显示顺序',
        default=0,
        db_index=True
    )
    column_span = models.PositiveSmallIntegerField(
        '列跨度',
        default=1,
        choices=[(1, '1列'), (2, '2列'), (3, '3列'), (4, '全宽')],
        help_text='在12列栅格中占据的列数比例'
    )
    row_span = models.PositiveSmallIntegerField(
        '行跨度',
        default=1,
        choices=[(1, '1行'), (2, '2行')],
    )
    is_visible = models.BooleanField(
        '是否显示',
        default=True,
        db_index=True
    )

    # 响应式配置 - JSONField 存储各断点的显示设置
    # 结构: {"mobile": true, "tablet": true, "desktop": true}
    responsive = models.JSONField(
        '响应式配置',
        default=dict,
        blank=True,
        help_text='各设备的显示配置'
    )

    class Meta:
        verbose_name = '组件布局'
        verbose_name_plural = verbose_name
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['display_order', 'is_visible']),
        ]

    def __str__(self):
        return f'{self.widget_type} - 顺序:{self.display_order}'

    def get_responsive(self, device, default=True):
        """获取特定设备的显示设置"""
        if not self.responsive:
            return default
        return self.responsive.get(device, default)

    def get_column_class(self):
        """获取 Bootstrap 列 CSS 类"""
        span_map = {1: 'col-md-3', 2: 'col-md-6', 3: 'col-md-9', 4: 'col-12'}
        return span_map.get(self.column_span, 'col-md-3')
