"""
仪表盘超级管理员视图

包含：
- DashboardWidget CRUD
- SystemConfig 单例编辑 + 发送测试邮件
"""

import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.provider_decorators import superadmin_required
from .models import DashboardWidget, SystemConfig
from .forms_admin import DashboardWidgetForm, SystemConfigForm

logger = logging.getLogger('zasca')


# ============================================================
# DashboardWidget CRUD
# ============================================================

@superadmin_required
def widget_list(request):
    """仪表盘组件列表"""
    queryset = DashboardWidget.objects.order_by('display_order')

    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            title__icontains=search
        ) | queryset.filter(
            widget_type__icontains=search
        )

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'active_nav': 'dashboard_widgets',
    }
    return render(request, 'admin_base/dashboard/widget_list.html', context)


@superadmin_required
def widget_create(request):
    """创建仪表盘组件"""
    if request.method == 'POST':
        form = DashboardWidgetForm(request.POST)
        if form.is_valid():
            widget = form.save()
            messages.success(
                request, f'仪表盘组件「{widget.title}」创建成功。'
            )
            return redirect('admin:admin_dashboard_config:widget_list')
    else:
        form = DashboardWidgetForm()

    context = {
        'form': form,
        'active_nav': 'dashboard_widgets',
        'is_create': True,
    }
    return render(request, 'admin_base/dashboard/widget_form.html', context)


@superadmin_required
def widget_edit(request, pk):
    """编辑仪表盘组件"""
    widget = get_object_or_404(DashboardWidget, pk=pk)

    if request.method == 'POST':
        form = DashboardWidgetForm(request.POST, instance=widget)
        if form.is_valid():
            widget = form.save()
            messages.success(
                request, f'仪表盘组件「{widget.title}」更新成功。'
            )
            return redirect('admin:admin_dashboard_config:widget_list')
    else:
        form = DashboardWidgetForm(instance=widget)

    context = {
        'form': form,
        'widget': widget,
        'active_nav': 'dashboard_widgets',
        'is_create': False,
    }
    return render(request, 'admin_base/dashboard/widget_form.html', context)


@superadmin_required
def widget_delete(request, pk):
    """删除仪表盘组件"""
    widget = get_object_or_404(DashboardWidget, pk=pk)

    if request.method == 'POST':
        title = widget.title
        widget.delete()
        messages.success(
            request, f'仪表盘组件「{title}」已删除。'
        )
        return redirect('admin:admin_dashboard_config:widget_list')

    context = {
        'widget': widget,
        'active_nav': 'dashboard_widgets',
    }
    return render(
        request, 'admin_base/dashboard/widget_confirm_delete.html', context
    )


# ============================================================
# SystemConfig 单例编辑 + 发送测试邮件
# ============================================================

@superadmin_required
def systemconfig_edit(request):
    """系统配置编辑（单例，自动 get_or_create）"""
    config, _ = SystemConfig.objects.get_or_create(pk=1)

    if request.method == 'POST':
        form = SystemConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, '系统配置已更新。')
            return redirect('admin:admin_dashboard_config:systemconfig_edit')
    else:
        form = SystemConfigForm(instance=config)

    context = {
        'form': form,
        'config': config,
        'active_nav': 'dashboard_config',
    }
    return render(
        request, 'admin_base/dashboard/systemconfig_edit.html', context
    )


@superadmin_required
@require_POST
def systemconfig_send_test_email(request):
    """发送测试邮件"""
    config = get_object_or_404(SystemConfig, pk=1)
    test_email = None

    try:
        test_email = (
            request.POST.get('test_email')
            or request.user.email
            or config.smtp_from_email
        )

        if not test_email:
            messages.error(request, '未提供测试邮箱地址。')
            return redirect('admin:admin_dashboard_config:systemconfig_edit')

        subject = 'ZASCA 测试邮件'
        html_body = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{subject}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #eee;
                }}
                .header {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-bottom: 1px solid #dee2e6;
                }}
                .content {{ padding: 20px 0; }}
                .footer {{
                    padding: 20px 0;
                    text-align: center;
                    border-top: 1px solid #dee2e6;
                    color: #6c757d;
                    font-size: 12px;
                }}
                .highlight {{
                    background-color: #e7f3ff;
                    padding: 15px;
                    border-left: 4px solid #007bff;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>ZASCA 验证码服务</h2>
                </div>
                <div class="content">
                    <p>您好！</p>
                    <div class="highlight">
                        <p><strong>这是一封测试邮件，用于验证邮件配置是否正确。</strong></p>
                    </div>
                    <p>系统配置的SMTP服务器可以正常发送邮件。</p>
                    <p>测试时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 ZASCA. All rights reserved.</p>
                    <p>此邮件由系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        '''

        text_body = (
            f'这是一封测试邮件，用于验证邮件配置是否正确。'
            f'测试时间: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )

        from apps.accounts.email_service import EmailService
        email_service = EmailService.from_system_config(config)
        email_service.send_email(
            to_emails=[test_email],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

        messages.success(request, f'测试邮件已成功发送至 {test_email}！')
        logger.info(
            f"测试邮件发送成功 - 用户: {request.user.username}, "
            f"目标: {test_email}"
        )
    except Exception as e:
        error_msg = f'测试邮件发送失败: {str(e)}'
        messages.error(request, error_msg)
        logger.error(
            f"测试邮件发送失败 - 用户: {request.user.username}, "
            f"错误: {str(e)}"
        )

    return redirect('admin:admin_dashboard_config:systemconfig_edit')
