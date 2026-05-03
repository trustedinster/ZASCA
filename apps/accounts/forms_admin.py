"""
超管后台 - 用户管理表单

包含创建用户、编辑用户、重置密码三个表单。
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password

from apps.accounts.models import GroupProfile

User = get_user_model()


class GroupChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        try:
            profile = obj.profile
            desc = profile.description
            if desc:
                return f'{obj.name} - {desc}'
        except GroupProfile.DoesNotExist:
            pass
        return obj.name


_SELECT_ATTRS = {
    'class': (
        'w-full bg-white/5 backdrop-blur-xl border border-white/10 '
        'rounded-md px-4 py-3 text-white appearance-none '
        'focus:outline-none focus:ring-1 focus:ring-cyan-500/50 '
        'focus:border-cyan-500 transition cursor-pointer'
    ),
}


class AdminUserCreateForm(forms.ModelForm):

    password1 = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(
            attrs={'autocomplete': 'new-password'}
        ),
        help_text='密码需满足安全策略要求',
    )
    password2 = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput(
            attrs={'autocomplete': 'new-password'}
        ),
        help_text='再次输入密码以确认',
    )
    groups = GroupChoiceField(
        queryset=Group.objects.select_related('profile').all(),
        required=False,
        widget=forms.Select(attrs=_SELECT_ATTRS),
        label='用户组',
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'groups',
        ]

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('两次输入的密码不一致')
        validate_password(password2)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            group = self.cleaned_data.get('groups')
            if group:
                user.groups.set([group])
            else:
                user.groups.clear()
        return user


class AdminUserUpdateForm(forms.ModelForm):

    groups = GroupChoiceField(
        queryset=Group.objects.select_related('profile').all(),
        required=False,
        widget=forms.Select(attrs=_SELECT_ATTRS),
        label='用户组',
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'groups',
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            group = self.cleaned_data.get('groups')
            if group:
                user.groups.set([group])
            else:
                user.groups.clear()
        return user


class AdminPasswordResetForm(forms.Form):
    """超管重置用户密码表单"""

    new_password1 = forms.CharField(
        label='新密码',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='密码需满足安全策略要求',
    )
    new_password2 = forms.CharField(
        label='确认新密码',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='再次输入新密码以确认',
    )

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('两次输入的密码不一致')
        validate_password(password2)
        return password2
