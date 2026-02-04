"""
错误处理 URL 配置
"""
from django.urls import path
from . import views

# 错误处理器
handler400 = 'apps.errors.handler400'
handler403 = 'apps.errors.handler403'
handler404 = 'apps.errors.handler404'
handler500 = 'apps.errors.handler500'

urlpatterns = [
    # 可以添加错误页面测试路由
    # path('403/', views.handler_test403, name='test_403'),
    # path('404/', views.handler_test404, name='test_404'),
    # path('500/', views.handler_test500, name='test_500'),
]