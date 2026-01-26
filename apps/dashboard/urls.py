"""
仪表盘URL配置
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='index'),

    path('widget-config/', views.WidgetConfigView.as_view(), name='widget_config'),
    path('api/stats/', views.StatsAPIView.as_view(), name='stats_api'),
    path('api/widget-config/', views.WidgetConfigView.as_view(), name='widget_config_api'),
]
