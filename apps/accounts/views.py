"""
用户管理视图
"""
from django.shortcuts import redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.core.cache import cache
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random

from .models import User
from .forms import UserRegistrationForm, UserUpdateForm, UserLoginForm
from . import geetest_utils


class RegisterView(CreateView):
    """用户注册视图"""

    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.dashboard.models import SystemConfig
        sc = SystemConfig.get_config()
        # 使用与后端验证相同的逻辑来确定captcha_id
        captcha_id, _ = geetest_utils._get_runtime_keys()
        context['GEETEST_ID'] = captcha_id
        context['CAPTCHA_PROVIDER'] = sc.captcha_provider
        # 仅在turnstile模式下提供turnstile的site key
        if sc.captcha_provider == 'turnstile':
            context['TURNSTILE_SITE_KEY'] = sc.captcha_id  # 使用统一的captcha_id字段
        else:
            context['TURNSTILE_SITE_KEY'] = None
        return context

    def form_valid(self, form):
        """表单验证成功后的处理"""
        # 在保存用户之前，验证邮箱验证码（行为验证码在获取邮箱验证码时已验证）
        request = self.request
        email = request.POST.get('email')
        email_code = request.POST.get('email_code')
        if not (email and email_code):
            form.add_error(None, '邮箱验证码缺失')
            return self.form_invalid(form)

        cache_key = f'register_email_code:{email}'
        expected = cache.get(cache_key)
        if not expected or expected != email_code:
            form.add_error(None, '邮箱验证码错误或已过期')
            return self.form_invalid(form)

        # Optionally clear the code to prevent reuse
        cache.delete(cache_key)

        response = super().form_valid(form)
        messages.success(
            self.request,
            '注册成功！请登录您的账户。'
        )
        return response

    def form_invalid(self, form):
        """表单验证失败后的处理"""
        messages.error(
            self.request,
            '注册失败，请检查表单中的错误。'
        )
        return super().form_invalid(form)


class LoginView(TemplateView):
    """用户登录视图"""

    template_name = 'accounts/login.html'

    def get_context_data(self, **kwargs):
        """获取模板上下文数据"""
        context = super().get_context_data(**kwargs)
        context['form'] = UserLoginForm()
        from apps.dashboard.models import SystemConfig
        sc = SystemConfig.get_config()
        # 使用与后端验证相同的逻辑来确定captcha_id
        captcha_id, _ = geetest_utils._get_runtime_keys()
        context['GEETEST_ID'] = captcha_id
        context['CAPTCHA_PROVIDER'] = sc.captcha_provider
        # 仅在turnstile模式下提供turnstile的site key
        if sc.captcha_provider == 'turnstile':
            context['TURNSTILE_SITE_KEY'] = sc.captcha_id  # 使用统一的captcha_id字段
        else:
            context['TURNSTILE_SITE_KEY'] = None
        return context

    def post(self, request, *args, **kwargs):
        """处理POST请求"""
        form = UserLoginForm(request.POST)

        if form.is_valid():
            # 根据系统配置决定是否需要行为验证码（仅 geetest 时启用）
            from apps.dashboard.models import SystemConfig
            provider = SystemConfig.get_config().captcha_provider
            if provider == 'geetest':
                # 在认证之前做 Geetest v4 二次校验
                lot_number = request.POST.get('lot_number')
                captcha_output = request.POST.get('captcha_output')
                pass_token = request.POST.get('pass_token')
                gen_time = request.POST.get('gen_time')
                captcha_id = request.POST.get('captcha_id')

                if not (lot_number and captcha_output and pass_token and gen_time):
                    form.add_error(None, '请完成验证码验证')
                    context = self.get_context_data(**kwargs)
                    context['form'] = form
                    return self.render_to_response(context)

                ok, resp = geetest_utils.verify_geetest_v4(lot_number, captcha_output, pass_token, gen_time, captcha_id=captcha_id)
                if not ok:
                    form.add_error(None, '验证码校验失败')
                    context = self.get_context_data(**kwargs)
                    context['form'] = form
                    return self.render_to_response(context)
            elif provider == 'turnstile':
                # Turnstile token param is usually 'cf-turnstile-response'
                tf_token = request.POST.get('cf-turnstile-response') or request.POST.get('turnstile_token')
                if not tf_token:
                    form.add_error(None, '请完成 Turnstile 验证')
                    context = self.get_context_data(**kwargs)
                    context['form'] = form
                    return self.render_to_response(context)
                ok, resp = geetest_utils.verify_turnstile(tf_token, remoteip=request.META.get('REMOTE_ADDR'))
                if not ok:
                    form.add_error(None, 'Turnstile 验证失败')
                    context = self.get_context_data(**kwargs)
                    context['form'] = form
                    return self.render_to_response(context)

            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember = form.cleaned_data.get('remember', False)

            from django.contrib.auth import authenticate
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # 更新最后登录IP
                from django.utils import timezone
                user.last_login = timezone.now()
                user.last_login_ip = self.get_client_ip(request)
                user.save(update_fields=['last_login', 'last_login_ip'])

                # 登录用户
                login(request, user)

                # 设置会话过期时间
                if not remember:
                    request.session.set_expiry(0)  # 浏览器关闭后过期
                else:
                    request.session.set_expiry(60 * 60 * 24 * 7)  # 7天

                messages.success(request, f'欢迎回来，{user.username}！')
                # 检查用户是否为管理员，如果是则跳转到admin页面
                if user.is_staff or user.is_superuser:
                    return redirect('/admin/')
                return redirect('dashboard:index')
            else:
                messages.error(request, '用户名或密码错误')

        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)

    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@method_decorator(login_required, name='dispatch')
class ProfileView(UpdateView):
    """用户资料视图"""

    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        """获取当前用户对象"""
        return self.request.user

    def form_valid(self, form):
        """表单验证成功后的处理"""
        messages.success(
            self.request,
            '个人资料更新成功！'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """表单验证失败后的处理"""
        messages.error(
            self.request,
            '个人资料更新失败，请检查表单中的错误。'
        )
        return super().form_invalid(form)


@login_required
def logout_view(request):
    """用户登出视图"""
    logout(request)
    messages.success(request, '您已成功登出')
    return redirect('accounts:login')


# Geetest endpoints
@require_http_methods(['GET'])
def geetest_register(request):
    """为前端提供极验初始化参数（JSON）"""
    data = geetest_utils.get_geetest_init(request)
    return JsonResponse(data)


@require_http_methods(['POST'])
@csrf_protect
def geetest_validate(request):
    """可以做一次性的验证接口（可选）。前端可直接把三个字段POST到此处获取验证结果"""
    # 支持 v4 参数（lot_number / captcha_output / pass_token / gen_time / captcha_id）
    lot_number = request.POST.get('lot_number')
    captcha_output = request.POST.get('captcha_output')
    pass_token = request.POST.get('pass_token')
    gen_time = request.POST.get('gen_time')
    captcha_id = request.POST.get('captcha_id')

    if lot_number and captcha_output and pass_token and gen_time:
        ok, resp = geetest_utils.verify_geetest_v4(lot_number, captcha_output, pass_token, gen_time, captcha_id=captcha_id)
        if ok:
            return JsonResponse({'result': 'ok', 'detail': resp})
        else:
            return JsonResponse({'result': 'fail', 'detail': resp}, status=400)

    return JsonResponse({'result': 'fail', 'detail': '参数不完整'}, status=400)


def _gen_code(length=6):
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


@csrf_exempt
@require_http_methods(['POST'])
def send_register_email_code(request):
    """Send a one-time code to the supplied email for registration.

    Requires behavior captcha validation to have been passed in this session if captcha_provider == 'geetest' or 'turnstile'
    (adapter should call /accounts/geetest/validate/ first and backend can check session or just trust front-end - here we trust front-end token by requiring v4 params in this request).
    """
    # 检查是否启用了注册功能
    from apps.dashboard.models import SystemConfig
    cfg = SystemConfig.get_config()
    if not cfg.enable_registration:
        return JsonResponse({'status': 'error', 'message': '注册功能已被管理员禁用'}, status=400)

    email = request.POST.get('email')
    # v4 captcha params optional but recommended to prevent abuse
    lot_number = request.POST.get('lot_number')
    captcha_output = request.POST.get('captcha_output')
    pass_token = request.POST.get('pass_token')
    gen_time = request.POST.get('gen_time')
    captcha_id = request.POST.get('captcha_id')

    # Validate email
    if not email:
        return JsonResponse({'status': 'error', 'message': '缺少email'}, status=400)

    # Check system config: if provider is geetest, require v4 params and validate them
    provider = getattr(cfg, 'captcha_provider', 'none')

    if provider == 'geetest':
        if not (lot_number and captcha_output and pass_token and gen_time):
            return JsonResponse({'status': 'error', 'message': '请先完成行为验证'}, status=400)
        ok, resp = geetest_utils.verify_geetest_v4(lot_number, captcha_output, pass_token, gen_time, captcha_id=captcha_id)
        if not ok:
            return JsonResponse({'status': 'error', 'message': '行为验证失败'}, status=400)
    elif provider == 'turnstile':
        # Turnstile token param is usually 'cf-turnstile-response'
        tf_token = request.POST.get('cf-turnstile-response') or request.POST.get('turnstile_token')
        if not tf_token:
            return JsonResponse({'status': 'error', 'message': '请先完成Turnstile验证'}, status=400)
        ok, resp = geetest_utils.verify_turnstile(tf_token, remoteip=request.META.get('REMOTE_ADDR'))
        if not ok:
            return JsonResponse({'status': 'error', 'message': 'Turnstile 验证失败'}, status=400)

    # generate code and store in cache
    code = _gen_code(6)
    cache_key = f'register_email_code:{email}'
    cache.set(cache_key, code, timeout=10 * 60)  # 10 minutes

    # send email using direct SMTP connection
    subject = 'ZASCA 注册验证码'
    message_body = f'您的注册验证码是: {code}，有效期10分钟。'
    from_email = cfg.smtp_from_email
    
    if cfg.smtp_host and cfg.smtp_port and cfg.smtp_username and cfg.smtp_password and cfg.smtp_from_email:
        # Create HTML email template for registration (never a test email in this context)
        html_body = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; }}
                .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; border-bottom: 1px solid #dee2e6; }}
                .content {{ padding: 20px 0; }}
                .code {{ font-size: 24px; font-weight: bold; color: #007bff; letter-spacing: 5px; text-align: center; margin: 20px 0; }}
                .footer {{ padding: 20px 0; text-align: center; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>ZASCA 验证码服务</h2>
                </div>
                <div class="content">
                    <p>您好！</p>
                    <p>感谢您注册ZASCA账户。</p>
                    <p>您的验证码是：</p>
                    <div class="code">{code}</div>
                    <p>此验证码将在10分钟后失效，请及时使用。</p>
                    <p>如果您没有进行相关操作，请忽略此邮件。</p>
                </div>
                <div class="footer">
                    <p>© 2026 ZASCA. All rights reserved.</p>
                    <p>此邮件由系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # 使用配置的SMTP设置直接发送HTML邮件
        msg = MIMEMultipart('alternative')  # 使用alternative类型支持HTML和纯文本
        msg['From'] = from_email
        msg['To'] = email
        msg['Subject'] = subject
        
        # 添加纯文本版本作为备选
        text_body = message_body
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # 根据配置决定是否使用STARTTLS
        server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port)
        server.ehlo()

        if cfg.smtp_use_tls:
            server.starttls()
            server.ehlo()

        server.login(cfg.smtp_username, cfg.smtp_password)
        text = msg.as_string()
        server.sendmail(from_email, [email], text)
        server.quit()
    else:
        return JsonResponse({'status': 'error', 'message': 'SMTP配置不完整'}, status=500)

    return JsonResponse({'status': 'ok'})