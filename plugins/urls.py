"""
插件系统URL配置
"""

from django.urls import path
from . import views

app_name = 'plugins'

urlpatterns = [
    # 插件管理相关视图
    path('', views.plugin_list, name='plugin_list'),
    path('<str:plugin_id>/', views.plugin_detail, name='plugin_detail'),
    path('<str:plugin_id>/toggle/', views.toggle_plugin, name='toggle_plugin'),
    path('sync/', views.sync_plugins, name='sync_plugins'),
]