"""
操作记录管理后台配置
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.html import mark_safe
from django.utils import timezone

from .models import SystemTask, AccountOpeningRequest, CloudComputerUser, Product
from apps.hosts.models import Host
from utils.winrm_client import WinrmClient


@admin.register(SystemTask)
class SystemTaskAdmin(admin.ModelAdmin):
    """
    系统任务管理后台
    """
    list_display = [
        'name', 'task_type', 'status', 'progress', 
        'created_at', 'started_at', 'completed_at'
    ]
    list_filter = ['status', 'task_type', 'created_at']
    search_fields = ['name', 'task_type', 'description']
    readonly_fields = ['created_at', 'started_at', 'completed_at']

    fieldsets = (
        ('任务信息', {
            'fields': ('name', 'task_type', 'description')
        }),
        ('执行信息', {
            'fields': ('status', 'progress', 'result', 'error_message')
        }),
        ('关联信息', {
            'fields': ('created_by',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def changelist_view(self, request, extra_context=None):
        """
        修复模板上下文处理问题
        """
        return super().changelist_view(request, extra_context)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    产品管理后台
    """
    list_display = [
        'display_name', 'host', 'status', 
        'is_available', 'created_at'
    ]
    list_filter = ['is_available', 'host', 'host__status', 'created_at']
    search_fields = ['name', 'display_name', 'host__name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'display_name', 'description', 'display_description')
        }),
        ('主机关联', {
            'fields': ('host', 'is_available', 'auto_approval')
        }),
        ('显示配置', {
            'fields': ('display_hostname', 'rdp_port',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_changelist_instance(self, request):
        """
        修复Django Admin模板上下文处理问题
        """
        from django.contrib.admin.views.main import ChangeList
        from functools import wraps
        
        # 获取ChangeList实例
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        # Check if list_display_links is None and handle accordingly
        if list_display_links is None:
            list_display_links = []
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        list_select_related = self.get_list_select_related(request)

        changelist = ChangeList(
            request,
            self.model,
            list_display,
            list_display_links,
            list_filter,
            self.date_hierarchy,
            search_fields,
            list_select_related,
            self.list_per_page,
            self.list_max_show_all,
            self.list_editable,
            self,
            sortable_by=[],
            search_help_text='',
        )
        
        return changelist

    def changelist_view(self, request, extra_context=None):
        """
        修复模板上下文处理问题
        """
        return super().changelist_view(request, extra_context)


@admin.register(AccountOpeningRequest)
class AccountOpeningRequestAdmin(admin.ModelAdmin):
    """
    开户申请管理后台
    """
    list_display = [
        'username', 'applicant', 'target_product', 'status', 
        'created_at', 'approval_date'
    ]
    list_filter = ['status', 'target_product', 'created_at', 'approval_date']
    search_fields = ['username', 'user_fullname', 'contact_email', 'applicant__username']
    readonly_fields = ['created_at', 'updated_at', 'cloud_user_id']

    fieldsets = (
        ('申请人信息', {
            'fields': ('applicant', 'contact_email')
        }),
        ('开户信息', {
            'fields': ('username', 'user_fullname', 'user_email', 'user_description')
        }),
        ('目标产品', {
            'fields': ('target_product',)
        }),
        ('审核信息', {
            'fields': ('status', 'approved_by', 'approval_date', 'approval_notes')
        }),
        ('结果信息', {
            'fields': ('cloud_user_id', 'result_message'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('applicant', 'target_product', 'target_product__host', 'approved_by')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "target_product":
            kwargs["queryset"] = Product.objects.filter(is_available=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def changelist_view(self, request, extra_context=None):
        """
        修复模板上下文处理问题
        """
        return super().changelist_view(request, extra_context)

    def approve_selected(self, request, queryset):
        """
        批量通过选中的开户申请
        """
        # 检查queryset是否是QuerySet对象，如果不是（如字节串），则抛出错误或返回提示
        if isinstance(queryset, bytes) or isinstance(queryset, str):
            self.message_user(
                request,
                '错误：无法处理所选项目，请刷新页面后重试。',
                level='error'
            )
            return
        
        updated_count = 0
        for obj in queryset:
            if obj.status == 'pending':  # 只能批准待审核的申请
                obj.status = 'approved'
                obj.approved_by = request.user
                obj.approval_date = timezone.now()
                obj.save()
                updated_count += 1
        
        if updated_count > 0:
            self.message_user(
                request,
                f'成功批准了 {updated_count} 个开户申请。'
            )
        else:
            self.message_user(
                request,
                '没有符合条件的开户申请需要批准（只对待审核状态的申请进行批准）。',
                level='warning'
            )
    
    approve_selected.short_description = "批准选中的开户申请"
    
    def reject_selected(self, request, queryset):
        """
        批量驳回选中的开户申请
        """
        # 检查queryset是否是QuerySet对象，如果不是（如字节串），则抛出错误或返回提示
        if isinstance(queryset, bytes) or isinstance(queryset, str):
            self.message_user(
                request,
                '错误：无法处理所选项目，请刷新页面后重试。',
                level='error'
            )
            return
        
        updated_count = 0
        for obj in queryset:
            if obj.status == 'pending':  # 只能驳回待审核的申请
                obj.status = 'rejected'
                obj.approved_by = request.user
                obj.approval_date = timezone.now()
                obj.save()
                updated_count += 1
        
        if updated_count > 0:
            self.message_user(
                request,
                f'成功驳回了 {updated_count} 个开户申请。'
            )
        else:
            self.message_user(
                request,
                '没有符合条件的开户申请需要驳回（只对待审核状态的申请进行驳回）。',
                level='warning'
            )
    
    reject_selected.short_description = "驳回选中的开户申请"
    
    def get_actions(self, request):
        """
        注册自定义操作
        """
        actions = super().get_actions(request)
        # 添加批量通过和批量驳回操作
        actions['approve_selected'] = (
            self.approve_selected,
            'approve_selected',
            '批准选中的开户申请'
        )
        actions['reject_selected'] = (
            self.reject_selected,
            'reject_selected',
            '驳回选中的开户申请'
        )
        return actions
    
    def save_model(self, request, obj, form, change):
        """
        重写save_model方法，在保存时自动填入当前用户作为审核人，当前时间作为审核时间
        """
        # 检查是否在审核状态（批准或拒绝）
        if obj.status in ['approved', 'rejected'] and (not obj.approved_by or not obj.approval_date):
            # 自动填入当前用户作为审核人
            obj.approved_by = request.user
            # 自动填入当前时间作为审核时间
            obj.approval_date = timezone.now()
        
        # 调用父类方法保存模型
        super().save_model(request, obj, form, change)


@admin.register(CloudComputerUser)
class CloudComputerUserAdmin(admin.ModelAdmin):
    """
    云电脑用户管理后台
    """
    list_display = [
        'username', 'product', 'status', 'created_at'
    ]
    list_filter = ['status', 'product', 'created_at']
    search_fields = ['username', 'fullname', 'email', 'product__name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('用户信息', {
            'fields': ('username', 'fullname', 'email', 'description')
        }),
        ('产品关联', {
            'fields': ('product',)
        }),
        ('状态权限', {
            'fields': ('status', 'is_admin', 'groups')
        }),
        ('创建信息', {
            'fields': ('created_from_request',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('product', 'product__host', 'created_from_request', 'created_from_request__applicant')

    def save_model(self, request, obj, form, change):
        """
        重写save_model方法，在保存时处理管理员权限变更
        """
        # 检查是否是更新操作并有is_admin字段变更
        if change and 'is_admin' in form.changed_data:
            old_obj = CloudComputerUser.objects.get(pk=obj.pk)
            old_is_admin = old_obj.is_admin
            new_is_admin = obj.is_admin
            
            # 先保存数据库记录
            super().save_model(request, obj, form, change)
            
            # 根据管理员权限变更调用相应的WinRM操作
            if old_is_admin != new_is_admin:
                try:
                    # 连接到产品关联的主机
                    product = obj.product
                    host = product.host
                    client = WinrmClient(
                        hostname=host.hostname,
                        port=host.port,
                        username=host.username,
                        password=host.password,
                        use_ssl=host.use_ssl
                    )
                    
                    if new_is_admin:
                        # 授予管理员权限
                        success = client.op_user(obj.username)
                        if success:
                            self.message_user(request, f'成功为用户 {obj.username} 授予管理员权限')
                        else:
                            self.message_user(request, f'为用户 {obj.username} 授予管理员权限失败', level='error')
                    else:
                        # 剥夺管理员权限
                        success = client.deop_user(obj.username)
                        if success:
                            self.message_user(request, f'成功撤销用户 {obj.username} 的管理员权限')
                        else:
                            self.message_user(request, f'撤销用户 {obj.username} 的管理员权限失败', level='error')
                except Exception as e:
                    self.message_user(request, f'处理管理员权限时发生错误: {str(e)}', level='error')
        else:
            # 新建或没有is_admin字段变更的情况
            super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        """
        修复模板上下文处理问题
        """
        return super().changelist_view(request, extra_context)