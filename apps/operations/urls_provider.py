"""
运营管理 - 提供商后台 URL 配置

开户申请、邀请令牌、访问授权、RDP域名路由、系统任务、
产品管理、产品组管理相关路由，
挂载在 /provider/operations/ 下。
命名空间: provider_operations
"""

from django.urls import path

from . import views_provider

app_name = 'provider_operations'

urlpatterns = [
    # ---- 产品管理 ----
    path(
        'products/',
        views_provider.ProductListView.as_view(),
        name='product_list',
    ),
    path(
        'products/create/',
        views_provider.ProductCreateView.as_view(),
        name='product_create',
    ),
    path(
        'products/<int:pk>/',
        views_provider.ProductDetailView.as_view(),
        name='product_detail',
    ),
    path(
        'products/<int:pk>/edit/',
        views_provider.ProductUpdateView.as_view(),
        name='product_edit',
    ),
    path(
        'products/<int:pk>/delete/',
        views_provider.ProductDeleteView.as_view(),
        name='product_delete',
    ),

    # ---- 产品组管理 ----
    path(
        'product-groups/',
        views_provider.ProductGroupListView.as_view(),
        name='productgroup_list',
    ),
    path(
        'product-groups/create/',
        views_provider.ProductGroupCreateView.as_view(),
        name='productgroup_create',
    ),
    path(
        'product-groups/<int:pk>/edit/',
        views_provider.ProductGroupUpdateView.as_view(),
        name='productgroup_edit',
    ),
    path(
        'product-groups/<int:pk>/delete/',
        views_provider.ProductGroupDeleteView.as_view(),
        name='productgroup_delete',
    ),

    # ---- 云电脑用户 ----
    path(
        'users/',
        views_provider.CloudComputerUserListView.as_view(),
        name='user_list',
    ),
    path(
        'users/<int:pk>/',
        views_provider.CloudComputerUserDetailView.as_view(),
        name='user_detail',
    ),
    path(
        'users/<int:pk>/sync-admin/',
        views_provider.CloudComputerUserSyncAdminView.as_view(),
        name='user_sync_admin',
    ),
    path(
        'users/<int:pk>/disk-quota/',
        views_provider.CloudComputerUserSetDiskQuotaView.as_view(),
        name='user_disk_quota',
    ),
    path(
        'users/<int:pk>/reset-password/',
        views_provider.CloudComputerUserResetPasswordView.as_view(),
        name='user_reset_password',
    ),
    path(
        'users/batch-activate/',
        views_provider.CloudComputerUserBatchActivateView.as_view(),
        name='user_batch_activate',
    ),
    path(
        'users/batch-deactivate/',
        views_provider.CloudComputerUserBatchDeactivateView.as_view(),
        name='user_batch_deactivate',
    ),
    path(
        'users/batch-disable/',
        views_provider.CloudComputerUserBatchDisableView.as_view(),
        name='user_batch_disable',
    ),

    # ---- 开户申请 ----
    path(
        'requests/',
        views_provider.AccountOpeningRequestListView.as_view(),
        name='request_list',
    ),
    # 批量批准（必须在 <int:pk> 之前，避免路径冲突）
    path(
        'requests/batch-approve/',
        views_provider.AccountOpeningRequestBatchApproveView.as_view(),
        name='request_batch_approve',
    ),
    # 批量驳回（必须在 <int:pk> 之前，避免路径冲突）
    path(
        'requests/batch-reject/',
        views_provider.AccountOpeningRequestBatchRejectView.as_view(),
        name='request_batch_reject',
    ),
    # 开户申请详情
    path(
        'requests/<int:pk>/',
        views_provider.AccountOpeningRequestDetailView.as_view(),
        name='request_detail',
    ),
    # 批准单条申请
    path(
        'requests/<int:pk>/approve/',
        views_provider.AccountOpeningRequestApproveView.as_view(),
        name='request_approve',
    ),
    # 驳回单条申请
    path(
        'requests/<int:pk>/reject/',
        views_provider.AccountOpeningRequestRejectView.as_view(),
        name='request_reject',
    ),
    # 执行开户
    path(
        'requests/<int:pk>/execute/',
        views_provider.AccountOpeningRequestExecuteView.as_view(),
        name='request_execute',
    ),

    # ---- 邀请令牌 ----
    path(
        'tokens/',
        views_provider.ProductInvitationTokenListView.as_view(),
        name='token_list',
    ),
    path(
        'tokens/<int:pk>/',
        views_provider.ProductInvitationTokenDetailView.as_view(),
        name='token_detail',
    ),
    path(
        'tokens/create/',
        views_provider.ProductInvitationTokenCreateView.as_view(),
        name='token_create',
    ),
    path(
        'tokens/batch-enable/',
        views_provider.ProductInvitationTokenBatchEnableView.as_view(),
        name='token_batch_enable',
    ),
    path(
        'tokens/batch-disable/',
        views_provider.ProductInvitationTokenBatchDisableView.as_view(),
        name='token_batch_disable',
    ),

    # ---- 访问授权 ----
    path(
        'grants/',
        views_provider.ProductAccessGrantListView.as_view(),
        name='grant_list',
    ),
    path(
        'grants/batch-revoke/',
        views_provider.ProductAccessGrantBatchRevokeView.as_view(),
        name='grant_batch_revoke',
    ),

    # ---- RDP 域名路由 ----
    path(
        'routes/',
        views_provider.RdpDomainRouteListView.as_view(),
        name='route_list',
    ),

    # ---- 系统任务（只读参考） ----
    path(
        'tasks/',
        views_provider.SystemTaskListView.as_view(),
        name='task_list',
    ),
]
