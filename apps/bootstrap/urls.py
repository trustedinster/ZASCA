from django.urls import path
from . import views

app_name = 'bootstrap'

urlpatterns = [
    # 引导配置API
    path('config/', views.get_bootstrap_config, name='get_bootstrap_config'),
    path('trigger/', views.trigger_host_bootstrap, name='trigger_host_bootstrap'),
    path('create-token/', views.create_bootstrap_token, name='create_bootstrap_token'),
    path('status/', views.check_bootstrap_status, name='check_bootstrap_status'),
    path('validate-token/', views.validate_bootstrap_token, name='validate_bootstrap_token'),
    
    # 引导管理API
    path('manage/', views.BootstrapManagementView.as_view(), name='bootstrap_management'),
]