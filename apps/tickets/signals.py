"""
工单系统信号处理

处理工单相关的信号，包括：
- 工单创建通知
- 工单分配通知
- 工单状态变更通知
- 工单关闭通知
- 评论添加通知
- 审计日志记录
"""

from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import (
    ticket_created, ticket_assigned, ticket_status_changed,
    ticket_closed, ticket_comment_added, TicketActivity
)

User = get_user_model()


@receiver(ticket_created)
def on_ticket_created(sender, instance, **kwargs):
    """
    工单创建时的信号处理
    - 记录创建活动
    - 发送通知给管理员
    """
    # 创建活动记录已在模型 save 方法中处理
    # 这里可以添加额外的通知逻辑
    pass


@receiver(ticket_assigned)
def on_ticket_assigned(sender, instance, **kwargs):
    """
    工单分配时的信号处理
    - 发送通知给处理人
    """
    if instance.assignee:
        # 可以在这里发送邮件通知或站内通知
        pass


@receiver(ticket_status_changed)
def on_ticket_status_changed(sender, instance, old_status, new_status, **kwargs):
    """
    工单状态变更时的信号处理
    - 发送通知给创建者
    - 检查SLA
    """
    # 状态变更活动记录已在模型 save 方法中处理
    # 可以在这里添加通知逻辑
    pass


@receiver(ticket_closed)
def on_ticket_closed(sender, instance, **kwargs):
    """
    工单关闭时的信号处理
    - 发送满意度评价邀请
    """
    # 可以在这里发送评价邀请邮件
    pass


@receiver(ticket_comment_added)
def on_ticket_comment_added(sender, instance, **kwargs):
    """
    评论添加时的信号处理
    - 通知相关人员
    """
    # 评论活动记录已在模型 save 方法中处理
    # 可以在这里添加通知逻辑
    pass
