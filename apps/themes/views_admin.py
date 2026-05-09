"""
主题系统超级管理员视图

包含：
- ThemeConfig 单例编辑 + 清除缓存
- PageContent CRUD
- WidgetLayout CRUD
"""

import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.cache import cache
from django.views.decorators.http import require_POST

from apps.accounts.provider_decorators import superadmin_required
from .models import ThemeConfig, PageContent, WidgetLayout
from .forms_admin import ThemeConfigForm, PageContentForm, WidgetLayoutForm

logger = logging.getLogger('2c2a')


# ============================================================
# ThemeConfig 单例编辑 + 清除缓存
# ============================================================

@superadmin_required
def themeconfig_edit(request):
    """主题配置编辑（单例，自动 get_or_create）"""
    config, _ = ThemeConfig.objects.get_or_create(pk=1)

    if request.method == 'POST':
        form = ThemeConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, '主题配置已更新，缓存已自动清除。')
            return redirect('admin_themes:themeconfig_edit')
    else:
        form = ThemeConfigForm(instance=config)

    context = {
        'form': form,
        'config': config,
        'active_nav': 'themes_config',
    }
    return render(
        request, 'admin_base/themes/themeconfig_edit.html', context
    )


@superadmin_required
@require_POST
def themeconfig_clear_cache(request):
    """清除主题缓存"""
    ThemeConfig.invalidate_cache()
    # 尝试清除页面内容缓存
    if hasattr(cache, 'delete_pattern'):
        try:
            cache.delete_pattern('page_content_*')
        except Exception:
            pass
    else:
        # 手动清除已知位置的页面内容缓存
        for key, _ in PageContent.POSITION_CHOICES:
            cache.delete(f'{PageContent.CACHE_KEY_PREFIX}{key}')
        cache.delete(f'{PageContent.CACHE_KEY_PREFIX}all')

    messages.success(request, '主题缓存已清除。')
    return redirect('admin_themes:themeconfig_edit')


# ============================================================
# PageContent CRUD
# ============================================================

@superadmin_required
def pagecontent_list(request):
    """页面内容列表"""
    queryset = PageContent.objects.order_by('position')

    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            title__icontains=search
        ) | queryset.filter(
            content__icontains=search
        )

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'active_nav': 'themes_pages',
    }
    return render(
        request, 'admin_base/themes/pagecontent_list.html', context
    )


@superadmin_required
def pagecontent_create(request):
    """创建页面内容"""
    if request.method == 'POST':
        form = PageContentForm(request.POST)
        if form.is_valid():
            page = form.save()
            messages.success(
                request, f'页面内容「{page}」创建成功。'
            )
            return redirect('admin_themes:pagecontent_list')
    else:
        form = PageContentForm()

    context = {
        'form': form,
        'active_nav': 'themes_pages',
        'is_create': True,
    }
    return render(
        request, 'admin_base/themes/pagecontent_form.html', context
    )


@superadmin_required
def pagecontent_edit(request, pk):
    """编辑页面内容"""
    page = get_object_or_404(PageContent, pk=pk)

    if request.method == 'POST':
        form = PageContentForm(request.POST, instance=page)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'页面内容「{page}」更新成功。'
            )
            return redirect('admin_themes:pagecontent_list')
    else:
        form = PageContentForm(instance=page)

    context = {
        'form': form,
        'page': page,
        'active_nav': 'themes_pages',
        'is_create': False,
    }
    return render(
        request, 'admin_base/themes/pagecontent_form.html', context
    )


@superadmin_required
def pagecontent_delete(request, pk):
    """删除页面内容"""
    page = get_object_or_404(PageContent, pk=pk)

    if request.method == 'POST':
        label = str(page)
        page.delete()
        messages.success(
            request, f'页面内容「{label}」已删除。'
        )
        return redirect('admin_themes:pagecontent_list')

    context = {
        'page': page,
        'active_nav': 'themes_pages',
    }
    return render(
        request, 'admin_base/themes/pagecontent_confirm_delete.html', context
    )


# ============================================================
# WidgetLayout CRUD
# ============================================================

@superadmin_required
def widgetlayout_list(request):
    """组件布局列表"""
    queryset = WidgetLayout.objects.order_by('display_order')

    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            widget_type__icontains=search
        )

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'active_nav': 'themes_layouts',
    }
    return render(
        request, 'admin_base/themes/widgetlayout_list.html', context
    )


@superadmin_required
def widgetlayout_create(request):
    """创建组件布局"""
    if request.method == 'POST':
        form = WidgetLayoutForm(request.POST)
        if form.is_valid():
            layout = form.save()
            messages.success(
                request, f'组件布局「{layout}」创建成功。'
            )
            return redirect('admin_themes:widgetlayout_list')
    else:
        form = WidgetLayoutForm()

    context = {
        'form': form,
        'active_nav': 'themes_layouts',
        'is_create': True,
    }
    return render(
        request, 'admin_base/themes/widgetlayout_form.html', context
    )


@superadmin_required
def widgetlayout_edit(request, pk):
    """编辑组件布局"""
    layout = get_object_or_404(WidgetLayout, pk=pk)

    if request.method == 'POST':
        form = WidgetLayoutForm(request.POST, instance=layout)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'组件布局「{layout}」更新成功。'
            )
            return redirect('admin_themes:widgetlayout_list')
    else:
        form = WidgetLayoutForm(instance=layout)

    context = {
        'form': form,
        'layout': layout,
        'active_nav': 'themes_layouts',
        'is_create': False,
    }
    return render(
        request, 'admin_base/themes/widgetlayout_form.html', context
    )


@superadmin_required
def widgetlayout_delete(request, pk):
    """删除组件布局"""
    layout = get_object_or_404(WidgetLayout, pk=pk)

    if request.method == 'POST':
        label = str(layout)
        layout.delete()
        messages.success(
            request, f'组件布局「{label}」已删除。'
        )
        return redirect('admin_themes:widgetlayout_list')

    context = {
        'layout': layout,
        'active_nav': 'themes_layouts',
    }
    return render(
        request, 'admin_base/themes/widgetlayout_confirm_delete.html',
        context,
    )
