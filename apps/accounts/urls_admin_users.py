"""
超管后台 - 用户管理 URL 配置

命名空间: admin_users (通过 admin: 命名空间访问)
"""

from django.urls import path

from . import views_admin_users as views

app_name = 'admin_users'

urlpatterns = [
    # 用户列表
    path('', views.user_list, name='user_list'),

    # 创建用户
    path('create/', views.user_create, name='user_create'),

    # 编辑用户
    path('<int:pk>/edit/', views.user_update, name='user_edit'),

    # 删除用户
    path('<int:pk>/delete/', views.user_delete, name='user_delete'),

    # 切换激活状态
    path('<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),

    # 重置密码
    path('<int:pk>/reset-password/', views.user_reset_password, name='user_reset_password'),
]
