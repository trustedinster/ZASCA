"""
工单系统审计日志集成

将工单相关操作记录到审计日志系统
"""

from django.contrib.contenttypes.models import ContentType
from apps.audit.models import AuditLog


def log_ticket_action(ticket, user, action, ip_address=None, details=None, success=True, result=None):
    """
    记录工单操作到审计日志
    
    Args:
        ticket: 工单实例
        user: 操作用户
        action: 操作类型（需要在 AuditLog.ACTION_CHOICES 中定义）
        ip_address: 操作IP地址
        details: 操作详情（字典）
        success: 操作是否成功
        result: 操作结果
    """
    # 获取工单的内容类型
    ticket_content_type = ContentType.objects.get_for_model(ticket)

    # 构建操作详情
    log_details = {
        'ticket_no': ticket.ticket_no,
        'ticket_title': ticket.title,
        'ticket_status': ticket.status,
        'ticket_priority': ticket.priority,
    }

    if details:
        log_details.update(details)

    # 创建审计日志
    AuditLog.objects.create(
        user=user,
        action=action,
        ip_address=ip_address,
        success=success,
        details=log_details,
        result=result,
        content_type=ticket_content_type,
        object_id=ticket.pk
    )


def log_ticket_created(ticket, user, ip_address=None):
    """记录工单创建"""
    log_ticket_action(
        ticket=ticket,
        user=user,
        action='create_ticket',
        ip_address=ip_address,
        details={'action': '创建工单'}
    )


def log_ticket_updated(ticket, user, ip_address=None, changes=None):
    """记录工单更新"""
    log_ticket_action(
        ticket=ticket,
        user=user,
        action='update_ticket',
        ip_address=ip_address,
        details={'action': '更新工单', 'changes': changes or {}}
    )


def log_ticket_assigned(ticket, user, old_assignee, new_assignee, ip_address=None):
    """记录工单分配"""
    log_ticket_action(
        ticket=ticket,
        user=user,
        action='assign_ticket',
        ip_address=ip_address,
        details={
            'action': '分配工单',
            'old_assignee': str(old_assignee) if old_assignee else None,
            'new_assignee': str(new_assignee) if new_assignee else None,
        }
    )


def log_ticket_status_changed(ticket, user, old_status, new_status, ip_address=None):
    """记录工单状态变更"""
    log_ticket_action(
        ticket=ticket,
        user=user,
        action='change_ticket_status',
        ip_address=ip_address,
        details={
            'action': '变更工单状态',
            'old_status': old_status,
            'new_status': new_status,
        }
    )


def log_ticket_closed(ticket, user, ip_address=None, satisfaction=None):
    """记录工单关闭"""
    log_ticket_action(
        ticket=ticket,
        user=user,
        action='close_ticket',
        ip_address=ip_address,
        details={
            'action': '关闭工单',
            'satisfaction': satisfaction,
        }
    )


def log_ticket_comment_added(comment, user, ip_address=None):
    """记录工单评论添加"""
    log_ticket_action(
        ticket=comment.ticket,
        user=user,
        action='add_ticket_comment',
        ip_address=ip_address,
        details={
            'action': '添加评论',
            'comment_id': comment.pk,
            'is_internal': comment.is_internal,
        }
    )
