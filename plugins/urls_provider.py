"""
插件系统 - 提供商后台 URL 配置

QQ验证配置相关路由，
挂载在 /provider/plugins/ 下。
命名空间: provider_plugins
"""

from django.urls import path

from . import views_provider

app_name = 'provider_plugins'

urlpatterns = [
    # ---- QQ验证配置 ----
    path(
        '',
        views_provider.QQVerificationConfigListView.as_view(),
        name='qq_list',
    ),
    path(
        'create/',
        views_provider.QQVerificationConfigCreateView.as_view(),
        name='qq_create',
    ),
    path(
        '<int:pk>/edit/',
        views_provider.QQVerificationConfigUpdateView.as_view(),
        name='qq_edit',
    ),
    path(
        '<int:pk>/delete/',
        views_provider.QQVerificationConfigDeleteView.as_view(),
        name='qq_delete',
    ),
]
