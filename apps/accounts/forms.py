"""
用户管理表单
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import UserProfile

User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    """用户注册表单"""

    email = forms.EmailField(
        required=True,
        label=_('邮箱'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('请输入邮箱地址')
        })
    )
    email_code = forms.CharField(
        required=True,
        label=_('邮箱验证码'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('请输入邮箱收到的验证码')
        })
    )
    confirm_password = forms.CharField(
        label=_('确认密码'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('请再次输入密码')
        })
    )
    agree_terms = forms.BooleanField(
        required=True,
        label=_('我已阅读并同意服务条款和隐私政策'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('请输入用户名')
            }),
        }

    def save(self, commit=True):
        """保存用户"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # 创建用户资料
            from .models import UserProfile
            UserProfile.objects.create(user=user)
        return user


class UserUpdateForm(forms.ModelForm):
    """用户信息更新表单"""

    class Meta:
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
        }


class UserLoginForm(forms.Form):
    """用户登录表单"""

    username = forms.CharField(
        label=_('用户名'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('请输入用户名')
        })
    )
    password = forms.CharField(
        label=_('密码'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('请输入密码')
        })
    )
    remember = forms.BooleanField(
        required=False,
        label=_('记住我'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class UserProfileForm(forms.ModelForm):
    """用户资料表单"""

    class Meta:
        model = UserProfile
        fields = ('nickname', 'gender', 'birthday', 'location', 'bio', 'email_notification', 'system_notification')
        widgets = {
            'nickname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('请输入昵称')
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'birthday': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('请输入所在地')
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('请输入个人简介')
            }),
            'email_notification': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'system_notification': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class PasswordChangeForm(forms.Form):
    """密码修改表单"""

    old_password = forms.CharField(
        label=_('当前密码'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('请输入当前密码')
        })
    )
    new_password = forms.CharField(
        label=_('新密码'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('请输入新密码')
        }),
        min_length=8
    )
    confirm_password = forms.CharField(
        label=_('确认密码'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('请再次输入新密码')
        }),
        min_length=8
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError(_('两次输入的密码不一致'))
        
        return cleaned_data
