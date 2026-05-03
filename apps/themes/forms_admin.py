"""
主题系统超级管理员表单
"""

from django import forms
from .models import ThemeConfig, PageContent, WidgetLayout


class ThemeConfigForm(forms.ModelForm):
    """主题配置表单（单例）"""

    class Meta:
        model = ThemeConfig
        fields = [
            'active_theme',
            'branding',
            'custom_colors',
            'css_overrides',
            'enable_mobile_optimization',
        ]

    def clean_branding(self):
        """验证 branding 为有效 JSON"""
        import json
        data = self.cleaned_data.get('branding')
        if data and isinstance(data, str):
            try:
                json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError('品牌资源必须是有效的 JSON 格式')
        return data

    def clean_custom_colors(self):
        """验证 custom_colors 为有效 JSON"""
        import json
        data = self.cleaned_data.get('custom_colors')
        if data and isinstance(data, str):
            try:
                json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError('自定义颜色必须是有效的 JSON 格式')
        return data


class PageContentForm(forms.ModelForm):
    """页面内容表单"""

    class Meta:
        model = PageContent
        fields = [
            'position',
            'title',
            'content',
            'is_enabled',
            'metadata',
        ]

    def clean_metadata(self):
        """验证 metadata 为有效 JSON"""
        import json
        data = self.cleaned_data.get('metadata')
        if data and isinstance(data, str):
            try:
                json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError('元数据必须是有效的 JSON 格式')
        return data


class WidgetLayoutForm(forms.ModelForm):
    """组件布局表单"""

    class Meta:
        model = WidgetLayout
        fields = [
            'widget_type',
            'display_order',
            'column_span',
            'row_span',
            'is_visible',
            'responsive',
        ]

    def clean_responsive(self):
        """验证 responsive 为有效 JSON"""
        import json
        data = self.cleaned_data.get('responsive')
        if data and isinstance(data, str):
            try:
                json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError('响应式配置必须是有效的 JSON 格式')
        return data
