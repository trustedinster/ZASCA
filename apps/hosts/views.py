"""
主机管理视图
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Host, HostGroup
from apps.accounts import rate_limit
import json


@method_decorator(login_required, name='dispatch')
class HostListView(ListView):
    """主机列表视图"""

    model = Host
    template_name = 'hosts/host_list.html'
    context_object_name = 'hosts'
    paginate_by = 20

    def get_queryset(self):
        """获取查询集"""
        queryset = Host.objects.all()

        # 搜索过滤
        search = self.request.GET.get('search')
        if search:
            # 对搜索输入进行清理，防止潜在的安全问题
            import re
            cleaned_search = re.sub(r'[;"\\\\]+', '', search)[:50]  # 移除潜在危险字符，限制长度
            if cleaned_search:  # 确保清理后的搜索词非空
                queryset = queryset.filter(
                    name__icontains=cleaned_search
                ) | queryset.filter(
                    hostname__icontains=cleaned_search
                )

        # 状态过滤
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        """获取模板上下文数据"""
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        return context


@method_decorator(login_required, name='dispatch')
class HostDetailView(DetailView):
    """主机详情视图"""
    
    model = Host
    template_name = 'hosts/host_detail.html'
    context_object_name = 'host'


@method_decorator(login_required, name='dispatch')
class HostGroupListView(ListView):
    """主机组列表视图"""
    
    model = HostGroup
    template_name = 'hosts/hostgroup_list.html'
    context_object_name = 'hostgroups'
    paginate_by = 20

    def get_queryset(self):
        """获取查询集"""
        queryset = HostGroup.objects.all()

        # 搜索过滤
        search = self.request.GET.get('search')
        if search:
            # 对搜索输入进行清理，防止潜在的安全问题
            import re
            cleaned_search = re.sub(r'[;"\\\\]+', '', search)[:50]  # 移除潜在危险字符，限制长度
            if cleaned_search:  # 确保清理后的搜索词非空
                queryset = queryset.filter(name__icontains=cleaned_search)

        return queryset.order_by('-created_at')


@require_http_methods(["POST"])
@csrf_exempt
@rate_limit.general_api_rate_limit
def test_host_connection(request, host_id):
    """测试主机连接的API"""
    try:
        host = get_object_or_404(Host, id=host_id)
        
        # 测试连接
        host.test_connection()
        
        # 返回结果
        return JsonResponse({
            'status': 'success',
            'message': f'主机连接测试完成，当前状态: {dict(Host.STATUS_CHOICES)[host.status]}',
            'status_code': host.status
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'主机连接测试失败: {str(e)}'
        }, status=500)


@login_required
def api_hosts_list(request):
    """返回主机列表的API"""
    hosts = Host.objects.all().values('id', 'name', 'hostname', 'status', 'host_type')
    return JsonResponse({
        'status': 'success',
        'hosts': list(hosts)
    })