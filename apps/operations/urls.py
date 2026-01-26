"""
操作记录URL配置
"""
from django.urls import path
from . import views

app_name = 'operations'

urlpatterns = [
    # 系统任务相关URL
    path('tasks/', views.SystemTaskListView.as_view(), name='task_list'),
    path('tasks/<int:pk>/', views.SystemTaskDetailView.as_view(), name='task_detail'),
    
    # 开户申请相关URL
    path('account-openings/', views.AccountOpeningRequestListView.as_view(), name='account_opening_list'),
    path('account-openings/create/', views.AccountOpeningRequestCreateView.as_view(), name='account_opening_create'),
    path('account-openings/confirm/', views.account_opening_confirm, name='account_opening_confirm'),
    path('account-openings/submit/', views.account_opening_submit, name='account_opening_submit'),
    path('account-openings/approve/<int:pk>/', views.approve_account_request, name='account_opening_approve'),
    path('account-openings/reject/<int:pk>/', views.reject_account_request, name='account_opening_reject'),
    path('account-openings/process/<int:pk>/', views.process_account_request, name='account_opening_process'),
    path('account-openings/<int:pk>/', views.account_opening_detail, name='account_opening_detail'),
    
    # 云电脑用户相关URL
    path('cloud-users/', views.CloudComputerUserListView.as_view(), name='cloud_user_list'),
    path('cloud-users/<int:pk>/toggle-status/', views.toggle_cloud_user_status, name='cloud_user_toggle_status'),
]