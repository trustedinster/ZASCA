"""
仪表盘视图
"""
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

from apps.hosts.models import Host
from .models import SystemStats, DashboardWidget, UserActivity

User = get_user_model()


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    仪表盘主视图
    展示系统概况、主机状态、操作统计等信息
    """
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        """获取仪表盘上下文数据"""
        context = super().get_context_data(**kwargs)

        # 获取基本统计数据
        context['total_users'] = User.objects.count()
        context['total_hosts'] = Host.objects.count()
        context['active_hosts'] = Host.objects.filter(status='online').count()
        # 由于已移除 OperationLog，暂时返回空列表
        context['recent_operations'] = []

        # 获取主机状态分布
        host_status_stats = Host.objects.values('status').annotate(
            count=Count('id')
        )
        context['host_status_stats'] = {
            stat['status']: stat['count'] 
            for stat in host_status_stats
        }

        # 由于已移除 OperationLog，暂时返回空趋势数据
        context['operation_trend'] = []

        # 获取启用的仪表盘组件
        context['widgets'] = DashboardWidget.objects.filter(
            is_enabled=True
        ).order_by('display_order')

        # 记录用户访问活动
        UserActivity.objects.create(
            user=self.request.user,
            activity_type='dashboard_view',
            description='访问仪表盘',
            ip_address=self.get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        return context

    @staticmethod
    def get_client_ip(request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class StatsAPIView(LoginRequiredMixin, View):
    """
    统计数据API视图
    提供JSON格式的统计数据
    """

    def get(self, request, *args, **kwargs):
        """获取统计数据"""
        stats_type = request.GET.get('type', 'all')

        if stats_type == 'all':
            data = self._get_all_stats()
        elif stats_type == 'hosts':
            data = self._get_host_stats()
        elif stats_type == 'operations':
            data = self._get_operation_stats()
        elif stats_type == 'users':
            data = self._get_user_stats()
        else:
            data = {'error': 'Invalid stats type'}

        return JsonResponse(data)

    def _get_all_stats(self):
        """获取所有统计数据"""
        return {
            'hosts': self._get_host_stats(),
            'operations': self._get_operation_stats(),
            'users': self._get_user_stats()
        }

    def _get_host_stats(self):
        """获取主机统计"""
        hosts = Host.objects.all()
        return {
            'total': hosts.count(),
            'online': hosts.filter(status='online').count(),
            'offline': hosts.filter(status='offline').count(),
            'error': hosts.filter(status='error').count(),
            'by_type': dict(hosts.values('host_type').annotate(
                count=Count('id')
            ).values_list('host_type', 'count'))
        }

    def _get_operation_stats(self):
        """获取操作统计"""
        # 由于已移除 OperationLog，返回空统计
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'recent_7_days': 0,
            'by_type': {}
        }

    def _get_user_stats(self):
        """获取用户统计"""
        users = User.objects.all()
        seven_days_ago = timezone.now() - timedelta(days=7)

        return {
            'total': users.count(),
            'active': users.filter(is_active=True).count(),
            'recent_7_days': users.filter(
                date_joined__gte=seven_days_ago
            ).count()
        }


class WidgetConfigView(LoginRequiredMixin, View):
    """
    仪表盘组件配置视图
    用于管理仪表盘组件的显示和配置
    """

    def get(self, request, *args, **kwargs):
        """渲染组件配置页面"""
        widgets = DashboardWidget.objects.all()
        context = {
            'widgets': widgets
        }
        return render(request, 'dashboard/widget_config.html', context)

    def post(self, request, *args, **kwargs):
        """更新组件配置"""
        import json
        try:
            data = json.loads(request.body)
            widgets_data = data.get('widgets', [])
            
            for widget_data in widgets_data:
                widget_id = widget_data.get('widget_id')
                is_enabled = widget_data.get('is_enabled', False)
                display_order = widget_data.get('display_order', 0)
                
                try:
                    widget = DashboardWidget.objects.get(id=widget_id)
                    widget.is_enabled = is_enabled
                    widget.display_order = display_order
                    widget.save()
                except DashboardWidget.DoesNotExist:
                    return JsonResponse(
                        {'status': 'error', 'message': f'Widget {widget_id} not found'},
                        status=404
                    )
            
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid JSON data'},
                status=400
            )