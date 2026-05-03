"""
提供商后台视图

包含仪表盘视图，所有视图均使用 @provider_required 装饰器保护。
统计数据通过 utils.provider 中的函数获取，确保数据隔离的一致性。
"""

from django.shortcuts import render

from apps.accounts.provider_decorators import provider_required
from utils.provider import get_provider_hosts, get_provider_products


@provider_required
def provider_dashboard(request):
    """
    提供商仪表盘视图

    渲染 provider/dashboard.html，传递统计数据到模板。
    所有统计均按 request.user 进行数据隔离。
    """
    user = request.user

    from apps.operations.models import AccountOpeningRequest, CloudComputerUser

    host_count = get_provider_hosts(user).count()
    product_count = get_provider_products(user).count()
    pending_request_count = AccountOpeningRequest.objects.filter(
        target_product__created_by=user, status='pending'
    ).count()
    active_user_count = CloudComputerUser.objects.filter(
        product__created_by=user, status='active'
    ).count()

    context = {
        'host_count': host_count,
        'product_count': product_count,
        'pending_request_count': pending_request_count,
        'active_user_count': active_user_count,
        'stats': {
            'host_count': host_count,
            'product_count': product_count,
            'pending_request_count': pending_request_count,
            'active_user_count': active_user_count,
        },
        'page_title': '仪表盘',
        'active_nav': 'dashboard',
    }

    return render(request, 'admin_base/provider/dashboard.html', context)
