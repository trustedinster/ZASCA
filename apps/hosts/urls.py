"""
主机管理URL配置
"""
from django.urls import path
from . import views

app_name = 'hosts'

urlpatterns = [
    # 主机相关URL
    path('', views.HostListView.as_view(), name='list'),
    path('groups/', views.HostGroupListView.as_view(), name='group_list'),
    path('<int:pk>/', views.HostDetailView.as_view(), name='detail'),
    # API端点
    path('api/list/', views.api_hosts_list, name='api_list'),
    path('api/<int:host_id>/test-connection/', views.test_host_connection, name='test_connection'),
]