"""
操作记录视图
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from datetime import timedelta
from .models import AccountOpeningRequest, SystemTask, CloudComputerUser, Product
from .forms import AccountOpeningRequestForm, AccountOpeningRequestFilterForm, CloudComputerUserFilterForm
from apps.hosts.models import Host
from django.http import JsonResponse
from utils.error_handlers import safe_exception_handler, create_error_response, WinRMConnectionException
from utils.error_handlers import sanitize_error_message as sanitize_msg
import logging


@method_decorator(login_required, name='dispatch')
class SystemTaskListView(ListView):
    """系统任务列表视图"""

    model = SystemTask
    template_name = 'operations/systemtask_list.html'
    context_object_name = 'tasks'
    paginate_by = 20

    def get_queryset(self):
        """获取查询集"""
        queryset = SystemTask.objects.all()

        # 应用过滤条件
        form = SystemTaskFilterForm(self.request.GET)
        if form.is_valid():
            task_type = form.cleaned_data.get('task_type')
            status = form.cleaned_data.get('status')
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')

            if task_type:
                # 对搜索输入进行清理，防止潜在的安全问题
                import re
                cleaned_task_type = re.sub(r'[;"\\\\]+', '', task_type)[:50]  # 移除潜在危险字符，限制长度
                if cleaned_task_type:  # 确保清理后的搜索词非空
                    queryset = queryset.filter(task_type__icontains=cleaned_task_type)
            if status:
                queryset = queryset.filter(status=status)
            if start_date:
                queryset = queryset.filter(created_at__gte=start_date)
            if end_date:
                # 包含结束日期的整天
                end_date = end_date + timedelta(days=1)
                queryset = queryset.filter(created_at__lt=end_date)

        return queryset.select_related('created_by').order_by('-created_at')

    def get_context_data(self, **kwargs):
        """获取模板上下文数据"""
        context = super().get_context_data(**kwargs)
        context['filter_form'] = SystemTaskFilterForm(self.request.GET)
        return context


@method_decorator(login_required, name='dispatch')
class SystemTaskDetailView(DetailView):
    """系统任务详情视图"""

    model = SystemTask
    template_name = 'operations/systemtask_detail.html'
    context_object_name = 'task'


@login_required
def task_progress(request, task_id):
    """
    获取任务进度

    Args:
        request: HTTP请求对象
        task_id: 任务ID

    Returns:
        JsonResponse: JSON格式的响应
    """
    try:
        task = SystemTask.objects.get(pk=task_id)
        return JsonResponse({
            'success': True,
            'data': {
                'id': task.id,
                'name': task.name,
                'status': task.status,
                'progress': task.progress,
                'result': task.result,
                'error_message': task.error_message,
            }
        })
    except SystemTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        })


class AccountOpeningRequestCreateView(CreateView):
    """创建开户申请视图"""
    
    model = AccountOpeningRequest
    form_class = AccountOpeningRequestForm
    template_name = 'operations/account_opening_request_form.html'
    success_url = reverse_lazy('operations:account_opening_confirm')

    def get_form_kwargs(self):
        """获取表单初始化参数"""
        kwargs = super().get_form_kwargs()
        
        # 获取目标产品ID参数
        target_product_id = self.request.GET.get('target_product')
        target_host_id = self.request.GET.get('target_host')  # 兼容旧参数
        
        # 获取可用产品查询集
        products_qs = Product.objects.filter(is_available=True)
        
        # 如果指定了特定产品，限制查询集
        if target_product_id:
            try:
                target_product = Product.objects.get(id=target_product_id, is_available=True)
                products_qs = Product.objects.filter(id=target_product.id)
            except Product.DoesNotExist:
                pass
        elif target_host_id:
            # 兼容旧参数：如果通过target_host指定，则找出关联的产品
            try:
                from apps.hosts.models import Host
                host = Host.objects.get(id=target_host_id)
                # 获取与该主机关联的所有可用产品
                products_qs = Product.objects.filter(host=host, is_available=True)
            except Host.DoesNotExist:
                pass
        
        # 将产品查询集传递给表单
        kwargs['products_qs'] = products_qs
        return kwargs

    def form_valid(self, form):
        """表单验证成功后的处理"""
        # 将表单数据存储到session中以供确认页面使用
        confirm_data = {
            'contact_email': self.request.user.email,  # 使用当前用户的邮箱，而不是从表单获取
            'username': form.cleaned_data['username'],
            'user_fullname': form.cleaned_data['user_fullname'],
            'user_description': form.cleaned_data['user_description'],
            'target_product_id': form.cleaned_data['target_product'].id,
            'target_product_name': form.cleaned_data['target_product'].display_name,
        }
        self.request.session['confirm_data'] = confirm_data
        
        # 重定向到确认页面，而不是直接保存
        return redirect('operations:account_opening_confirm')

    def form_invalid(self, form):
        """表单验证失败后的处理"""
        messages.error(self.request, '开户申请信息填写有误，请检查输入信息。')
        return super().form_invalid(form)


@login_required
def account_opening_confirm(request):
    """开户申请确认页面"""
    confirm_data = request.session.get('confirm_data')
    if not confirm_data:
        messages.error(request, '未找到待确认的申请信息，请重新填写申请。')
        return redirect('operations:account_opening_create')
    
    context = {
        'confirm_data': confirm_data
    }
    return render(request, 'operations/account_opening_confirm.html', context)


@csrf_protect
@require_POST
@login_required
@safe_exception_handler  # 添加安全异常处理
def account_opening_submit(request):
    """提交开户申请"""
    logger = logging.getLogger('zasca')

    confirm_data = request.session.get('confirm_data')
    if not confirm_data:
        messages.error(request, '未找到待提交的申请信息。')
        logger.warning(f'用户 {request.user.username} 尝试提交开户申请，但未找到确认数据')
        return redirect('operations:account_opening_create')
    
    # 创建开户申请对象
    account_request = AccountOpeningRequest()
    account_request.applicant = request.user
    account_request.contact_email = request.user.email  # 使用当前用户的邮箱，而不是表单中的数据
    account_request.username = confirm_data['username']
    account_request.user_fullname = confirm_data['user_fullname']
    account_request.user_email = request.user.email  # 使用当前用户的邮箱
    account_request.user_description = confirm_data['user_description']
    # 移除了requested_password字段，由系统自动生成
    
    # 设置目标产品
    try:
        target_product = Product.objects.get(id=confirm_data['target_product_id'])
        account_request.target_product = target_product
        logger.info(f'用户 {request.user.username} 提交开户申请，目标产品: {target_product.name}, 用户名: {account_request.username}, 联系邮箱: {account_request.contact_email}')
    except Product.DoesNotExist:
        messages.error(request, '指定的目标产品不存在。')
        logger.error(f'用户 {request.user.username} 尝试提交申请，但目标产品ID {confirm_data["target_product_id"]} 不存在')
        return redirect('operations:account_opening_create')
    
    try:
        logger.info(f'准备保存开户申请，当前状态: {account_request.status}')
        account_request.save()
        logger.info(f'开户申请已保存，ID: {account_request.id}, 最终状态: {account_request.status}')
        messages.success(request, '开户申请已成功提交，请等待审核。')
        
        # 清除session中的确认数据
        del request.session['confirm_data']
        
        return redirect('operations:account_opening_list')
    except ValidationError as e:
        logger.error(f'验证错误: {str(e)}')
        messages.error(request, f'输入数据验证失败: {str(e)}')
        return redirect('operations:account_opening_create')
    except ObjectDoesNotExist as e:
        logger.error(f'对象不存在错误: {str(e)}')
        messages.error(request, '指定的资源不存在')
        return redirect('operations:account_opening_create')
    except Exception as e:
        # 记录内部错误但不暴露给用户
        error_response = create_error_response(e, request)
        logger.error(f'提交申请时发生错误 [trace_id: {error_response["trace_id"]}]: {str(e)}', exc_info=True)
        messages.error(request, '提交申请时发生错误，请联系技术支持')
        return redirect('operations:account_opening_create')


class AccountOpeningRequestListView(ListView):
    """开户申请列表视图"""
    
    model = AccountOpeningRequest
    template_name = 'operations/account_opening_request_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        """获取查询集"""
        queryset = AccountOpeningRequest.objects.all()

        # 如果不是管理员，则只显示自己的申请
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(applicant=self.request.user)

        # 应用过滤条件
        form = AccountOpeningRequestFilterForm(self.request.GET)
        if form.is_valid():
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)

            host = form.cleaned_data.get('host')
            if host:
                # 查询与该主机相关的产品的申请
                queryset = queryset.filter(target_product__host=host)

            search = form.cleaned_data.get('search')
            if search:
                # 对搜索输入进行清理，防止潜在的安全问题
                import re
                cleaned_search = re.sub(r'[;"\\\\]+', '', search)[:50]  # 移除潜在危险字符，限制长度
                if cleaned_search:  # 确保清理后的搜索词非空
                    queryset = queryset.filter(
                        Q(username__icontains=cleaned_search) |
                        Q(user_fullname__icontains=cleaned_search) |
                        Q(contact_email__icontains=cleaned_search)
                    )

        return queryset.select_related('applicant', 'target_product', 'target_product__host', 'approved_by').order_by('-created_at')

    def get_context_data(self, **kwargs):
        """获取模板上下文数据"""
        context = super().get_context_data(**kwargs)
        context['filter_form'] = AccountOpeningRequestFilterForm(self.request.GET)
        context['statuses'] = AccountOpeningRequest._meta.get_field('status').choices
        
        # 如果是管理员，显示所有主机；否则只显示与用户申请相关的产品的主机
        if self.request.user.is_staff or self.request.user.is_superuser:
            context['hosts'] = Host.objects.all()
        else:
            context['hosts'] = Host.objects.filter(
                product__accountopeningrequest__applicant=self.request.user
            ).distinct()
        
        return context


@login_required
def account_opening_detail(request, pk):
    """查看开户申请详情"""
    account_request = get_object_or_404(AccountOpeningRequest, pk=pk)
    
    # 检查权限：用户只能查看自己提交的申请
    if account_request.applicant != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '您没有权限查看此申请的详情。')
        return redirect('operations:account_opening_list')
    
    context = {
        'request': account_request
    }
    return render(request, 'operations/account_opening_request_detail.html', context)


@login_required
def approve_account_request(request, pk):
    """批准开户申请"""
    account_request = get_object_or_404(AccountOpeningRequest, pk=pk)

    # 检查权限
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '您没有权限执行此操作。')
        return redirect('operations:account_opening_list')

    if request.method == 'POST':
        notes = request.POST.get('approval_notes', '')
        account_request.approve(request.user, notes)
        messages.success(request, f'开户申请已批准：{account_request.username}')
        return redirect('operations:account_opening_list')

    context = {
        'request_obj': account_request,
        'action': 'approve'
    }
    return render(request, 'operations/account_opening_confirm.html', context)


@login_required
def reject_account_request(request, pk):
    """拒绝开户申请"""
    account_request = get_object_or_404(AccountOpeningRequest, pk=pk)

    # 检查权限
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '您没有权限执行此操作。')
        return redirect('operations:account_opening_list')

    if request.method == 'POST':
        notes = request.POST.get('approval_notes', '')
        account_request.reject(request.user, notes)
        messages.success(request, f'开户申请已拒绝：{account_request.username}')
        return redirect('operations:account_opening_list')

    context = {
        'request_obj': account_request,
        'action': 'reject'
    }
    return render(request, 'operations/account_opening_confirm.html', context)


@login_required
@safe_exception_handler  # 添加安全异常处理
def process_account_request(request, pk):
    """处理开户申请（执行实际的开户操作）"""
    logger = logging.getLogger('zasca')

    try:
        account_request = get_object_or_404(AccountOpeningRequest, pk=pk)
    except ObjectDoesNotExist:
        messages.error(request, '指定的申请不存在')
        return redirect('operations:account_opening_list')

    # 检查权限
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '您没有权限执行此操作。')
        return redirect('operations:account_opening_list')

    # 确保申请已批准
    if account_request.status not in ['approved', 'pending']:
        messages.error(request, '只有待处理或已批准的申请才能执行开户操作。')
        return redirect('operations:account_opening_list')

    try:
        # 开始处理
        account_request.start_processing()
        
        # 导入WinRM客户端
        from utils.winrm_client import WinrmClient
        import secrets
        import string
        
        # 系统生成强密码
        password = CloudComputerUser.generate_complex_password()
        
        # 连接到目标主机 - 使用target_product关联的主机
        host = account_request.target_product.host
        client = WinrmClient(
            hostname=host.hostname,
            port=host.port,
            username=host.username,
            password=host.password,
            use_ssl=host.use_ssl
        )

        
        result = client.create_user(account_request.username, password)
        
        if result.status_code == 0:
            # 成功创建用户
            # 创建云电脑用户记录，并存储初始密码
            cloud_user, created = CloudComputerUser.objects.get_or_create(
                username=account_request.username,
                product=account_request.target_product,
                defaults={
                    'fullname': account_request.user_fullname,
                    'email': account_request.user_email,
                    'description': account_request.user_description,
                    'created_from_request': account_request,
                    'initial_password': password  # 存储生成的密码
                }
            )
            
            account_request.complete(account_request.username, '', f"用户 {account_request.username} 已成功创建")
            messages.success(request, f"用户 {account_request.username} 已成功创建")
        else:
            # 创建用户失败
            error_msg = result.std_err if result.std_err else '未知错误'
            account_request.fail(f"创建用户失败: {error_msg}")
            messages.error(request, f"创建用户失败: {error_msg}")

    except ValidationError as e:
        error_msg = sanitize_msg(str(e))
        account_request.fail(f"验证错误: {error_msg}")
        logger.error(f"处理开户申请时验证失败 [申请ID: {pk}]: {error_msg}")
        messages.error(request, f"输入验证错误: {error_msg}")
    except WinRMConnectionException as e:
        error_msg = sanitize_msg(str(e))
        account_request.fail(f"连接错误: {error_msg}")
        logger.error(f"WinRM 连接失败 [申请ID: {pk}] [主机: {account_request.target_product.host.hostname}]: {error_msg}")
        messages.error(request, f"无法连接到远程主机: {error_msg}")
    except Exception as e:
        error_response = create_error_response(e, request)
        error_msg = sanitize_msg(str(e))
        account_request.fail(error_msg)
        logger.error(f"处理开户申请时失败 [申请ID: {pk}] [trace_id: {error_response['trace_id']}]: {error_msg}", exc_info=True)
        messages.error(request, f"处理失败，请联系技术支持 (错误ID: {error_response['trace_id']})")

    return redirect('operations:account_opening_list')


@method_decorator(login_required, name='dispatch')
class CloudComputerUserListView(ListView):
    """云电脑用户列表视图"""
    
    model = CloudComputerUser
    template_name = 'operations/cloud_computer_user_list.html'
    context_object_name = 'cloud_users'
    paginate_by = 20

    def get_queryset(self):
        """获取查询集"""
        queryset = CloudComputerUser.objects.all()

        # 应用过滤条件
        form = CloudComputerUserFilterForm(self.request.GET)
        if form.is_valid():
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)

            host = form.cleaned_data.get('host')
            if host:
                queryset = queryset.filter(host=host)

            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(username__icontains=search) |
                    Q(fullname__icontains=search) |
                    Q(email__icontains=search)
                )

        return queryset.select_related('host', 'created_from_request__applicant').order_by('-created_at')

    def get_context_data(self, **kwargs):
        """获取模板上下文数据"""
        context = super().get_context_data(**kwargs)
        context['filter_form'] = CloudComputerUserFilterForm(self.request.GET)
        context['statuses'] = CloudComputerUser._meta.get_field('status').choices
        context['hosts'] = Host.objects.all()
        return context


@login_required
def toggle_cloud_user_status(request, pk):
    """切换云电脑用户状态"""
    cloud_user = get_object_or_404(CloudComputerUser, pk=pk)

    # 检查权限
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, '您没有权限执行此操作。')
        return redirect('operations:cloud_user_list')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'activate':
            cloud_user.activate()
            messages.success(request, f'用户 {cloud_user.username} 已激活。')
        elif action == 'deactivate':
            cloud_user.deactivate()
            messages.success(request, f'用户 {cloud_user.username} 已停用。')
        elif action == 'disable':
            cloud_user.disable()
            messages.success(request, f'用户 {cloud_user.username} 已禁用。')
        elif action == 'delete':
            cloud_user.delete_user()
            messages.success(request, f'用户 {cloud_user.username} 已标记为删除。')
        else:
            messages.error(request, '无效的操作。')

        return redirect('operations:cloud_user_list')

    context = {
        'cloud_user': cloud_user
    }
    return render(request, 'operations/cloud_user_toggle_status.html', context)


@method_decorator(login_required, name='dispatch')
class MyCloudComputersView(ListView):
    """我的云电脑用户列表视图
    
    显示当前用户拥有的云电脑用户
    """
    
    model = CloudComputerUser
    template_name = 'operations/my_cloud_computers.html'
    context_object_name = 'cloud_users'
    paginate_by = 20

    def get_queryset(self):
        """获取查询集 - 只显示当前用户通过开户申请创建的云电脑用户"""
        queryset = CloudComputerUser.objects.filter(
            created_from_request__applicant=self.request.user
        )

        # 应用过滤条件
        form = CloudComputerUserFilterForm(self.request.GET)
        if form.is_valid():
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)

            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(username__icontains=search) |
                    Q(fullname__icontains=search) |
                    Q(email__icontains=search) |
                    Q(product__display_name__icontains=search)
                )

        # 按产品筛选
        product_filter = self.request.GET.get('product')
        if product_filter:
            queryset = queryset.filter(product__display_name=product_filter)

        return queryset.select_related('product', 'created_from_request').order_by('-created_at')

    def get_context_data(self, **kwargs):
        """获取模板上下文数据"""
        context = super().get_context_data(**kwargs)
        context['filter_form'] = CloudComputerUserFilterForm(self.request.GET)
        context['statuses'] = CloudComputerUser._meta.get_field('status').choices
        
        # 按产品分组云电脑用户
        from collections import defaultdict
        cloud_users_by_product = defaultdict(list)
        for user in context['cloud_users']:
            cloud_users_by_product[user.product.display_name].append(user)
        context['cloud_users_by_product'] = dict(cloud_users_by_product)
        
        return context


@login_required
def my_cloud_computer_detail(request, pk):
    """我的云电脑用户详情页面"""
    cloud_user = get_object_or_404(CloudComputerUser, pk=pk)

    # 权限检查：owner优先，兼容旧数据用created_from_request
    if cloud_user.owner:
        if cloud_user.owner != request.user:
            return HttpResponseForbidden('无权访问')
    elif cloud_user.created_from_request:
        if cloud_user.created_from_request.applicant != request.user:
            return HttpResponseForbidden('无权访问')
    else:
        return HttpResponseForbidden('无权访问')

    context = {'cloud_user': cloud_user}
    return render(request, 'operations/my_cloud_computer_detail.html', context)


@login_required
@require_POST
def get_password_and_burn(request, pk):
    """获取密码并销毁 - 阅后即焚"""
    cloud_user = get_object_or_404(CloudComputerUser, pk=pk)

    # 权限检查
    has_access = False
    if cloud_user.owner and cloud_user.owner == request.user:
        has_access = True
    elif cloud_user.created_from_request and cloud_user.created_from_request.applicant == request.user:
        has_access = True

    if not has_access:
        return JsonResponse({'success': False, 'error': '无权访问'}, status=403)

    try:
        password = cloud_user.get_and_burn_password()
        return JsonResponse({'success': True, 'password': password})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
