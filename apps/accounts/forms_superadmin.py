"""
超级管理员表单

用于超级管理员分配提供商给主机和主机组。
"""

from django import forms
from django.contrib.auth import get_user_model

from utils.provider import PROVIDER_GROUP_NAME

User = get_user_model()


def _get_provider_queryset():
    """获取属于'提供商'组的用户查询集"""
    return User.objects.filter(
        groups__name=PROVIDER_GROUP_NAME,
        is_staff=True,
        is_active=True,
    ).order_by('username')


class HostProviderAssignForm(forms.Form):
    """
    主机提供商分配表单

    允许超级管理员为指定主机分配多个提供商。
    """
    providers = forms.ModelMultipleChoiceField(
        queryset=_get_provider_queryset(),
        required=False,
        label='管理提供商',
        help_text='选择可以管理此主机的提供商用户，留空表示不分配任何提供商',
        widget=forms.SelectMultiple(attrs={
            'size': 12,
            'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 '
                     'text-md-on-surface focus:outline-none focus:ring-2 focus:ring-md-primary '
                     'transition cursor-pointer',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.host = kwargs.pop('host', None)
        super().__init__(*args, **kwargs)
        if self.host:
            self.fields['providers'].initial = self.host.providers.all()


class HostGroupProviderAssignForm(forms.Form):
    """
    主机组提供商分配表单

    允许超级管理员为指定主机组分配多个提供商。
    """
    providers = forms.ModelMultipleChoiceField(
        queryset=_get_provider_queryset(),
        required=False,
        label='管理提供商',
        help_text='选择可以管理此主机组的提供商用户，留空表示不分配任何提供商',
        widget=forms.SelectMultiple(attrs={
            'size': 12,
            'class': 'w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 '
                     'text-md-on-surface focus:outline-none focus:ring-2 focus:ring-md-primary '
                     'transition cursor-pointer',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.hostgroup = kwargs.pop('hostgroup', None)
        super().__init__(*args, **kwargs)
        if self.hostgroup:
            self.fields['providers'].initial = self.hostgroup.providers.all()
