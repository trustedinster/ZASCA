"""
超管后台 - 工单系统 URL 配置

命名空间: admin_tickets
超管可查看所有工单数据，无数据隔离。
"""

from django.urls import path

from . import views_admin

app_name = 'admin_tickets'

urlpatterns = [
    # 工单管理
    path('', views_admin.admin_ticket_list, name='ticket_list'),
    path('<int:pk>/', views_admin.admin_ticket_detail, name='ticket_detail'),
    path('<int:pk>/comment/', views_admin.admin_ticket_comment_create, name='ticket_comment_create'),

    # 工单批量操作
    path('batch/processing/', views_admin.admin_ticket_batch_processing, name='ticket_batch_processing'),
    path('batch/resolved/', views_admin.admin_ticket_batch_resolved, name='ticket_batch_resolved'),
    path('batch/closed/', views_admin.admin_ticket_batch_closed, name='ticket_batch_closed'),

    # 工单分类管理
    path('categories/', views_admin.admin_category_list, name='category_list'),
    path('categories/create/', views_admin.admin_category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views_admin.admin_category_update, name='category_edit'),
    path('categories/<int:pk>/delete/', views_admin.admin_category_delete, name='category_delete'),

    # 活动日志（只读）
    path('activities/', views_admin.admin_activity_list, name='activity_list'),
]
