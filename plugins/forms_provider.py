"""
插件系统 - 提供商后台表单

QQ验证配置相关的表单，支持提供商数据隔离。
"""

from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _

from .models import QQVerificationConfig


# MD3 风格的通用 CSS 类
_INPUT_CLASS = (
    'w-full bg-md-surface/50 border border-md-outline/50 rounded-md '
    'px-4 py-3 text-md-on-surface placeholder-md-outline '
    'focus:outline-none focus:ring-2 focus:ring-md-primary transition'
)
_SELECT_CLASS = (
    'w-full bg-md-surface/50 border border-md-outline/50 rounded-md '
    'px-4 py-3 text-md-on-surface appearance-none '
    'focus:outline-none focus:ring-2 focus:ring-md-primary '
    'transition cursor-pointer'
)


class QQVerificationConfigForm(forms.ModelForm):
    """
    QQ验证配置表单

    提供商只能选择自己创建的产品（product__created_by=request.user）。
    """

    BOT_SERVER_MODE_CHOICES = [
        ('default', '使用系统默认'),
        ('custom', '自定义'),
    ]

    bot_server_mode = forms.ChoiceField(
        choices=BOT_SERVER_MODE_CHOICES,
        initial='default',
        label='机器人服务器',
        help_text='选择使用系统默认配置或自定义配置',
        widget=forms.Select(attrs={
            'class': _SELECT_CLASS,
            'id': 'id_bot_server_mode',
            'x-model': 'botMode',
        }),
    )

    class Meta:
        model = QQVerificationConfig
        fields = [
            'product', 'bot_server_mode', 'host', 'port', 'token',
            'group_ids', 'enable_status', 'non_qq_email_handling',
        ]
        widgets = {
            'product': forms.Select(attrs={
                'class': _SELECT_CLASS,
            }),
            'host': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '例如: 127.0.0.1',
            }),
            'port': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '例如: 8080',
            }),
            'token': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '输入访问令牌',
            }),
            'group_ids': forms.Textarea(attrs={
                'class': (
                    'w-full bg-md-surface/50 border border-md-outline/50 '
                    'rounded-md px-4 py-3 text-md-on-surface '
                    'placeholder-md-outline focus:outline-none '
                    'focus:ring-2 focus:ring-md-primary transition resize-y'
                ),
                'rows': 5,
                'placeholder': '每行输入一个QQ群号',
            }),
            'enable_status': forms.Select(attrs={
                'class': _SELECT_CLASS,
            }),
            'non_qq_email_handling': forms.Select(attrs={
                'class': _SELECT_CLASS,
            }),
        }
        labels = {
            'product': _('关联产品'),
            'host': _('机器人服务器地址'),
            'port': _('机器人服务器端口'),
            'token': _('访问令牌'),
            'group_ids': _('验证群号'),
            'enable_status': _('启用状态'),
            'non_qq_email_handling': _('非QQ邮箱处理策略'),
        }
        help_texts = {
            'product': _(
                '此QQ验证配置关联的产品（每个产品只能有一条配置）'
            ),
            'host': _('QQ机器人服务器的主机地址'),
            'port': _('QQ机器人服务器的端口号'),
            'token': _('用于认证的访问令牌'),
            'group_ids': _(
                '用于验证QQ号是否在群内的群号，每行一个QQ群号'
            ),
            'enable_status': _('QQ验证功能的启用状态'),
            'non_qq_email_handling': _(
                '当用户使用非QQ邮箱时的处理策略'
            ),
        }

    def __init__(self, *args, **kwargs):
        self.provider_user = kwargs.pop('provider_user', None)
        super().__init__(*args, **kwargs)

        if self.provider_user:
            from apps.operations.models import Product
            available_products = Product.objects.filter(
                created_by=self.provider_user
            )
            if self.instance and self.instance.pk:
                available_products = available_products.filter(
                    models.Q(qq_verification_config__isnull=True)
                    | models.Q(qq_verification_config=self.instance)
                )
            else:
                available_products = available_products.filter(
                    qq_verification_config__isnull=True
                )
            self.fields['product'].queryset = (
                available_products.order_by('name')
            )

        if self.instance and self.instance.pk:
            if self.instance.use_default_bot:
                self.fields['bot_server_mode'].initial = 'default'
            else:
                self.fields['bot_server_mode'].initial = 'custom'
        else:
            self.fields['bot_server_mode'].initial = 'default'

        self.fields['host'].required = False
        self.fields['port'].required = False
        self.fields['token'].required = False

    def clean_product(self):
        product = self.cleaned_data.get('product')
        if product and self.provider_user:
            if product.created_by != self.provider_user:
                raise forms.ValidationError(
                    '您只能选择自己创建的产品。'
                )
        return product

    def clean(self):
        cleaned = super().clean()
        if cleaned is None:
            cleaned = {}

        mode = cleaned.get('bot_server_mode', 'default')
        if mode == 'custom':
            if not cleaned.get('host'):
                self.add_error(
                    'host', '自定义模式下必须填写服务器地址'
                )
            if not cleaned.get('port'):
                self.add_error(
                    'port', '自定义模式下必须填写服务器端口'
                )
            if not cleaned.get('token'):
                self.add_error(
                    'token', '自定义模式下必须填写访问令牌'
                )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        mode = self.cleaned_data.get('bot_server_mode', 'default')
        instance.use_default_bot = (mode == 'default')

        if mode == 'default':
            instance.host = None
            instance.port = None
            instance.token = None

        if commit:
            instance.save()
        return instance
