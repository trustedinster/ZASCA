"""
插件系统 - 提供商后台视图

QQ验证配置的 CRUD 视图，支持提供商数据隔离。
通过 product__created_by=request.user 实现数据隔离。
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView
from django.core.paginator import Paginator

from apps.accounts.provider_decorators import is_provider
from apps.provider.context_mixin import ProviderContextMixin

from .models import QQVerificationConfig
from .forms_provider import QQVerificationConfigForm


class ProviderQQConfigMixin(ProviderContextMixin):
    """
    提供商QQ验证配置数据隔离 Mixin

    - dispatch: 验证提供商身份
    - get_provider_queryset: 限制为当前提供商产品下的QQ验证配置
    """

    provider_url_namespace = 'provider:provider_plugins'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not is_provider(request.user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden(
                '您没有提供商权限，无法访问此页面。'
            )
        return super().dispatch(request, *args, **kwargs)

    def get_provider_queryset(self):
        return QQVerificationConfig.objects.filter(
            product__created_by=self.request.user
        ).select_related(
            'product',
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_nav'] = 'qq_verify'
        context['page_title'] = 'QQ验证配置'
        return context


class QQVerificationConfigListView(ProviderQQConfigMixin, TemplateView):
    template_name = 'admin_base/plugins/qq_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_provider_queryset()

        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                product__display_name__icontains=search
            ) | queryset.filter(
                group_ids__icontains=search
            )

        status_filter = self.request.GET.get(
            'enable_status', ''
        ).strip()
        if status_filter:
            queryset = queryset.filter(enable_status=status_filter)

        paginator = Paginator(queryset, 15)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        context.update({
            'page_obj': page_obj,
            'configs': page_obj,
            'search': search,
            'status_filter': status_filter,
            'enable_status_choices': (
                QQVerificationConfig.ENABLE_STATUS_CHOICES
            ),
            'page_title': 'QQ验证配置',
            'active_nav': 'qq_verify',
        })
        return context


class QQVerificationConfigCreateView(ProviderQQConfigMixin, TemplateView):
    template_name = 'admin_base/plugins/qq_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form': kwargs.get(
                'form',
                QQVerificationConfigForm(
                    provider_user=self.request.user,
                ),
            ),
            'page_title': '创建QQ验证配置',
            'active_nav': 'qq_verify',
            'is_create': True,
        })
        return context

    def post(self, request, *args, **kwargs):
        form = QQVerificationConfigForm(
            request.POST,
            provider_user=request.user,
        )
        if form.is_valid():
            config = form.save()
            messages.success(
                request,
                f'QQ验证配置（{config.product.display_name}）创建成功',
            )
            return redirect('provider_plugins:qq_list')

        return self.render_to_response(
            self.get_context_data(form=form)
        )


class QQVerificationConfigUpdateView(ProviderQQConfigMixin, TemplateView):
    template_name = 'admin_base/plugins/qq_form.html'

    def get_config(self):
        return get_object_or_404(
            self.get_provider_queryset(),
            pk=self.kwargs['pk'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.get_config()
        form = kwargs.get(
            'form',
            QQVerificationConfigForm(
                instance=config,
                provider_user=self.request.user,
            ),
        )
        context.update({
            'form': form,
            'config': config,
            'page_title': f'编辑QQ验证配置 - {config.product.display_name}',
            'active_nav': 'qq_verify',
            'is_create': False,
        })
        return context

    def post(self, request, *args, **kwargs):
        config = self.get_config()
        form = QQVerificationConfigForm(
            request.POST,
            instance=config,
            provider_user=request.user,
        )
        if form.is_valid():
            config = form.save()
            messages.success(
                request,
                f'QQ验证配置（{config.product.display_name}）更新成功',
            )
            return redirect('provider_plugins:qq_list')

        return self.render_to_response(
            self.get_context_data(form=form)
        )


class QQVerificationConfigDeleteView(ProviderQQConfigMixin, TemplateView):
    template_name = 'admin_base/plugins/qq_confirm_delete.html'

    def get_config(self):
        return get_object_or_404(
            self.get_provider_queryset(),
            pk=self.kwargs['pk'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.get_config()

        context.update({
            'config': config,
            'page_title': (
                f'删除QQ验证配置 - {config.product.display_name}'
            ),
            'active_nav': 'qq_verify',
        })
        return context

    def post(self, request, *args, **kwargs):
        config = self.get_config()
        product_name = config.product.display_name
        config.delete()

        messages.success(
            request,
            f'QQ验证配置（{product_name}）已删除',
        )
        return redirect('provider_plugins:qq_list')
