"""
审计日志超级管理员视图

审计日志为只读，不支持创建/编辑/删除操作。
"""

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator

from apps.accounts.provider_decorators import superadmin_required
from .models import AuditLog


@superadmin_required
def auditlog_list(request):
    """
    审计日志列表视图（只读）

    支持按用户、操作类型、时间范围筛选，支持搜索。
    """
    queryset = AuditLog.objects.select_related(
        'user', 'host'
    ).order_by('-timestamp')

    # 搜索
    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            action__icontains=search
        ) | queryset.filter(
            user__username__icontains=search
        ) | queryset.filter(
            host__name__icontains=search
        ) | queryset.filter(
            ip_address__icontains=search
        )

    # 操作类型筛选
    action_filter = request.GET.get('action', '').strip()
    if action_filter:
        queryset = queryset.filter(action=action_filter)

    # 用户筛选
    user_filter = request.GET.get('user', '').strip()
    if user_filter:
        queryset = queryset.filter(user__username__icontains=user_filter)

    # 时间范围筛选
    timestamp_from = request.GET.get('timestamp_from', '').strip()
    if timestamp_from:
        queryset = queryset.filter(timestamp__gte=timestamp_from)

    timestamp_to = request.GET.get('timestamp_to', '').strip()
    if timestamp_to:
        queryset = queryset.filter(timestamp__lte=timestamp_to)

    # 分页
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'timestamp_from': timestamp_from,
        'timestamp_to': timestamp_to,
        'action_choices': AuditLog.ACTION_CHOICES,
        'active_nav': 'audit',
    }

    return render(request, 'admin_base/audit/auditlog_list.html', context)


@superadmin_required
def auditlog_detail(request, pk):
    """
    审计日志详情视图（只读）
    """
    log = get_object_or_404(
        AuditLog.objects.select_related('user', 'host', 'content_type'),
        pk=pk
    )

    context = {
        'log': log,
        'active_nav': 'audit',
    }

    return render(request, 'admin_base/audit/auditlog_detail.html', context)
