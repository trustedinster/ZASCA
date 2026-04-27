"""
工单系统通知模块

支持邮件通知和站内通知
"""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.tasks.models import AsyncTask


def send_ticket_email(subject, template_name, context, recipient_list):
    """
    发送工单相关邮件

    Args:
        subject: 邮件主题
        template_name: 邮件模板名称
        context: 模板上下文
        recipient_list: 收件人列表
    """
    if not recipient_list:
        return

    # 渲染邮件内容
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)

    # 发送邮件
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@zasca.com'),
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=True
    )


def notify_ticket_created(ticket):
    """
    通知工单创建
    - 通知管理员
    - 通知自动分配的处理人
    """
    # 构建邮件上下文
    context = {
        'ticket': ticket,
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }

    # 通知处理人（如果有自动分配）
    if ticket.assignee and ticket.assignee.email:
        send_ticket_email(
            subject=f'[ZASCA] 新工单分配 - {ticket.ticket_no}',
            template_name='tickets/email/assigned.html',
            context=context,
            recipient_list=[ticket.assignee.email]
        )


def notify_ticket_assigned(ticket, old_assignee=None):
    """
    通知工单分配
    - 通知新的处理人
    """
    if not ticket.assignee or not ticket.assignee.email:
        return

    context = {
        'ticket': ticket,
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'old_assignee': old_assignee,
    }

    send_ticket_email(
        subject=f'[ZASCA] 工单分配通知 - {ticket.ticket_no}',
        template_name='tickets/email/assigned.html',
        context=context,
        recipient_list=[ticket.assignee.email]
    )


def notify_ticket_status_changed(ticket, old_status, new_status):
    """
    通知工单状态变更
    - 通知创建者
    """
    if not ticket.creator or not ticket.creator.email:
        return

    # 如果创建者自己变更状态，不发送通知
    # 这里简化处理，实际应该传入操作人参数

    context = {
        'ticket': ticket,
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'old_status': old_status,
        'new_status': new_status,
    }

    send_ticket_email(
        subject=f'[ZASCA] 工单状态更新 - {ticket.ticket_no}',
        template_name='tickets/email/status_update.html',
        context=context,
        recipient_list=[ticket.creator.email]
    )


def notify_ticket_closed(ticket):
    """
    通知工单关闭
    - 通知创建者
    - 邀请评价
    """
    if not ticket.creator or not ticket.creator.email:
        return

    context = {
        'ticket': ticket,
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }

    send_ticket_email(
        subject=f'[ZASCA] 工单已关闭 - {ticket.ticket_no}',
        template_name='tickets/email/closed.html',
        context=context,
        recipient_list=[ticket.creator.email]
    )


def notify_new_comment(comment):
    """
    通知新评论
    - 通知工单相关人员
    """
    ticket = comment.ticket

    # 收集需要通知的用户
    recipients = []

    # 通知创建者（如果不是评论者自己）
    if ticket.creator and ticket.creator.email and ticket.creator != comment.author:
        recipients.append(ticket.creator.email)

    # 通知处理人（如果不是评论者自己）
    if ticket.assignee and ticket.assignee.email and ticket.assignee != comment.author:
        recipients.append(ticket.assignee.email)

    if not recipients:
        return

    context = {
        'ticket': ticket,
        'comment': comment,
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }

    send_ticket_email(
        subject=f'[ZASCA] 工单新评论 - {ticket.ticket_no}',
        template_name='tickets/email/new_comment.html',
        context=context,
        recipient_list=recipients
    )


def notify_overdue_ticket(ticket):
    """
    通知工单即将超时或已超时
    - 通知处理人
    - 通知管理员
    """
    if not ticket.assignee or not ticket.assignee.email:
        return

    context = {
        'ticket': ticket,
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }

    send_ticket_email(
        subject=f'[ZASCA] 工单即将超时 - {ticket.ticket_no}',
        template_name='tickets/email/overdue.html',
        context=context,
        recipient_list=[ticket.assignee.email]
    )
