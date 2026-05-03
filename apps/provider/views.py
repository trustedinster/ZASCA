"""
提供商后台视图

包含仪表盘和各模块的占位视图。
所有视图均使用 @provider_required 装饰器保护。
"""

from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from .decorators import provider_required


class ProviderBaseView:
    """
    提供商后台基础视图混入类

    通过重写 dispatch 方法实现提供商身份验证，
    避免在混入类上使用 method_decorator（混入类无 dispatch 方法）。
    """

    def dispatch(self, request, *args, **kwargs):
        from django.shortcuts import redirect
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        from .decorators import is_provider
        if not is_provider(request.user):
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)


# ========== 仪表盘 ==========

class ProviderDashboardView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 统计数据
        from apps.hosts.models import Host, HostGroup
        from apps.operations.models import (
            Product, ProductGroup, AccountOpeningRequest,
            CloudComputerUser, ProductInvitationToken,
            ProductAccessGrant, RdpDomainRoute,
        )

        stats = {
            'host_count': Host.objects.filter(providers=user).count(),
            'hostgroup_count': HostGroup.objects.filter(providers=user).count(),
            'product_count': Product.objects.filter(created_by=user).count(),
            'productgroup_count': ProductGroup.objects.filter(created_by=user).count(),
            'pending_request_count': AccountOpeningRequest.objects.filter(
                target_product__created_by=user, status='pending'
            ).count(),
            'active_user_count': CloudComputerUser.objects.filter(
                product__created_by=user, status='active'
            ).count(),
            'invitation_token_count': ProductInvitationToken.objects.filter(
                created_by=user, is_active=True
            ).count(),
            'access_grant_count': ProductAccessGrant.objects.filter(
                product__created_by=user, is_revoked=False
            ).count(),
            'rdp_route_count': RdpDomainRoute.objects.filter(
                product__created_by=user
            ).count(),
        }

        context['stats'] = stats
        context['page_title'] = '仪表盘'
        context['active_nav'] = 'dashboard'
        return context


# ========== 占位视图（后续实现具体功能） ==========

class HostListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '主机管理'
        context['active_nav'] = 'hosts'
        context['feature_icon'] = 'dns'
        context['feature_name'] = '主机管理'
        return context


class HostGroupListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '主机组'
        context['active_nav'] = 'host_groups'
        context['feature_icon'] = 'folder'
        context['feature_name'] = '主机组'
        return context


class ProductListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '产品管理'
        context['active_nav'] = 'products'
        context['feature_icon'] = 'inventory_2'
        context['feature_name'] = '产品管理'
        return context


class ProductGroupListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '产品组'
        context['active_nav'] = 'product_groups'
        context['feature_icon'] = 'category'
        context['feature_name'] = '产品组'
        return context


class AccountOpeningListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '开户申请'
        context['active_nav'] = 'account_opening'
        context['feature_icon'] = 'how_to_reg'
        context['feature_name'] = '开户申请'
        return context


class CloudUserListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '云电脑用户'
        context['active_nav'] = 'cloud_users'
        context['feature_icon'] = 'people'
        context['feature_name'] = '云电脑用户'
        return context


class InvitationTokenListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '邀请令牌'
        context['active_nav'] = 'invitation_tokens'
        context['feature_icon'] = 'mail'
        context['feature_name'] = '邀请令牌'
        return context


class AccessGrantListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '授权记录'
        context['active_nav'] = 'access_grants'
        context['feature_icon'] = 'key'
        context['feature_name'] = '授权记录'
        return context


class TicketListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '工单管理'
        context['active_nav'] = 'tickets'
        context['feature_icon'] = 'confirmation_number'
        context['feature_name'] = '工单管理'
        return context


class TicketCategoryListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '工单分类'
        context['active_nav'] = 'ticket_categories'
        context['feature_icon'] = 'label'
        context['feature_name'] = '工单分类'
        return context


class ActivityLogView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '活动日志'
        context['active_nav'] = 'activity_log'
        context['feature_icon'] = 'history'
        context['feature_name'] = '活动日志'
        return context


class DomainRouteListView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '域名路由'
        context['active_nav'] = 'domain_routes'
        context['feature_icon'] = 'language'
        context['feature_name'] = '域名路由'
        return context


class QQVerifyView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'QQ验证'
        context['active_nav'] = 'qq_verify'
        context['feature_icon'] = 'verified'
        context['feature_name'] = 'QQ验证'
        return context


class PluginConfigView(ProviderBaseView, TemplateView):
    template_name = 'admin_base/provider/coming_soon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = '插件配置'
        context['active_nav'] = 'plugins'
        context['feature_icon'] = 'extension'
        context['feature_name'] = '插件配置'
        return context
