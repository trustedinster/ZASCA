from django.urls import path
from . import views

app_name = 'bootstrap'

urlpatterns = [
    # 引导配置API
    path('config/', views.get_bootstrap_config, name='get_bootstrap_config'),
    path('trigger/', views.trigger_host_bootstrap, name='trigger_host_bootstrap'),
    path('create-initial-token/', views.create_initial_token, name='create_initial_token'),
    path('status/', views.check_bootstrap_status, name='check_bootstrap_status'),
    path('validate-token/', views.validate_bootstrap_token, name='validate_bootstrap_token'),
    
    # 引导管理API
    path('manage/', views.BootstrapManagementView.as_view(), name='bootstrap_management'),
    
    # 新增API端点 - 根据规范
    path('verify-totp/', views.verify_totp, name='verify_totp'),
    path('exchange-token/', views.exchange_token, name='exchange_token'),
    path('session/', views.revoke_session, name='revoke_session'),
    
    # API端点别名 - 为H端提供兼容路径
    path('api/verify_totp/', views.verify_totp, name='api_verify_totp'),
    path('api/exchange_token/', views.exchange_token, name='api_exchange_token'),
    path('api/session/', views.revoke_session, name='api_revoke_session'),
]