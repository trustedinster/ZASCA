"""
主机管理 - 提供商后台 URL 配置

所有 URL 以 /provider/hosts/ 为前缀，命名空间为 'provider_hosts'。
完整命名空间为 'provider:provider_hosts:'。
"""

from django.urls import path

from . import views_provider

app_name = 'provider_hosts'

urlpatterns = [
    path(
        '',
        views_provider.HostListView.as_view(),
        name='host_list'
    ),
    path(
        'create/',
        views_provider.HostCreateView.as_view(),
        name='host_create'
    ),
    path(
        '<int:pk>/',
        views_provider.HostDetailView.as_view(),
        name='host_detail'
    ),
    path(
        '<int:pk>/edit/',
        views_provider.HostUpdateView.as_view(),
        name='host_edit'
    ),
    path(
        '<int:pk>/delete/',
        views_provider.HostDeleteView.as_view(),
        name='host_delete'
    ),
    path(
        '<int:pk>/deploy/',
        views_provider.HostDeployCommandView.as_view(),
        name='host_deploy'
    ),
    path(
        '<int:pk>/toggle/',
        views_provider.HostToggleActiveView.as_view(),
        name='host_toggle'
    ),

    # 主机组管理
    path(
        'groups/',
        views_provider.HostGroupListView.as_view(),
        name='hostgroup_list'
    ),
    path(
        'groups/create/',
        views_provider.HostGroupCreateView.as_view(),
        name='hostgroup_create'
    ),
    path(
        'groups/<int:pk>/edit/',
        views_provider.HostGroupUpdateView.as_view(),
        name='hostgroup_edit'
    ),
    path(
        'groups/<int:pk>/delete/',
        views_provider.HostGroupDeleteView.as_view(),
        name='hostgroup_delete'
    ),
]
