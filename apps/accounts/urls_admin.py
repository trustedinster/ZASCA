"""
超管后台 URL 配置

所有 URL 以 /admin/ 为前缀，命名空间为 'admin'。
各子模块通过 include 引入，实现模块化路由。
此模块完全替代 Django Admin。
"""

from django.urls import path, include

from apps.accounts.views_admin import admin_dashboard
from plugins.dynamic_urls import get_plugin_admin_urls

app_name = 'admin'

urlpatterns = [
    # 仪表盘
    path('', admin_dashboard, name='dashboard'),

    # 用户与权限
    path('users/', include('apps.accounts.urls_admin_users')),
    path('groups/', include('apps.accounts.urls_admin_groups')),

    # 提供商分配
    path('providers/', include('apps.accounts.urls_admin_providers')),

    # 主机与产品
    path('hosts/', include('apps.hosts.urls_admin')),

    # 运营管理
    path('operations/', include('apps.operations.urls_admin')),

    # 工单系统
    path('tickets/', include('apps.tickets.urls_admin')),

    # 插件配置（动态加载）
    path('plugins/', include('plugins.urls_admin')),
    path('plugins/', include(get_plugin_admin_urls())),

    # 审计日志
    path('audit/', include('apps.audit.urls_admin')),

    # 仪表盘组件配置
    path('dashboard/', include('apps.dashboard.urls_admin')),

    # 主题配置
    path('themes/', include('apps.themes.urls_admin')),
]
