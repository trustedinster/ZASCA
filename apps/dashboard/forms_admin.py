"""
仪表盘超级管理员表单
"""

from django import forms
from .models import DashboardWidget, SystemConfig


class DashboardWidgetForm(forms.ModelForm):
    """仪表盘组件表单"""

    class Meta:
        model = DashboardWidget
        fields = [
            'widget_type', 'title', 'display_order',
            'is_enabled', 'widget_config',
        ]

    def clean_widget_config(self):
        """验证 widget_config 为有效 JSON"""
        import json
        config = self.cleaned_data.get('widget_config')
        if config:
            if isinstance(config, str):
                try:
                    json.loads(config)
                except json.JSONDecodeError:
                    raise forms.ValidationError('配置参数必须是有效的 JSON 格式')
        return config


class SystemConfigForm(forms.ModelForm):
    """系统配置表单（单例）"""

    _PRESERVE_IF_EMPTY = [
        'smtp_password',
        'captcha_key',
        'email_captcha_key',
        'login_captcha_key',
        'register_captcha_key',
    ]

    class Meta:
        model = SystemConfig
        fields = [
            'site_name',
            'enable_registration',
            'icp_number',
            'police_number',
            'smtp_host',
            'smtp_port',
            'smtp_use_tls',
            'smtp_username',
            'smtp_password',
            'smtp_from_email',
            'captcha_provider',
            'captcha_id',
            'captcha_key',
            'email_captcha_provider',
            'email_captcha_id',
            'email_captcha_key',
            'login_captcha_provider',
            'login_captcha_id',
            'login_captcha_key',
            'register_captcha_provider',
            'register_captcha_id',
            'register_captcha_key',
            'email_suffix_whitelist',
            'email_suffix_blacklist',
            'local_access_locked',
        ]

    def clean_smtp_port(self):
        port = self.cleaned_data.get('smtp_port')
        if port and (port < 1 or port > 65535):
            raise forms.ValidationError('端口号必须在 1-65535 之间')
        return port

    def clean(self):
        cleaned = super().clean()
        if cleaned is None:
            cleaned = {}
        provider = cleaned.get('captcha_provider')
        errors = {}

        if provider in ['geetest', 'turnstile']:
            captcha_id = cleaned.get('captcha_id')
            captcha_key = cleaned.get('captcha_key')
            if self.instance and self.instance.pk:
                if not captcha_id:
                    captcha_id = self.instance.captcha_id
                if not captcha_key:
                    captcha_key = self.instance.captcha_key
            if not (captcha_id and captcha_key):
                msg = (
                    f'启用 '
                    f'{self.instance.get_captcha_provider_display()} '
                    f'时必须填写验证码 ID 和密钥。'
                )
                errors['captcha_id'] = msg
                errors['captcha_key'] = msg

        if errors:
            raise forms.ValidationError(errors)

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.instance and self.instance.pk:
            for field in self._PRESERVE_IF_EMPTY:
                if not getattr(instance, field):
                    setattr(
                        instance, field,
                        getattr(self.instance, field),
                    )
        if commit:
            instance.save()
        return instance
