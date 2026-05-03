"""
提供商后台 URL 配置

所有 URL 以 /provider/ 为前缀，命名空间为 'provider'。
各子模块通过 include 引入，实现模块化路由。
"""

from django.urls import path, include

from apps.accounts.views_provider import provider_dashboard
from apps.accounts.views_superadmin import (
    superadmin_host_list,
    superadmin_host_provider_assign,
    superadmin_hostgroup_list,
    superadmin_hostgroup_provider_assign,
)
from plugins.dynamic_urls import get_plugin_provider_urls

app_name = 'provider'

urlpatterns = [
    # 仪表盘
    path('', provider_dashboard, name='dashboard'),

    # 主机管理子模块
    path('hosts/', include('apps.hosts.urls_provider')),

    # 运营管理子模块
    path('operations/', include('apps.operations.urls_provider')),

    # 工单管理子模块
    path('tickets/', include('apps.tickets.urls_provider')),

    # 插件配置子模块（动态加载）
    path('plugins/', include('plugins.urls_provider')),
    path('plugins/', include(get_plugin_provider_urls())),

    # 提供商 API
    path('api/', include('apps.provider_backend.api_urls')),

    # 超级管理员 - 提供商分配
    path('superadmin/hosts/', superadmin_host_list, name='superadmin_host_list'),
    path('superadmin/hosts/<int:pk>/providers/', superadmin_host_provider_assign, name='superadmin_host_provider_assign'),
    path('superadmin/host-groups/', superadmin_hostgroup_list, name='superadmin_hostgroup_list'),
    path('superadmin/host-groups/<int:pk>/providers/', superadmin_hostgroup_provider_assign, name='superadmin_hostgroup_provider_assign'),
]
