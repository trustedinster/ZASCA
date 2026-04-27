"""
工单系统管理后台配置

包含数据隔离功能：
- 提供商只能看到自己相关的工单
"""

from typing import Any, Sequence
from django.contrib import admin
from django.http import HttpRequest
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import TicketCategory, Ticket, TicketComment, TicketActivity, TicketAttachment

User = get_user_model()

PROVIDER_GROUP_NAME = "提供商"


def is_provider(user):
    """
    检查用户是否是提供商
    """
    if user.is_superuser:
        return False
    return user.groups.filter(name=PROVIDER_GROUP_NAME).exists()


class ProviderDataIsolationMixin(admin.ModelAdmin):
    """
    提供商数据隔离Mixin
    """

    def get_queryset_for_provider(self, request: HttpRequest, queryset: Any) -> Any:
        """
        为提供商过滤查询集
        """
        return queryset

    def get_queryset(self, request: HttpRequest) -> Any:
        """
        重写get_queryset方法，为提供商过滤数据
        """
        qs = super().get_queryset(request)

        if is_provider(request.user):
            return self.get_queryset_for_provider(request, qs)

        return qs


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    """
    工单分类管理后台
    """

    list_display = [
        "name",
        "icon",
        "default_priority",
        "sla_hours",
        "is_active",
        "display_order",
        "created_at",
    ]
    list_filter = ["is_active", "default_priority", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("基本信息", {"fields": ("name", "description", "icon")}),
        (
            "配置",
            {
                "fields": (
                    "default_priority",
                    "auto_assign_to",
                    "sla_hours",
                )
            },
        ),
        ("显示设置", {"fields": ("is_active", "display_order")}),
        (
            "时间信息",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Ticket)
class TicketAdmin(ProviderDataIsolationMixin, admin.ModelAdmin):
    """
    工单管理后台

    提供商只能看到与自己产品/主机关联的工单
    """

    list_display = [
        "ticket_no",
        "title",
        "category",
        "status",
        "priority",
        "creator",
        "assignee",
        "created_at",
        "due_at",
        "is_overdue_display",
    ]
    list_filter = [
        "status",
        "priority",
        "category",
        "source",
        "created_at",
        "due_at",
    ]
    search_fields = [
        "ticket_no",
        "title",
        "description",
        "creator__username",
        "assignee__username",
    ]
    readonly_fields = [
        "ticket_no",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
    ]
    date_hierarchy = "created_at"

    fieldsets = (
        ("基本信息", {"fields": ("ticket_no", "title", "description", "category")}),
        ("状态信息", {"fields": ("status", "priority", "source")}),
        ("关联信息", {"fields": ("creator", "assignee", "related_product", "related_host")}),
        (
            "时间信息",
            {
                "fields": ("due_at", "resolved_at", "closed_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "满意度",
            {"fields": ("satisfaction", "satisfaction_comment"), "classes": ("collapse",)},
        ),
    )

    def get_queryset_for_provider(self, request, queryset):
        """
        提供商只能看到与自己产品/主机关联的工单
        """
        return queryset.filter(
            models.Q(related_product__created_by=request.user) |
            models.Q(related_host__administrators=request.user)
        ).distinct()

    def is_overdue_display(self, obj):
        """
        显示是否超时
        """
        if obj.is_overdue():
            return "已超时"
        return "-"
    is_overdue_display.short_description = "超时状态"

    def save_model(self, request, obj, form, change):
        """
        保存时记录当前用户
        """
        if not change:
            obj.creator = request.user
        obj._current_user = request.user
        super().save_model(request, obj, form, change)

    actions = ["approve_selected", "resolve_selected", "close_selected"]

    @admin.action(description="标记为处理中")
    def approve_selected(self, request, queryset):
        """
        批量标记为处理中
        """
        updated_count = queryset.filter(status="pending").update(
            status="processing", assignee=request.user
        )
        self.message_user(request, f"成功将 {updated_count} 个工单标记为处理中。")

    @admin.action(description="标记为已解决")
    def resolve_selected(self, request, queryset):
        """
        批量标记为已解决
        """
        updated_count = queryset.filter(status__in=["pending", "processing", "waiting_feedback"]).update(
            status="resolved", resolved_at=timezone.now()
        )
        self.message_user(request, f"成功将 {updated_count} 个工单标记为已解决。")

    @admin.action(description="关闭选中的工单")
    def close_selected(self, request, queryset):
        """
        批量关闭工单
        """
        updated_count = queryset.exclude(status="closed").update(
            status="closed", closed_at=timezone.now()
        )
        self.message_user(request, f"成功关闭了 {updated_count} 个工单。")


@admin.register(TicketComment)
class TicketCommentAdmin(ProviderDataIsolationMixin, admin.ModelAdmin):
    """
    工单评论管理后台
    """

    list_display = ["ticket", "author", "is_internal", "created_at"]
    list_filter = ["is_internal", "created_at"]
    search_fields = ["content", "ticket__ticket_no", "author__username"]
    readonly_fields = ["created_at"]

    def get_queryset_for_provider(self, request, queryset):
        """
        提供商只能看到与自己相关的工单评论
        """
        return queryset.filter(
            models.Q(ticket__related_product__created_by=request.user) |
            models.Q(ticket__related_host__administrators=request.user)
        ).distinct()


@admin.register(TicketActivity)
class TicketActivityAdmin(admin.ModelAdmin):
    """
    工单活动记录管理后台（只读）
    """

    list_display = ["ticket", "actor", "action", "description", "created_at"]
    list_filter = ["action", "created_at"]
    search_fields = ["ticket__ticket_no", "actor__username", "description"]
    readonly_fields = ["ticket", "actor", "action", "old_value", "new_value", "description", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(ProviderDataIsolationMixin, admin.ModelAdmin):
    """
    工单附件管理后台
    """

    list_display = ["ticket", "filename", "uploaded_by", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["filename", "ticket__ticket_no"]
    readonly_fields = ["created_at"]

    def get_queryset_for_provider(self, request, queryset):
        """
        提供商只能看到与自己相关的工单附件
        """
        return queryset.filter(
            models.Q(ticket__related_product__created_by=request.user) |
            models.Q(ticket__related_host__administrators=request.user)
        ).distinct()
