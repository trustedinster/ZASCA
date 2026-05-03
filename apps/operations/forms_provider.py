"""
运营管理 - 提供商后台表单

包含开户申请、云电脑用户管理、邀请令牌、产品、产品组相关的表单。
"""

import json
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Product, ProductGroup, ProductInvitationToken


class AccountOpeningRequestRejectForm(forms.Form):
    """
    驳回开户申请表单

    用于输入驳回原因
    """

    rejection_reason = forms.CharField(
        label='驳回原因',
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': '请输入驳回原因...',
            'class': 'w-full px-4 py-3 bg-md-surface-container-high/50 border border-white/10 '
                     'rounded-md text-md-on-surface placeholder-md-on-surface-variant/50 '
                     'focus:outline-none focus:ring-2 focus:ring-md-primary focus:border-transparent '
                     'transition resize-none',
        }),
        help_text='驳回原因将作为审核备注发送给申请人',
    )


class CloudComputerUserDiskQuotaForm(forms.Form):
    """
    磁盘配额设置表单

    用于设置用户的磁盘配额（MB），格式为 {"C:": 10240, "D:": 20480}
    """

    disk_quota = forms.CharField(
        label=_('磁盘配额'),
        help_text=_('JSON 格式，例如: {"C:": 10240, "D:": 20480}'),
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': '{"C:": 10240, "D:": 20480}',
            'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 text-md-on-surface placeholder-md-outline focus:outline-none focus:ring-2 focus:ring-md-primary transition resize-y font-mono text-sm',
        }),
    )

    def clean_disk_quota(self):
        data = self.cleaned_data.get('disk_quota', '{}')
        if not data or not data.strip():
            return {}
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError('磁盘配额格式无效，请输入有效的 JSON 格式')
        if not isinstance(parsed, dict):
            raise forms.ValidationError('磁盘配额必须为字典格式，例如: {"C:": 10240}')
        for disk, value in parsed.items():
            try:
                val = int(value)
                if val < 0:
                    raise forms.ValidationError(f'磁盘 {disk} 的配额不能为负数')
            except (ValueError, TypeError):
                raise forms.ValidationError(f'磁盘 {disk} 的配额必须为数字')
        return parsed


class CloudComputerUserResetPasswordForm(forms.Form):
    """
    重置密码表单

    用于重置云电脑用户的 Windows 密码
    """

    new_password = forms.CharField(
        label=_('新密码'),
        help_text=_('设置用户的新密码，建议使用复杂密码'),
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 text-md-on-surface placeholder-md-outline focus:outline-none focus:ring-2 focus:ring-md-primary transition',
            'placeholder': '请输入新密码',
        }),
    )

    confirm_password = forms.CharField(
        label=_('确认密码'),
        help_text=_('再次输入新密码以确认'),
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 text-md-on-surface placeholder-md-outline focus:outline-none focus:ring-2 focus:ring-md-primary transition',
            'placeholder': '请再次输入新密码',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('两次输入的密码不一致')

        return cleaned_data


class ProductInvitationTokenForm(forms.ModelForm):
    """
    产品邀请令牌创建表单

    提供商只能选择自己创建的产品/产品组
    """

    class Meta:
        model = ProductInvitationToken
        fields = ['product', 'product_group', 'max_uses', 'expires_at', 'is_active']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 '
                         'text-md-on-surface appearance-none focus:outline-none focus:ring-2 '
                         'focus:ring-md-primary transition cursor-pointer',
            }),
            'product_group': forms.Select(attrs={
                'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 '
                         'text-md-on-surface appearance-none focus:outline-none focus:ring-2 '
                         'focus:ring-md-primary transition cursor-pointer',
            }),
            'max_uses': forms.NumberInput(attrs={
                'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 '
                         'text-md-on-surface placeholder-md-outline focus:outline-none focus:ring-2 '
                         'focus:ring-md-primary transition',
                'placeholder': '0 表示无限制',
                'min': '0',
            }),
            'expires_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 '
                         'text-md-on-surface focus:outline-none focus:ring-2 '
                         'focus:ring-md-primary transition',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-md-outline bg-md-surface-container-high text-md-primary '
                         'focus:ring-md-primary focus:ring-2 cursor-pointer',
            }),
        }
        labels = {
            'product': _('关联产品'),
            'product_group': _('关联产品组'),
            'max_uses': _('最大使用次数'),
            'expires_at': _('过期时间'),
            'is_active': _('是否启用'),
        }
        help_texts = {
            'product': _('此令牌关联的产品（与产品组至少选一个）'),
            'product_group': _('此令牌关联的产品组（与产品至少选一个）'),
            'max_uses': _('令牌最大可使用次数，0表示无限制'),
            'expires_at': _('令牌过期时间，留空表示永不过期'),
        }

    def __init__(self, *args, **kwargs):
        self.provider_user = kwargs.pop('provider_user', None)
        super().__init__(*args, **kwargs)

        if self.provider_user:
            from apps.operations.models import Product, ProductGroup
            self.fields['product'].queryset = Product.objects.filter(
                created_by=self.provider_user
            )
            self.fields['product_group'].queryset = ProductGroup.objects.filter(
                created_by=self.provider_user
            )

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        product_group = cleaned_data.get('product_group')
        if not product and not product_group:
            raise forms.ValidationError(
                _('关联产品和关联产品组至少需要选择一个。')
            )
        return cleaned_data


# ========== 产品管理表单 ==========


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
_CHECKBOX_CLASS = (
    'w-5 h-5 rounded border-md-outline/50 bg-md-surface/50 '
    'text-md-primary focus:ring-md-primary focus:ring-2 '
    'transition cursor-pointer accent-md-primary'
)
_TEXTAREA_CLASS = (
    'w-full bg-md-surface/50 border border-md-outline/50 rounded-md '
    'px-4 py-3 text-md-on-surface placeholder-md-outline '
    'focus:outline-none focus:ring-2 focus:ring-md-primary '
    'transition resize-y'
)


class ProductForm(forms.ModelForm):
    """
    产品管理表单

    复用 Admin 中 ProductAdminForm 的逻辑，使用 MD3 风格的 Widget。
    包含磁盘配额配置和主机保护开关。
    提供商只能选择自己可见的主机。
    """

    default_disk_quota = forms.CharField(
        label=_('默认磁盘配额'),
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '{"C:": 10240, "D:": 20480}',
            'class': _TEXTAREA_CLASS + ' font-mono text-sm',
        }),
        help_text=_(
            '每个磁盘的默认配额大小（MB），'
            'JSON 格式，如 {"C:": 10240, "D:": 20480}'
        ),
    )

    allow_extra_quota_disks = forms.CharField(
        label=_('允许额外申请容量的磁盘'),
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': '["C:", "D:"]',
            'class': _TEXTAREA_CLASS + ' font-mono text-sm',
        }),
        help_text=_(
            '允许用户在申请时额外申请容量的磁盘列表，'
            'JSON 数组格式，如 ["C:", "D:"]'
        ),
    )

    class Meta:
        model = Product
        fields = [
            'display_name', 'display_description',
            'product_group',
            'host', 'is_available', 'auto_approval', 'visibility',
            'enable_host_protection',
            'display_hostname', 'rdp_port',
            'enable_disk_quota',
        ]
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '输入产品显示名称',
            }),
            'display_description': forms.Textarea(attrs={
                'class': _TEXTAREA_CLASS,
                'rows': 3,
                'placeholder': '输入产品显示描述（可选）',
            }),
            'product_group': forms.Select(attrs={
                'class': _SELECT_CLASS,
            }),
            'host': forms.Select(attrs={
                'class': _SELECT_CLASS,
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': _CHECKBOX_CLASS,
            }),
            'auto_approval': forms.CheckboxInput(attrs={
                'class': _CHECKBOX_CLASS,
            }),
            'visibility': forms.Select(attrs={
                'class': _SELECT_CLASS,
            }),
            'enable_host_protection': forms.CheckboxInput(attrs={
                'class': _CHECKBOX_CLASS,
            }),
            'display_hostname': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '输入显示地址',
            }),
            'rdp_port': forms.NumberInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '3389',
            }),
            'enable_disk_quota': forms.CheckboxInput(attrs={
                'class': _CHECKBOX_CLASS,
            }),
        }
        labels = {
            'display_name': _('显示名称'),
            'display_description': _('显示描述'),
            'product_group': _('产品组'),
            'host': _('关联主机'),
            'is_available': _('是否可用'),
            'auto_approval': _('自动审核'),
            'visibility': _('可见性'),
            'enable_host_protection': _('启用主机保护(Gateway)'),
            'display_hostname': _('显示地址'),
            'rdp_port': _('RDP端口'),
            'enable_disk_quota': _('启用磁盘配额管理'),
        }
        help_texts = {
            'host': _('此产品运行所在的主机'),
            'is_available': _('是否在前端展示此产品'),
            'auto_approval': _('是否自动批准针对此产品的开户申请'),
            'visibility': _(
                '公开对所有用户可见，'
                '邀请访问仅对已授权用户可见'
            ),
            'enable_host_protection': _(
                '启用后，用户只能通过Gateway隧道访问RDP，'
                '主机不暴露公网IP。需部署Gateway服务。'
            ),
            'enable_disk_quota': _(
                '是否启用磁盘配额管理，'
                '启用后将自动为新用户设置磁盘配额'
            ),
        }

    def __init__(self, *args, **kwargs):
        self.provider_user = kwargs.pop('provider_user', None)
        super().__init__(*args, **kwargs)

        # 提供商只能选择自己可见的主机
        if self.provider_user:
            from utils.provider import get_provider_hosts
            self.fields['host'].queryset = get_provider_hosts(
                self.provider_user
            ).order_by('name')

            # 提供商只能选择自己创建的产品组
            self.fields['product_group'].queryset = (
                ProductGroup.objects.filter(
                    created_by=self.provider_user
                ).order_by('name')
            )

        # 初始化 JSON 字段的显示值
        if self.instance and self.instance.pk:
            if self.instance.default_disk_quota:
                self.initial['default_disk_quota'] = json.dumps(
                    self.instance.default_disk_quota,
                    ensure_ascii=False,
                    indent=2,
                )
            if self.instance.allow_extra_quota_disks:
                self.initial['allow_extra_quota_disks'] = json.dumps(
                    self.instance.allow_extra_quota_disks,
                    ensure_ascii=False,
                )

    def clean_default_disk_quota(self):
        data = self.cleaned_data.get('default_disk_quota', '')
        if not data or not data.strip():
            return {}
        if isinstance(data, dict):
            return data
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError('磁盘配额格式无效，请输入有效的 JSON')
        if not isinstance(parsed, dict):
            raise forms.ValidationError(
                '磁盘配额必须为字典格式，如 {"C:": 10240}'
            )
        for disk, value in parsed.items():
            try:
                val = int(value)
                if val < 0:
                    raise forms.ValidationError(
                        f'磁盘 {disk} 的配额不能为负数'
                    )
            except (ValueError, TypeError):
                raise forms.ValidationError(
                    f'磁盘 {disk} 的配额必须为数字'
                )
        return parsed

    def clean_allow_extra_quota_disks(self):
        data = self.cleaned_data.get('allow_extra_quota_disks', '')
        if not data or not data.strip():
            return []
        if isinstance(data, list):
            return data
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError(
                '磁盘列表格式无效，请输入有效的 JSON 数组'
            )
        if not isinstance(parsed, list):
            raise forms.ValidationError(
                '磁盘列表必须为数组格式，如 ["C:", "D:"]'
            )
        return parsed

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.default_disk_quota = self.cleaned_data.get(
            'default_disk_quota', {}
        )
        instance.allow_extra_quota_disks = self.cleaned_data.get(
            'allow_extra_quota_disks', []
        )
        if commit:
            instance.save()
        return instance


# ========== 产品组管理表单 ==========


class ProductGroupForm(forms.ModelForm):
    """
    产品组管理表单

    提供商创建产品组时自动设置 created_by。
    """

    class Meta:
        model = ProductGroup
        fields = [
            'name', 'description',
            'display_order', 'is_active', 'visibility',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '输入产品组名称',
            }),
            'description': forms.Textarea(attrs={
                'class': _TEXTAREA_CLASS,
                'rows': 3,
                'placeholder': '输入产品组描述（可选）',
            }),
            'display_order': forms.NumberInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '0',
                'min': '0',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': _CHECKBOX_CLASS,
            }),
            'visibility': forms.Select(attrs={
                'class': _SELECT_CLASS,
            }),
        }
        labels = {
            'name': _('产品组名称'),
            'description': _('描述'),
            'display_order': _('显示顺序'),
            'is_active': _('是否启用'),
            'visibility': _('可见性'),
        }
        help_texts = {
            'display_order': _(
                '产品组在前端展示的顺序，数字越小越靠前'
            ),
            'is_active': _('是否在前端展示此产品组'),
            'visibility': _(
                '公开对所有用户可见，'
                '邀请访问仅对已授权用户可见'
            ),
        }
