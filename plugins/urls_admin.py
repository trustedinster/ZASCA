"""
超管后台 - 插件配置 URL 配置

命名空间: admin_plugins
"""

from django.urls import path

from . import views_admin

app_name = 'admin_plugins'

urlpatterns = [
    # QQ验证配置
    path('', views_admin.admin_qq_list, name='qq_list'),
    path('create/', views_admin.admin_qq_create, name='qq_create'),
    path('<int:pk>/edit/', views_admin.admin_qq_update, name='qq_edit'),
    path('<int:pk>/delete/', views_admin.admin_qq_delete, name='qq_delete'),
]
