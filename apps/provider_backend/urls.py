from django.urls import path, include
from . import views

app_name = 'provider'

urlpatterns = [
    # 仪表盘
    path('', views.DashboardView.as_view(), name='dashboard'),

    # 主机管理
    path('hosts/', views.HostListView.as_view(), name='host_list'),
    path('hosts/create/', views.HostCreateWizard.as_view(), name='host_create'),
    path('hosts/<int:pk>/', views.HostDetailView.as_view(), name='host_detail'),
    path('hosts/<int:pk>/edit/', views.HostUpdateView.as_view(), name='host_update'),
    path('hosts/<int:pk>/deploy/', views.HostDeployView.as_view(), name='host_deploy'),

    # 主机组管理
    path('host-groups/', views.HostGroupListView.as_view(), name='hostgroup_list'),
    path('host-groups/create/', views.HostGroupCreateView.as_view(), name='hostgroup_create'),
    path('host-groups/<int:pk>/edit/', views.HostGroupUpdateView.as_view(), name='hostgroup_update'),

    # 产品管理
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),

    # 产品组管理
    path('product-groups/', views.ProductGroupListView.as_view(), name='productgroup_list'),
    path('product-groups/create/', views.ProductGroupCreateView.as_view(), name='productgroup_create'),
    path('product-groups/<int:pk>/edit/', views.ProductGroupUpdateView.as_view(), name='productgroup_update'),

    # 开户申请管理
    path('account-requests/', views.AccountRequestListView.as_view(), name='accountrequest_list'),
    path('account-requests/<int:pk>/', views.AccountRequestDetailView.as_view(), name='accountrequest_detail'),

    # 云电脑用户管理
    path('cloud-users/', views.CloudUserListView.as_view(), name='clouduser_list'),
    path('cloud-users/<int:pk>/', views.CloudUserDetailView.as_view(), name='clouduser_detail'),

    # 邀请令牌管理
    path('invitation-tokens/', views.InvitationTokenListView.as_view(), name='invitationtoken_list'),
    path('invitation-tokens/create/', views.InvitationTokenCreateView.as_view(), name='invitationtoken_create'),

    # 访问授权管理
    path('access-grants/', views.AccessGrantListView.as_view(), name='accessgrant_list'),

    # 工单管理
    path('tickets/', views.TicketListView.as_view(), name='ticket_list'),
    path('tickets/create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),

    # 工单分类
    path('ticket-categories/', views.TicketCategoryListView.as_view(), name='ticketcategory_list'),

    # 工单活动
    path('ticket-activities/', views.TicketActivityListView.as_view(), name='ticketactivity_list'),

    # RDP路由
    path('rdp-routes/', views.RdpRouteListView.as_view(), name='rdproute_list'),

    # QQ验证配置
    path('qq-config/', views.QQConfigListView.as_view(), name='qqconfig_list'),
    path('qq-config/create/', views.QQConfigCreateView.as_view(), name='qqconfig_create'),
    path('qq-config/<int:pk>/edit/', views.QQConfigUpdateView.as_view(), name='qqconfig_update'),

    # API 端点
    path('api/', include('apps.provider_backend.api_urls')),
]
