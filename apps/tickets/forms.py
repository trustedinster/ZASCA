"""
工单系统表单
"""
from django import forms
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from .models import Ticket, TicketComment, TicketCategory

User = get_user_model()


class TicketForm(forms.ModelForm):
    """
    工单创建/编辑表单
    """
    title = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入工单标题'
        }),
        label=_('标题'),
        help_text=_('请简要描述工单主题')
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': '请详细描述您的问题或需求'
        }),
        label=_('详细描述'),
        help_text=_('请提供尽可能详细的信息，以便我们更好地帮助您')
    )
    
    category = forms.ModelChoiceField(
        queryset=TicketCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('分类'),
        help_text=_('请选择工单分类'),
        required=False
    )
    
    priority = forms.ChoiceField(
        choices=Ticket.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('优先级'),
        help_text=_('请选择工单优先级'),
        initial='medium'
    )
    
    related_product = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('关联产品'),
        help_text=_('如有关联的产品，请选择'),
        required=False
    )
    
    related_host = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('关联主机'),
        help_text=_('如有关联的主机，请选择'),
        required=False
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority', 'related_product', 'related_host']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 动态设置关联产品查询集
        from apps.operations.models import Product
        from apps.hosts.models import Host
        
        self.fields['related_product'].queryset = Product.objects.filter(is_available=True)
        self.fields['related_host'].queryset = Host.objects.all()
        
        # 如果有分类，设置默认优先级
        if self.data.get('category'):
            try:
                category = TicketCategory.objects.get(pk=self.data['category'])
                self.fields['priority'].initial = category.default_priority
            except TicketCategory.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        
        # 如果有分类，继承分类的默认优先级（如果用户未修改）
        category = cleaned_data.get('category')
        priority = cleaned_data.get('priority')
        
        if category and priority == 'medium' and category.default_priority != 'medium':
            # 如果用户没有显式修改优先级，使用分类默认值
            if not self.data.get('priority') or self.data.get('priority') == 'medium':
                cleaned_data['priority'] = category.default_priority
        
        return cleaned_data


class TicketCommentForm(forms.ModelForm):
    """
    工单评论表单
    """
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '请输入评论内容'
        }),
        label=_('内容'),
        help_text=_('请输入您的回复')
    )
    
    is_internal = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('内部备注'),
        help_text=_('仅工作人员可见')
    )

    class Meta:
        model = TicketComment
        fields = ['content', 'is_internal']


class TicketAssignForm(forms.Form):
    """
    工单分配表单
    """
    assignee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('处理人'),
        help_text=_('请选择要分配的处理人')
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': '可选：添加分配备注'
        }),
        label=_('备注'),
        help_text=_('可选：添加分配备注')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 只显示有权限处理工单的用户（staff、superuser、提供商）
        self.fields['assignee'].queryset = User.objects.filter(
            is_active=True
        ).filter(
            models.Q(is_staff=True) | models.Q(is_superuser=True) | models.Q(groups__name='提供商')
        ).distinct()


class TicketStatusForm(forms.Form):
    """
    工单状态变更表单
    """
    status = forms.ChoiceField(
        choices=[
            ('pending', _('待处理')),
            ('processing', _('处理中')),
            ('waiting_feedback', _('待反馈')),
            ('resolved', _('已解决')),
            ('closed', _('已关闭')),
            ('rejected', _('已驳回')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('新状态'),
        help_text=_('请选择新的工单状态')
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': '可选：添加状态变更备注'
        }),
        label=_('备注'),
        help_text=_('可选：添加状态变更备注')
    )


class TicketCloseForm(forms.Form):
    """
    工单关闭表单（含满意度评价）
    """
    satisfaction = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('不评价')),
            ('5', _('非常满意')),
            ('4', _('满意')),
            ('3', _('一般')),
            ('2', _('不满意')),
            ('1', _('非常不满意')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('满意度评分'),
        help_text=_('请对工单处理进行评价')
    )
    
    satisfaction_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '可选：请输入您的评价内容'
        }),
        label=_('评价内容'),
        help_text=_('可选：请输入您的评价内容')
    )


class TicketFilterForm(forms.Form):
    """
    工单筛选表单
    """
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('全部'))] + Ticket.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('状态')
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', _('全部'))] + Ticket.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('优先级')
    )
    
    category = forms.ModelChoiceField(
        required=False,
        queryset=TicketCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('分类')
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜索工单编号、标题或描述'
        }),
        label=_('搜索')
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('开始日期')
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('结束日期')
    )
