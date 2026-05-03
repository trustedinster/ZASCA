"""
插件系统 - 超管后台视图

QQ验证配置的 CRUD 视图。
超管可管理所有配置；提供商仅可管理自己产品的配置。
"""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator

from apps.accounts.provider_decorators import admin_required
from utils.provider import get_provider_products

from .models import QQVerificationConfig
from .forms_admin import AdminQQVerificationConfigForm


@admin_required
def admin_qq_list(request):
    """
    超管QQ验证配置列表视图

    - 无数据隔离，查看所有配置
    - 支持搜索、启用状态筛选、分页
    """
    if request.user.is_superuser:
        queryset = QQVerificationConfig.objects.select_related(
            'product',
        ).order_by('-created_at')
    else:
        provider_products = get_provider_products(request.user)
        queryset = QQVerificationConfig.objects.filter(
            product__in=provider_products
        ).select_related('product').order_by('-created_at')

    # 搜索
    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(product__display_name__icontains=search)
            | Q(group_ids__icontains=search)
        )

    # 启用状态筛选
    status_filter = request.GET.get('enable_status', '').strip()
    if status_filter:
        queryset = queryset.filter(enable_status=status_filter)

    # 分页
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'configs': page_obj,
        'search': search,
        'status_filter': status_filter,
        'enable_status_choices': (
            QQVerificationConfig.ENABLE_STATUS_CHOICES
        ),
        'page_title': 'QQ验证配置',
        'active_nav': 'admin_plugins_qq',
    }

    return render(request, 'admin_base/plugins/qq_list.html', context)


@admin_required
def admin_qq_create(request):
    """
    超管创建QQ验证配置
    """
    if request.method == 'POST':
        form = AdminQQVerificationConfigForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(
                request,
                f'QQ验证配置（{config.product.display_name}）创建成功',
            )
            return redirect('admin_plugins:qq_list')
    else:
        form = AdminQQVerificationConfigForm()

    context = {
        'form': form,
        'page_title': '创建QQ验证配置',
        'active_nav': 'admin_plugins_qq',
        'is_create': True,
    }

    return render(request, 'admin_base/plugins/qq_form.html', context)


@admin_required
def admin_qq_update(request, pk):
    """
    超管编辑QQ验证配置

    无数据隔离，可编辑所有配置。
    """
    # 数据隔离：提供商仅可编辑自己产品的配置
    if request.user.is_superuser:
        config = get_object_or_404(QQVerificationConfig, pk=pk)
    else:
        provider_products = get_provider_products(request.user)
        config = get_object_or_404(
            QQVerificationConfig, pk=pk,
            product__in=provider_products,
        )

    if request.method == 'POST':
        form = AdminQQVerificationConfigForm(
            request.POST, instance=config
        )
        if form.is_valid():
            config = form.save()
            messages.success(
                request,
                f'QQ验证配置（{config.product.display_name}）更新成功',
            )
            return redirect('admin_plugins:qq_list')
    else:
        form = AdminQQVerificationConfigForm(instance=config)

    context = {
        'form': form,
        'config': config,
        'page_title': f'编辑QQ验证配置 - {config.product.display_name}',
        'active_nav': 'admin_plugins_qq',
        'is_create': False,
    }

    return render(request, 'admin_base/plugins/qq_form.html', context)


@admin_required
def admin_qq_delete(request, pk):
    """
    超管删除QQ验证配置

    无数据隔离，可删除所有配置。
    """
    # 数据隔离：提供商仅可删除自己产品的配置
    if request.user.is_superuser:
        config = get_object_or_404(QQVerificationConfig, pk=pk)
    else:
        provider_products = get_provider_products(request.user)
        config = get_object_or_404(
            QQVerificationConfig, pk=pk,
            product__in=provider_products,
        )

    if request.method == 'POST':
        product_name = config.product.display_name
        config.delete()

        messages.success(
            request,
            f'QQ验证配置（{product_name}）已删除',
        )
        return redirect('admin_plugins:qq_list')

    context = {
        'config': config,
        'page_title': (
            f'删除QQ验证配置 - {config.product.display_name}'
        ),
        'active_nav': 'admin_plugins_qq',
    }

    return render(
        request, 'admin_base/plugins/qq_confirm_delete.html', context
    )
