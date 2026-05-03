"""
提供商后台 URL 配置

所有 URL 以 /provider/ 为前缀。
"""

from django.urls import path
from . import views

app_name = 'provider'

urlpatterns = [
    # 仪表盘
    path('', views.ProviderDashboardView.as_view(), name='dashboard'),

    # 主机管理
    path('hosts/', views.HostListView.as_view(), name='hosts'),

    # 主机组
    path('host-groups/', views.HostGroupListView.as_view(), name='host_groups'),

    # 产品管理
    path('products/', views.ProductListView.as_view(), name='products'),

    # 产品组
    path('product-groups/', views.ProductGroupListView.as_view(),
         name='product_groups'),

    # 开户申请
    path('account-opening/', views.AccountOpeningListView.as_view(),
         name='account_opening'),

    # 云电脑用户
    path('cloud-users/', views.CloudUserListView.as_view(),
         name='cloud_users'),

    # 邀请令牌
    path('invitation-tokens/', views.InvitationTokenListView.as_view(),
         name='invitation_tokens'),

    # 授权记录
    path('access-grants/', views.AccessGrantListView.as_view(),
         name='access_grants'),

    # 工单管理
    path('tickets/', views.TicketListView.as_view(), name='tickets'),

    # 工单分类
    path('ticket-categories/', views.TicketCategoryListView.as_view(),
         name='ticket_categories'),

    # 活动日志
    path('activity-log/', views.ActivityLogView.as_view(),
         name='activity_log'),

    # 域名路由
    path('domain-routes/', views.DomainRouteListView.as_view(),
         name='domain_routes'),

    # QQ验证
    path('qq-verify/', views.QQVerifyView.as_view(), name='qq_verify'),

    # 插件配置
    path('plugins/', views.PluginConfigView.as_view(), name='plugins'),
]
